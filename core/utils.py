# core/utils.py
# 文件作用：存放通用的、可在多个模块间共享的辅助函数。
# 主要提供基于FFmpeg/FFprobe的底层信息获取功能。

import subprocess
import os
import json

def get_video_duration(video_path: str, ffprobe_path: str) -> float:
    """
    使用ffprobe获取视频的总时长（秒）。
    
    :param video_path: 视频文件路径。
    :param ffprobe_path: ffprobe.exe的路径。
    :return: 视频时长（浮点数），如果失败则返回0。
    """
    if not os.path.exists(video_path):
        return 0.0
    command = [
        ffprobe_path, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def get_video_dimensions(video_path: str, ffprobe_path: str) -> (int, int, str):
    """
    使用ffprobe获取视频的分辨率（宽和高）。
    
    :param video_path: 视频文件路径。
    :param ffprobe_path: ffprobe.exe的路径。
    :return: (宽度, 高度, 消息) 元组。成功时返回 (宽, 高, "成功消息")，失败时返回 (None, None, "错误消息")。
    """
    if not os.path.exists(video_path):
        return None, None, f"错误：找不到视频文件 '{video_path}'"
    command = [
        ffprobe_path, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        data = json.loads(result.stdout)
        width = data["streams"][0]["width"]
        height = data["streams"][0]["height"]
        return width, height, "视频尺寸检测成功"
    except Exception as e:
        return None, None, f"获取视频尺寸失败: {e}"

# 【新增】一个更强大的函数，用于获取视频流的详细信息
def get_video_stream_info(video_path: str, ffprobe_path: str) -> (dict, str):
    """
    使用 ffprobe 获取视频文件的第一个视频流的详细信息。

    :param video_path: 视频文件路径。
    :param ffprobe_path: ffprobe.exe 的路径。
    :return: (信息字典, 错误消息) 元组。成功时返回 (stream_info, None)，失败时返回 (None, error_message)。
    """
    if not os.path.exists(video_path):
        return None, f"错误：找不到视频文件 '{video_path}'"
    
    command = [
        ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "v:0", # 只选择第一个视频流
        video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            return data["streams"][0], None
        else:
            return None, "文件中未找到有效的视频流。"
    except Exception as e:
        return None, f"获取视频信息失败: {e}"