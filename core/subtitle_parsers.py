# core/subtitle_parsers.py
# 文件作用：提供一个统一的字幕文件解析器，支持多种格式。

import re
import os

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
    except (ValueError, IndexError):
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

    return [e for e in final_events if e.get('end', 0) > e.get('start', 0)]

def _parse_srt_vtt(file_path):
    """解析SRT或VTT文件"""
    events = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    blocks = re.split(r'\n\s*\n', content.strip())
    time_pattern = re.compile(r'(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 1:
            time_line = ""
            text_lines = []
            
            for i, line in enumerate(lines):
                if '-->' in line:
                    time_line = line
                    text_lines = lines[i+1:]
                    break
            
            if not time_line:
                # 兼容 VTT 文件中时间戳在第二行的情况
                if len(lines) >= 2 and '-->' in lines[1]:
                    time_line = lines[1]
                    text_lines = lines[2:]

            time_match = time_pattern.search(time_line)
            if time_match:
                start_str, end_str = time_match.groups()
                start_sec = _time_to_seconds(start_str)
                end_sec = _time_to_seconds(end_str)
                text = ' '.join(text_lines).strip()
                if text:
                    events.append({'start': start_sec, 'end': end_sec, 'text': text})
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
            text = text.strip()
            if text:
                events.append({
                    'start': _time_to_seconds(start_str),
                    'end': _time_to_seconds(end_str),
                    'text': text
                })
    return events

def parse_subtitle_file(subtitle_path):
    """
    根据文件扩展名，调用相应的解析器，返回一个包含事件字典的列表。
    每个字典包含 'start', 'end', 'text' 三个键。
    """
    _, ext = os.path.splitext(subtitle_path.lower())
    
    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"字幕文件未找到: {subtitle_path}")

    try:
        if ext == '.lrc':
            return _parse_lrc(subtitle_path)
        elif ext == '.srt' or ext == '.vtt':
            return _parse_srt_vtt(subtitle_path)
        elif ext == '.txt':
            return _parse_custom_txt(subtitle_path)
        else:
            raise ValueError(f"不支持的字幕文件格式: {ext}")
    except Exception as e:
        # 捕获所有潜在的解析错误，并返回一个更友好的信息
        raise IOError(f"解析字幕文件 '{os.path.basename(subtitle_path)}' 时出错: {e}")