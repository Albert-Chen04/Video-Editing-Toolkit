# core/subtitle_converter.py
import re, os, json, subprocess

def get_video_dimensions(video_path, ffprobe_path):
    if not os.path.exists(video_path): return None, None, f"错误：找不到视频文件 '{video_path}'"
    command = [ffprobe_path, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        data = json.loads(result.stdout); width = data["streams"][0]["width"]; height = data["streams"][0]["height"]
        return width, height, "视频尺寸检测成功"
    except Exception as e: return None, None, f"获取视频尺寸失败: {e}"

def wrap_text(text, width=20, indent="  "):
    if len(text) <= width: return text
    lines = [text[:width]]; remaining_text = text[width:]; sub_width = width - len(indent)
    while remaining_text: chunk = remaining_text[:sub_width]; lines.append(indent + chunk); remaining_text = remaining_text[sub_width:]
    return "\\N".join(lines)

# --- 【核心修正】将函数的参数名 'height' 改为 'video_height' 以保持一致 ---
def lrc_to_ass_chatbox_region(lrc_file, ass_file, video_width, video_height, font_name, font_size, line_spacing, letter_spacing, chatbox_max_height_ratio, margin_left, margin_bottom, chatbox_duration_after_last, wrap_width):
    try:
        max_pixel_height = int(video_height * chatbox_max_height_ratio)
        header = f"""[Script Info]\nTitle: Converted from LRC to Chatbox\nScriptType: v4.00+\nPlayResX: {video_width}\nPlayResY: {video_height}\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Chatbox,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,{letter_spacing},0,1,0,0,1,0,0,{line_spacing},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
        with open(lrc_file, 'r', encoding='utf-8-sig') as f: lrc_content = f.readlines()
        pattern = re.compile(r'\[(\d{2}):(\d{2}):(\d{2})[.:](\d{2,3})\](.*)'); comments = []
        for line in lrc_content:
            m = pattern.search(line);
            if not m: continue
            hh, mm, ss, ms_s, txt = m.groups(); ms = int(ms_s.ljust(3, '0')); txt = txt.strip()
            if not txt: continue
            parts = re.split(r'\s+', txt, 1); formatted_txt = f"{parts[0]}:{parts[1]}" if len(parts) == 2 else txt
            wrapped_txt = wrap_text(formatted_txt, width=wrap_width); t = int(hh) * 3600 + int(mm) * 60 + int(ss) + ms / 1000
            comments.append((t, wrapped_txt))
        if not comments: return False, "警告：未在LRC文件中解析到任何弹幕！"
        comments.sort(key=lambda x: x[0]); events = []; line_h = font_size + line_spacing; pos_x = margin_left; pos_y = video_height - margin_bottom
        def fmt_time(t): h = int(t // 3600); m = int((t - h * 3600) // 60); s = t - h * 3600 - m * 60; cs = int((s - int(s)) * 100); return f"{h}:{m:02}:{int(s):02}.{cs:02}"
        for i, (start_t, _) in enumerate(comments):
            end_t = comments[i+1][0] if i+1 < len(comments) else start_t + chatbox_duration_after_last
            if end_t - start_t < 0.1: continue
            h_acc = 0; lines_to_display = []
            for j in range(i, -1, -1):
                comment_text = comments[j][1]; comment_height = (comment_text.count('\\N') + 1) * line_h
                separator_height = line_h if lines_to_display else 0
                if h_acc + comment_height + separator_height > max_pixel_height: break
                h_acc += comment_height + separator_height; lines_to_display.insert(0, comment_text)
            text = "\\N\\N".join(lines_to_display)
            x1, y1 = margin_left, pos_y - max_pixel_height; x2, y2 = video_width - margin_left, pos_y
            override = f"{{\\an1\\pos({pos_x},{pos_y})\\fs{font_size}\\fn{font_name}\\fsp{letter_spacing}\\clip({x1},{y1},{x2},{y2})}}"; full_text = f"{override}{text}"
            events.append(f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},Chatbox,,0,0,0,,{full_text}")
        with open(ass_file, 'w', encoding='utf-8-sig') as fw: fw.write(header); fw.write("\n".join(events))
        return True, f"成功生成 {len(events)} 条弹幕事件"
    except Exception as e: return False, f"生成ASS文件时发生严重错误: {e}"