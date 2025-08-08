# core/workers/vbg_worker.py
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal

from core.utils import get_video_duration

class VideoFromBgWorker(QObject):
    """
    在后台使用一张静态背景图和一个音频文件，合成为一个视频。
    视频的尺寸由背景图的尺寸决定。
    """
    finished = Signal(int, str)
    progress = Signal(int)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, ffprobe_path, params):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.params = params
        self._is_running = True

    def run(self):
        try:
            audio_source = self.params['audio_source']
            bg_image = self.params['bg_image']
            output_dir = self.params['output_dir']
            ext = self.params['format']
            codec = self.params['codec'].split(" ")[0]
            # 【移除】不再需要分辨率和裁剪参数
            # resolution = self.params['resolution']
            # crop_filter = self.params.get('crop_filter', None)
            
            base_name, _ = os.path.splitext(os.path.basename(audio_source))
            output_file = os.path.join(output_dir, f"{base_name}_with_bg.{ext}").replace("\\", "/")
            
            # 【修改】构建简化的滤镜链。
            # FFmpeg会自动使用输入图片(-i bg_image)的尺寸作为输出视频的尺寸。
            # 我们只需要确保像素格式是通用的 yuv420p 即可。
            vf_chain = "format=yuv420p"
            
            command = [
                '-hide_banner', 
                '-loop', '1', '-i', bg_image, 
                '-i', audio_source,
                '-vf', vf_chain,
                '-c:v', codec, 
                '-c:a', 'aac', '-b:a', '192k', 
                '-shortest', # 以较短的输入（即音频）时长为准
                '-y', output_file
            ]
            
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            
            duration = get_video_duration(audio_source, self.ffprobe_path)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            
            for line in iter(process.stdout.readline, ''):
                if not self._is_running:
                    process.terminate()
                    break
                if not line: break
                line_strip = line.strip()
                self.log_message.emit(line_strip)
                match = time_pattern.search(line_strip)
                if match and duration > 0:
                    h, m, s, ms = map(int, match.groups())
                    current_seconds = h * 3600 + m * 60 + s + ms / 100
                    progress = int((current_seconds / duration) * 100)
                    self.progress.emit(min(progress, 100))

            process.wait()
            self.finished.emit(process.returncode, "处理完成！")
        except Exception as e:
            self.finished.emit(-1, f"发生严重错误: {e}")

    def stop(self):
        self._is_running = False