# core/chatbox_converter.py
# 文件作用：负责生成“Chatbox弹幕”效果的ASS字幕文件。

import re
import os
import codecs

# 【最终修复】在函数定义中，添加缺失的 'internal_line_spacing' 参数
def generate_chatbox_ass(
    lrc_file, ass_file, video_width, video_height, 
    font_name, font_size, line_spacing, internal_line_spacing, letter_spacing, 
    chatbox_max_height_ratio, margin_left, margin_bottom, 
    chatbox_duration_after_last, wrap_width, primary_colour, outline
):
    """
    将LRC文件转换为模拟聊天框滚动效果的ASS字幕文件。
    这是一个独立的转换器，拥有自己的解析和渲染逻辑。
    """
    try:
        max_pixel_height = int(video_height * chatbox_max_height_ratio)
        
        header = f"""[Script Info]
Title: Converted from LRC to Chatbox
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Chatbox,{font_name},{font_size},{primary_colour},{primary_colour},&H00000000,&H00000000,0,0,0,0,100,100,{letter_spacing},0,1,{outline},0,1,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(lrc_file, 'r', encoding='utf-8-sig') as f:
            lrc_content = f.readlines()
        
        pattern = re.compile(r'\[(\d{2}):(\d{2}):(\d{2})[.:](\d{2,3})\](.*)')
        comments = []
        
        # 【最终修复】这个内部函数现在使用新的 'internal_line_spacing' 参数
        def wrap_text_chatbox(text, max_length, spacing):
            if max_length <= 0 or len(text) <= max_length:
                return text
            lines = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            spacer = f'\\N{{\\r\\fs{spacing}}}\\h\\N{{\\r}}'
            return spacer.join(lines)

        for line in lrc_content:
            m = pattern.search(line)
            if not m: continue
            hh, mm, ss, ms_s, txt = m.groups()
            ms = int(ms_s.ljust(3, '0'))
            txt = txt.strip()
            if not txt: continue
            
            parts = re.split(r'\s+', txt, 1)
            formatted_txt = f"{parts[0]}:{parts[1]}" if len(parts) == 2 else txt
            
            # 【最终修复】确保调用时传递的是 'internal_line_spacing'
            wrapped_text = wrap_text_chatbox(
                text=formatted_txt, 
                max_length=wrap_width,
                spacing=internal_line_spacing # 使用弹幕内行距
            )
            
            t = int(hh) * 3600 + int(mm) * 60 + int(ss) + ms / 1000
            comments.append((t, wrapped_text))
            
        if not comments:
            return False, "警告：未在LRC文件中解析到任何弹幕！"
        
        comments.sort(key=lambda x: x[0])
        events = []
        
        # 【最终修复】高度计算时，也要使用 internal_line_spacing
        internal_line_h = font_size + internal_line_spacing
        
        pos_x = margin_left
        pos_y = video_height - margin_bottom

        def fmt_time(t):
            h = int(t // 3600)
            m = int((t - h * 3600) // 60)
            s = t - h * 3600 - m * 60
            cs = int((s - int(s)) * 100)
            return f"{h}:{m:02}:{int(s):02}.{cs:02}"

        for i, (start_t, _) in enumerate(comments):
            end_t = comments[i+1][0] if i+1 < len(comments) else start_t + chatbox_duration_after_last
            if end_t - start_t < 0.1: continue

            h_acc = 0
            lines_to_display = []
            for j in range(i, -1, -1):
                comment_text = comments[j][1]
                
                num_internal_lines = comment_text.count('{\\r\\fs') + 1
                comment_height = num_internal_lines * internal_line_h
                
                # 不同弹幕之间的间隔，由大的 line_spacing 控制
                separator_height = (font_size + line_spacing) if lines_to_display else 0
                if h_acc + comment_height + separator_height > max_pixel_height:
                    break
                h_acc += comment_height + separator_height
                lines_to_display.insert(0, comment_text)
            
            # 使用大的 line_spacing 来连接不同的弹幕
            spacer = f'\\N{{\\r\\fs{line_spacing}}}\\h\\N{{\\r}}'
            text = spacer.join(lines_to_display)

            x1, y1 = margin_left, pos_y - max_pixel_height
            x2, y2 = video_width - margin_left, pos_y
            override = f"{{\\an1\\pos({pos_x},{pos_y})\\fs{font_size}\\fn{font_name}\\fsp{letter_spacing}\\clip({x1},{y1},{x2},{y2})}}"
            full_text = f"{override}{text}"
            events.append(f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},Chatbox,,0,0,0,,{full_text}")

        with codecs.open(ass_file, 'w', 'utf-8-sig') as fw:
            fw.write(header)
            fw.write("\n".join(events))
            
        return True, f"成功生成 {len(events)} 条弹幕事件"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"生成Chatbox ASS文件时发生严重错误: {e}"