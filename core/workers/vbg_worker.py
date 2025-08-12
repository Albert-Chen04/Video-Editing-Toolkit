# core/workers/vbg_worker.py
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal
import ctypes

from core.utils import get_video_duration
from core.codec_config import get_codec_params

class VideoFromBgWorker(QObject):
    """
    在后台使用一张静态背景图和一个音频文件，合成为一个视频。
    【最终稳定版】:
    - 自动处理奇数分辨率，向下取偶。
    - 为CPU和N卡编码器分别应用针对静态图像的深度优化。
    - 使用安全的低帧率(2fps)，实现极致压缩与良好兼容性。
    - 精确控制输出时长，与音频源完全一致。
    - 【修正】移除不稳定的输入端硬件加速，确保兼容任意图片格式。
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
            codec_name = self.params.get('codec_name', 'CPU x264 (高兼容)')
            
            base_name, _ = os.path.splitext(os.path.basename(audio_source))
            output_file = os.path.join(output_dir, f"{base_name}_with_bg.{ext}").replace("\\", "/")
            
            self.log_message.emit("正在精确检测音频时长...")
            duration_secs = get_video_duration(audio_source, self.ffprobe_path)
            if duration_secs <= 0:
                self.finished.emit(-1, f"无法获取有效的音频时长: {audio_source}")
                return
            self.log_message.emit(f"✅ 精确时长为: {duration_secs} 秒")

            # 【最终修复】构建最稳定、兼容的FFmpeg命令
            command = [
                '-hide_banner', 
                '-framerate', '2',     # 使用2fps低帧率
                '-loop', '1',          # 让背景图循环
                '-i', bg_image,        # 输入1: 图片 (使用默认软件解码器，兼容所有格式)
                '-i', audio_source,    # 输入2: 音频
                # 滤镜链：先裁剪为偶数分辨率，再转为标准像素格式
                '-vf', 'crop=floor(iw/2)*2:floor(ih/2)*2,format=yuvj420p',
            ]
            
            if "CPU" in codec_name:
                command.extend(get_codec_params(codec_name))
                command.extend(['-tune', 'stillimage', '-threads', '0'])
            elif "N卡" in codec_name:
                base_params = get_codec_params(codec_name)
                command.extend(base_params)
                command.extend(['-preset', 'p1', '-rc', 'constqp', '-bf', '0'])
            else:
                 command.extend(get_codec_params(codec_name))

            command.extend(['-c:a', 'aac', '-b:a', '192k'])
            command.extend([
                '-t', str(duration_secs),
                '-shortest',
                '-y', output_file
            ])
            
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            
            duration = duration_secs
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
            
            return_code = ctypes.c_int32(process.returncode).value
            self.finished.emit(return_code, "处理完成！")
            
        except Exception as e:
            self.finished.emit(-1, f"发生严重错误: {e}")

    def stop(self):
        self._is_running = False