# core/utils.py
# 文件作用：存放通用的、可在多个模块间共享的辅助函数。
# 主要提供基于FFmpeg/FFprobe的底层信息获取功能。

import subprocess
import os
import json
import shutil

def find_executable(name, project_path=None):
    """
    按优先级顺序查找一个可执行文件。
    1. 在项目指定的路径下查找 (如果提供了 project_path)。
    2. 在系统的 PATH 环境变量中查找。
    
    :param name: 可执行文件名 (例如 'ffmpeg.exe')
    :param project_path: 项目内指定的路径 (例如 'E:/Project/dependencies/ffmpeg.exe')
    :return: 可执行文件的有效路径，如果找不到则返回 None。
    """
    # 优先级1：检查项目内部路径
    if project_path and os.path.exists(project_path):
        return project_path
    
    # 优先级2：检查系统环境变量
    executable_path = shutil.which(name)
    if executable_path:
        return executable_path
        
    return None


def get_video_duration(video_path: str, ffprobe_path: str) -> float:
    """
    使用ffprobe获取视频的总时长（秒）。
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

def get_video_stream_info(video_path: str, ffprobe_path: str) -> (dict, str):
    """
    使用 ffprobe 获取视频文件的第一个视频流的详细信息。
    """
    if not os.path.exists(video_path):
        return None, f"错误：找不到视频文件 '{video_path}'"
    
    command = [
        ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "v:0",
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