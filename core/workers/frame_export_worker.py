# core/workers/frame_export_worker.py
import subprocess
import os
from PySide6.QtCore import QObject, Signal

class FrameExportWorker(QObject):
    """
    在后台使用FFmpeg从视频的指定时间戳导出一帧高质量的静态图片。
    """
    finished = Signal(bool, str)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, video_file, timestamp_secs, output_path):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.video_file = video_file
        self.timestamp_secs = timestamp_secs
        self.output_path = output_path

    def run(self):
        try:
            self.log_message.emit(f"准备从 {self.timestamp_secs:.3f}s 处导出静帧...")
            
            # -ss: 定位到指定时间戳
            # -i: 输入文件
            # -vframes 1: 只导出一帧
            # -q:v 2: 对于JPG是高质量，对于PNG则几乎是无损
            command = [
                self.ffmpeg_path,
                '-y',
                '-ss', str(self.timestamp_secs),
                '-i', self.video_file,
                '-vframes', '1',
                '-q:v', '2',
                self.output_path
            ]
            
            self.log_message.emit(f"🚀 执行命令: {' '.join(command)}")
            
            # 使用 subprocess.run 因为这是一个短暂、一次性的任务
            result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

            if os.path.exists(self.output_path):
                self.log_message.emit(f"✅ 静帧导出成功: {self.output_path}")
                self.finished.emit(True, self.output_path)
            else:
                error_msg = f"导出失败，未找到输出文件。\nFFmpeg输出:\n{result.stderr}"
                self.log_message.emit(f"❌ {error_msg}")
                self.finished.emit(False, error_msg)

        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg执行失败 (返回码 {e.returncode}):\n{e.stderr}"
            self.log_message.emit(f"❌ {error_msg}")
            self.finished.emit(False, error_msg)
        except Exception as e:
            error_msg = f"发生未知错误: {e}"
            self.log_message.emit(f"❌ {error_msg}")
            self.finished.emit(False, error_msg)