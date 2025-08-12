# core/subtitle_converter.py
# 文件作用：负责将多种格式的字幕文件(LRC, SRT, VTT, TXT)转换为ASS格式。

import re
import os
import codecs

# ==============================================================================
# 1. 新增：多种字幕格式的解析器
# ==============================================================================

def _time_to_seconds(time_str):
    """将 HH:MM:SS,ms 或 MM:SS.ms 格式的时间字符串转换为秒。"""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    seconds = 0
    try:
        if len(parts) == 3:  # HH:MM:SS.ms
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:  # MM:SS.ms
            seconds = int(parts[0]) * 60 + float(parts[1])
    except ValueError:
        seconds = 0 # 如果格式转换失败，返回0
    return seconds

def _parse_lrc(file_path):
    """解析LRC文件"""
    events = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    
    time_pattern = re.compile(r'\[(\d{2}):(\d{2})[.:](\d{2,3})\](.*)')
    
    for line in lines:
        match = time_pattern.search(line.strip())
        if match:
            minutes, seconds, ms_str, text = match.groups()
            text = re.sub(r'\s*\[\d{2}:\d{2}[.:]\d{2,3}\]\s*$', '', text.strip()).strip()
            if text:
                total_seconds = int(minutes) * 60 + int(seconds) + int(ms_str.ljust(3, '0')) / 1000.0
                events.append({'time': total_seconds, 'text': text})

    if not events:
        return []
    
    sorted_events = sorted(events, key=lambda x: x['time'])
    final_events = []
    for i in range(len(sorted_events) - 1):
        final_events.append({
            'start': sorted_events[i]['time'],
            'end': sorted_events[i+1]['time'],
            'text': sorted_events[i]['text']
        })
    if sorted_events:
        last_event = sorted_events[-1]
        final_events.append({
            'start': last_event['time'],
            'end': last_event['time'] + 5,
            'text': last_event['text']
        })

    return [e for e in final_events if e['end'] > e['start']]


def _parse_srt_vtt(file_path):
    """解析SRT或VTT文件"""
    events = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    blocks = re.split(r'\n\s*\n', content.strip())
    time_pattern = re.compile(r'(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            time_line = lines[0] if '-->' in lines[0] else (lines[1] if '-->' in lines[1] else '')
            time_match = time_pattern.search(time_line)
            if time_match:
                start_str, end_str = time_match.groups()
                start_sec = _time_to_seconds(start_str)
                end_sec = _time_to_seconds(end_str)
                text_lines = [l for l in lines if '-->' not in l and not l.strip().isdigit()]
                text = ' '.join(text_lines)
                events.append({'start': start_sec, 'end': end_sec, 'text': text.strip()})
    return events


def _parse_custom_txt(file_path):
    """解析自定义的 [start --> end] text 格式的TXT文件"""
    events = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    time_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\]\s*(.*)')
    for line in lines:
        match = time_pattern.match(line.strip())
        if match:
            start_str, end_str, text = match.groups()
            events.append({
                'start': _time_to_seconds(start_str),
                'end': _time_to_seconds(end_str),
                'text': text.strip()
            })
    return events

def _master_subtitle_parser(subtitle_path):
    """根据文件扩展名，调用相应的解析器"""
    _, ext = os.path.splitext(subtitle_path.lower())
    if ext == '.lrc':
        return _parse_lrc(subtitle_path)
    elif ext == '.srt' or ext == '.vtt':
        return _parse_srt_vtt(subtitle_path)
    elif ext == '.txt':
        return _parse_custom_txt(subtitle_path)
    else:
        raise ValueError(f"不支持的字幕文件格式: {ext}")

# ==============================================================================
# 2. 修改ASS生成函数
# ==============================================================================

def lrc_to_centered_canvas_ass(subtitle_path, ass_path, style_params, canvas_width, canvas_height, video_width):
    try:
        events = _master_subtitle_parser(subtitle_path)
        if not events:
            return False, "字幕文件中未找到有效的事件行。"
            
        subtitle_area_width = canvas_width - video_width
        center_x = video_width + (subtitle_area_width / 2)
        center_y = canvas_height / 2

        ass_header = f"""[Script Info]
Title: Converted from {os.path.basename(subtitle_path)}
ScriptType: v4.00+
WrapStyle: {style_params['wrap_style']}
PlayResX: {canvas_width}
PlayResY: {canvas_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_params['font_name']},{style_params['font_size']},{style_params['primary_colour']},&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,{style_params['spacing']},0,1,{style_params['outline']},2,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(seconds):
            ms_part = int((seconds - int(seconds)) * 100)
            s_part = int(seconds)
            m_part, s_part = divmod(s_part, 60)
            h_part, m_part = divmod(m_part, 60)
            # 【最终修复】使用正确的变量名 m_part 和 s_part
            return f'{h_part}:{m_part:02d}:{s_part:02d}.{ms_part:02d}'

        def wrap_text_with_spacing(text, max_length, line_spacing):
            if max_length <= 0 or len(text) <= max_length:
                return text
            lines = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            spacer = f'\\N{{\\r\\fs{line_spacing}}}\\h\\N{{\\r}}'
            return spacer.join(lines)
        
        position_override = f"{{\\an5\\pos({center_x:.2f},{center_y:.2f})}}"
        dialogue_lines = []
        for event in events:
            start_time, end_time, text = event['start'], event['end'], event['text']
            wrapped_text = wrap_text_with_spacing(
                text,
                style_params['wrap_width'],
                style_params['line_spacing']
            )
            dialogue_lines.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{position_override}{wrapped_text}")
        
        with codecs.open(ass_path, 'w', 'utf-8-sig') as f:
            f.write(ass_header)
            f.write('\n'.join(dialogue_lines))
        return True, f"成功生成 {len(dialogue_lines)} 条字幕事件"
    except Exception as e:
        return False, f"生成ASS文件时发生严重错误: {e}"


def lrc_to_horizontal_ass(subtitle_path, ass_path, style_params, video_width, video_height):
    try:
        events = _master_subtitle_parser(subtitle_path)
        if not events:
            return False, "字幕文件中未找到有效的事件行。"
            
        ass_header = f"""[Script Info]
Title: Converted from {os.path.basename(subtitle_path)}
ScriptType: v4.00+
WrapStyle: {style_params['wrap_style']}
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_params['font_name']},{style_params['font_size']},{style_params['primary_colour']},&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,{style_params['spacing']},0,1,{style_params['outline']},2,2,10,10,{style_params['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(seconds):
            ms_part = int((seconds - int(seconds)) * 100)
            s_part = int(seconds)
            m_part, s_part = divmod(s_part, 60)
            h_part, m_part = divmod(m_part, 60)
            # 【最终修复】使用正确的变量名 m_part 和 s_part
            return f'{h_part}:{m_part:02d}:{s_part:02d}.{ms_part:02d}'

        def wrap_text_with_spacing(text, max_length, line_spacing):
            if max_length <= 0 or len(text) <= max_length:
                return text
            lines = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            spacer = f'\\N{{\\r\\fs{line_spacing}}}\\h\\N{{\\r}}'
            return spacer.join(lines)
        
        dialogue_lines = []
        for event in events:
            start_time, end_time, text = event['start'], event['end'], event['text']
            wrapped_text = wrap_text_with_spacing(
                text,
                style_params['wrap_width'],
                style_params['line_spacing']
            )
            dialogue_lines.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{wrapped_text}")
        
        with codecs.open(ass_path, 'w', 'utf-8-sig') as f:
            f.write(ass_header)
            f.write('\n'.join(dialogue_lines))
        return True, f"成功生成 {len(dialogue_lines)} 条字幕事件"
    except Exception as e:
        return False, f"生成ASS文件时发生严重错误: {e}"

def lrc_to_ass_chatbox_region(lrc_file, ass_file, video_width, video_height, font_name, font_size, line_spacing, letter_spacing, chatbox_max_height_ratio, margin_left, margin_bottom, chatbox_duration_after_last, wrap_width, primary_colour, outline):
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
        
        def wrap_text_simple(text, max_length):
            if max_length <= 0 or len(text) <= max_length:
                return text
            lines = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            return "\\N".join(lines)

        for line in lrc_content:
            m = pattern.search(line)
            if not m: continue
            hh, mm, ss, ms_s, txt = m.groups()
            ms = int(ms_s.ljust(3, '0'))
            txt = txt.strip()
            if not txt: continue
            
            parts = re.split(r'\s+', txt, 1)
            formatted_txt = f"{parts[0]}:{parts[1]}" if len(parts) == 2 else txt
            
            wrapped_text = wrap_text_simple(formatted_txt, max_length=wrap_width)
            
            t = int(hh) * 3600 + int(mm) * 60 + int(ss) + ms / 1000
            comments.append({'time': t, 'text': wrapped_text})
            
        if not comments:
            return False, "警告：未在LRC文件中解析到任何弹幕！"
        
        comments.sort(key=lambda x: x['time'])
        dialogue_lines = []
        
        def fmt_time(t):
            h = int(t // 3600)
            m = int((t - h * 3600) // 60)
            s = t - h * 3600 - m * 60
            cs = int((s - int(s)) * 100)
            return f"{h}:{m:02}:{int(s):02}.{cs:02}"

        for i, current_event in enumerate(comments):
            start_t = current_event['time']
            end_t = comments[i+1]['time'] if i + 1 < len(comments) else start_t + chatbox_duration_after_last
            if end_t <= start_t: continue

            lines_to_display = []
            current_height = 0
            max_pixel_height = video_height * chatbox_max_height_ratio
            line_h = font_size + line_spacing

            for j in range(i, -1, -1):
                prev_event_text = comments[j]['text']
                num_lines = len(prev_event_text.split('\\N'))
                
                required_height = num_lines * line_h
                
                if current_height + required_height > max_pixel_height:
                    break
                
                lines_to_display.insert(0, {'text': prev_event_text, 'height': required_height})
                current_height += required_height

            base_y = video_height - margin_bottom
            y_offset = 0
            
            for k, line_info in enumerate(lines_to_display):
                cmt_text = line_info['text']
                
                current_y = base_y - y_offset
                
                override = f"{{\\an7\\pos({margin_left},{current_y})}}"
                
                dialogue_lines.append(
                    f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},Chatbox,,0,0,0,,{override}{cmt_text}"
                )
                
                y_offset += line_info['height']


        with codecs.open(ass_file, 'w', 'utf-8-sig') as f:
            f.write(header)
            f.write('\n'.join(dialogue_lines))
            
        return True, f"成功生成 {len(dialogue_lines)} 条字幕事件"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"生成ASS文件时发生严重错误: {e}"