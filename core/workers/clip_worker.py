# core/workers/clip_worker.py
import subprocess
import os
from PySide6.QtCore import QObject, Signal

# 【新增】导入统一编码器配置模块
from core.codec_config import get_codec_params

class BatchClipWorker(QObject):
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
        # 【修改】获取编码器名称
        codec_name = self.options.get('codec_name', '直接复制 (无损/极速)')

        for i, clip_info in enumerate(self.clip_list):
            if not self._is_running:
                break
            
            clip_name = clip_info['name']
            start_time = clip_info['start']
            end_time = clip_info['end']

            progress_text = f"正在裁剪: {i + 1}/{total_clips} - {clip_name}"
            self.clip_started.emit(progress_text)
            
            temp_filename = f"{i+1:03d}.{ext}"
            temp_filepath = os.path.join(output_dir, temp_filename).replace("\\", "/")

            command = ['-hide_banner', '-i', self.source_video, '-ss', start_time, '-to', end_time]
            
            is_audio_only = ext in ['aac', 'mp3', 'flac', 'wav', 'opus']
            if is_audio_only:
                codec_map = {"aac": "aac", "mp3": "libmp3lame", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
                command.extend(['-vn', '-c:a', codec_map.get(ext, 'aac')])
            else:
                # 【修改】重构编码器参数逻辑
                if "直接复制" in codec_name:
                    command.extend(['-c', 'copy'])
                else:
                    # 获取动态编码参数
                    codec_params = get_codec_params(codec_name)
                    command.extend(codec_params)
                    # 对于重新编码视频的裁剪，音频流默认直接复制以提高速度
                    command.extend(['-c:a', 'copy'])
            
            command.extend(['-y', temp_filepath])
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