# core/workers/transcode_worker.py
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal

from core.utils import get_video_duration
from core.codec_config import build_video_command_with_codec, get_actual_codec_name

class BatchTranscodeWorker(QObject):
    # 【修正】整个类的内容都需要缩进
    """
    在后台线程中执行批量转码/提取音频的任务。
    通过信号(Signal)与主UI线程通信，汇报进度和结果。
    """
    batch_finished = Signal()
    file_started = Signal(str)
    file_progress = Signal(int)
    file_finished = Signal(int)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, ffprobe_path, file_queue, transcode_options):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.file_queue = file_queue
        self.options = transcode_options
        self._is_running = True

    def run(self):
        total_files = len(self.file_queue)
        for i, input_file in enumerate(self.file_queue):
            if not self._is_running:
                break
                
            progress_text = f"正在处理: {i + 1}/{total_files} - {os.path.basename(input_file)}"
            self.file_started.emit(progress_text)
            self.file_progress.emit(0)

            selected_format = self.options['format']
            output_dir = self.options['output_dir']
            ext = selected_format.split(" ")[1] if "提取" in selected_format else selected_format
            base_name, _ = os.path.splitext(os.path.basename(input_file))
            output_file = os.path.join(output_dir, f"{base_name}_converted.{ext}").replace("\\", "/")

            command = ['-hide_banner', '-i', input_file]
            if "提取" in selected_format:
                codec_map = {"aac": "aac", "mp3": "libmp3lame", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
                command.extend(['-vn', '-c:a', codec_map.get(ext, 'aac')])
                command.extend(['-y', output_file])
            else:
                # 使用统一的编码器配置
                codec = get_actual_codec_name(self.options['codec'])
                if codec == 'copy':
                    base_command = command + ['-c', 'copy']
                else:
                    base_command = command + ['-c:v', codec, '-c:a', 'copy']
                command = build_video_command_with_codec(base_command, codec, output_file)

            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")

            duration = get_video_duration(input_file, self.ffprobe_path)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")

            for line in iter(process.stdout.readline, ''):
                if not line: break
                line_strip = line.strip()
                self.log_message.emit(line_strip)
                match = time_pattern.search(line_strip)
                if match and duration > 0:
                    h, m, s, ms = map(int, match.groups())
                    current_seconds = h * 3600 + m * 60 + s + ms / 100
                    progress = int((current_seconds / duration) * 100)
                    self.file_progress.emit(min(progress, 100))
            
            process.wait()
            self.file_finished.emit(process.returncode)
            
        self.batch_finished.emit()

    def stop(self):
        self._is_running = False