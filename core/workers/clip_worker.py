# core/workers/clip_worker.py
import subprocess
import os
from PySide6.QtCore import QObject, Signal

from core.codec_config import build_video_command_with_codec, get_actual_codec_name

class BatchClipWorker(QObject):
    # 【修正】整个类的内容都需要缩进
    """
    在后台根据时间码列表，从一个源视频中裁剪出多个片段。
    """
    batch_finished = Signal()
    clip_started = Signal(str)
    clip_finished = Signal(int, str)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, source_video, clip_list, options):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.source_video = source_video
        self.clip_list = clip_list
        self.options = options
        self._is_running = True

    def run(self):
        total_clips = len(self.clip_list)
        output_dir = self.options['output_dir']
        ext = self.options['format']

        for i, clip_info in enumerate(self.clip_list):
            if not self._is_running:
                break
            
            clip_name = clip_info['name']
            start_time = clip_info['start']
            end_time = clip_info['end']

            progress_text = f"正在裁剪: {i + 1}/{total_clips} - {clip_name}"
            self.clip_started.emit(progress_text)
            
            # 使用临时数字文件名，防止特殊字符导致问题，完成后再重命名
            temp_filename = f"{i+1:03d}.{ext}"
            temp_filepath = os.path.join(output_dir, temp_filename).replace("\\", "/")

            command = ['-hide_banner', '-i', self.source_video, '-ss', start_time, '-to', end_time]
            
            is_audio_only = ext in ['aac', 'mp3', 'flac', 'wav', 'opus']
            if is_audio_only:
                codec_map = {"aac": "aac", "mp3": "libmp3lame", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
                command.extend(['-vn', '-c:a', codec_map.get(ext, 'aac')])
                command.extend(['-y', temp_filepath])
            else:
                # 使用统一的编码器配置
                codec = get_actual_codec_name(self.options['codec'])
                if codec == 'copy':
                    base_command = command + ['-c', 'copy']
                else:
                    base_command = command + ['-c:v', codec, '-c:a', 'copy']
                command = build_video_command_with_codec(base_command, codec, temp_filepath)
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")

            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            
            for line in iter(process.stdout.readline, ''):
                if not line: break
                self.log_message.emit(line.strip())
            
            process.wait()
            self.clip_finished.emit(process.returncode, temp_filepath)

        self.batch_finished.emit()

    def stop(self):
        self._is_running = False