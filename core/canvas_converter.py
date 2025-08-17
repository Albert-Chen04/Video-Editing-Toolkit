# core/canvas_converter.py
# 文件作用：负责生成“竖屏画布字幕”效果的ASS字幕文件。

import os
import codecs
from .subtitle_parsers import parse_subtitle_file

def generate_canvas_ass(subtitle_path, ass_path, style_params, canvas_width, canvas_height, video_width):
    """
    将字幕数据转换为ASS字幕，字幕精确居中于视频右侧的画布区域。
    """
    try:
        # --- 1. 使用解析器获取事件 ---
        events = parse_subtitle_file(subtitle_path)
        if not events:
            return False, "字幕文件中未找到有效的事件行。"
            
        # --- 2. 计算字幕的中心定位坐标 ---
        subtitle_area_width = canvas_width - video_width
        center_x = video_width + (subtitle_area_width / 2)
        center_y = canvas_height / 2

        # --- 3. 构建ASS文件头和样式 ---
        ass_header = f"""[Script Info]
Title: Converted from {os.path.basename(subtitle_path)}
ScriptType: v4.00+
WrapStyle: {style_params.get('wrap_style', 0)}
PlayResX: {canvas_width}
PlayResY: {canvas_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_params.get('font_name', '黑体')},{style_params.get('font_size', 90)},{style_params.get('primary_colour', '&H00FFFFFF')},&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,{style_params.get('spacing', 5)},0,1,{style_params.get('outline', 4)},2,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # --- 4. 生成ASS事件行 ---
        def format_time(seconds):
            ms_part = int((seconds - int(seconds)) * 100)
            s_part = int(seconds)
            m_part, s_part = divmod(s_part, 60)
            h_part, m_part = divmod(m_part, 60)
            return f'{h_part}:{m_part:02d}:{s_part:02d}.{ms_part:02d}'

        def wrap_text_with_spacing(text, max_length, line_spacing):
            if max_length <= 0 or len(text) <= max_length:
                return text
            lines = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            # 使用硬空格技巧来实现可靠的行间距
            spacer = f'\\N{{\\r\\fs{line_spacing}}}\\h\\N{{\\r}}'
            return spacer.join(lines)
        
        position_override = f"{{\\an5\\pos({center_x:.2f},{center_y:.2f})}}"
        dialogue_lines = []
        for event in events:
            start_time = event.get('start', 0)
            end_time = event.get('end', 0)
            text = event.get('text', '')
            
            wrapped_text = wrap_text_with_spacing(
                text,
                style_params.get('wrap_width', 10),
                style_params.get('line_spacing', 45)
            )
            dialogue_lines.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{position_override}{wrapped_text}")
        
        # --- 5. 写入文件 ---
        with codecs.open(ass_path, 'w', 'utf-8-sig') as f:
            f.write(ass_header)
            f.write('\n'.join(dialogue_lines))
            
        return True, f"成功生成 {len(dialogue_lines)} 条字幕事件"
        
    except Exception as e:
        return False, f"生成画布ASS文件时发生严重错误: {e}"