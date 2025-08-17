# core/workers/subtitle_worker.py
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal

from core.utils import get_video_duration, get_video_dimensions
from core.codec_config import get_codec_params

class SubtitleBurnWorker(QObject):
    """
    【已重构】在后台执行ASS的转换，并使用FFmpeg将字幕烧录到视频中。
    这是一个通用的Worker，具体转换逻辑由传入的 ass_converter 决定。
    """
    finished = Signal(int, str)
    progress = Signal(int)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, ffprobe_path, params, ass_converter):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.params = params
        # 【修改】变量名 lrc_to_ass_converter 改为 ass_converter
        self.ass_converter = ass_converter
        self._is_running = True

    def run(self):
        video_file = self.params['video_file']
        # 【修改】变量名 lrc_file 改为 subtitle_file 以保持通用性
        subtitle_file = self.params['lrc_file']
        output_dir = self.params['output_dir']
        temp_ass_path = None
        
        try:
            self.log_message.emit("▶️ 任务开始...\n正在检测视频尺寸...");
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            if not width:
                self.finished.emit(-1, f"无法获取视频尺寸: {msg}")
                return
            self.log_message.emit(f"✅ 视频尺寸: {width}x{height}")

            self.log_message.emit("正在转换字幕文件为ASS格式...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(os.path.dirname(video_file), f"{base_name}_temp.ass").replace("\\", "/")
            
            # 动态调用传入的转换函数
            # 【修改】参数名 lrc_file 改为 subtitle_file (对于chatbox来说就是lrc_file)
            success, msg = self.ass_converter(lrc_file=subtitle_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success:
                self.finished.emit(-1, f"生成ASS字幕失败: {msg}")
                return
            self.log_message.emit(f"✅ {msg}")

            output_format = self.params['output_format']
            output_file = os.path.join(output_dir, f"{base_name}_danmaku.{output_format}").replace("\\", "/")
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            
            command = [
                '-hide_banner', '-i', video_file, 
                '-vf', f"ass=filename='{escaped_ass_path}'"
            ]

            codec_name = self.params.get('codec_name', 'CPU x264 (高兼容)')
            codec_params = get_codec_params(codec_name)
            command.extend(codec_params)
            
            command.extend(['-c:a', 'aac', '-b:a', '192k'])
            command.extend(['-y', output_file])
            
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            
            duration = get_video_duration(video_file, self.ffprobe_path)
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
        finally:
            if temp_ass_path and os.path.exists(temp_ass_path):
                try:
                    os.remove(temp_ass_path)
                except OSError:
                    pass

    def stop(self):
        self._is_running = False

class PreviewWorker(QObject):
    """
    在后台生成带字幕效果的单帧预览图。
    """
    finished = Signal(bool, str)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, ffprobe_path, params, ass_converter):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.params = params
        # 【修改】变量名 lrc_to_ass_converter 改为 ass_converter
        self.ass_converter = ass_converter

    def run(self):
        temp_ass_path = None
        temp_img_path = None
        try:
            video_file = self.params['video_file']
            # 【修改】变量名 lrc_file 改为 subtitle_file
            subtitle_file = self.params['lrc_file']
            
            self.log_message.emit("正在获取视频信息...")
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            duration = get_video_duration(video_file, self.ffprobe_path)
            if not (width and duration > 0):
                self.finished.emit(False, f"无法获取视频信息: {msg}")
                return

            self.log_message.emit("正在生成ASS字幕文件...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(self.params['base_path'], f"{base_name}_preview.ass").replace("\\", "/")
            
            # 【修改】参数名 lrc_file 改为 subtitle_file
            success, msg = self.ass_converter(lrc_file=subtitle_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success:
                self.finished.emit(False, f"生成ASS字幕失败: {msg}")
                return

            self.log_message.emit("正在截取预览帧...")
            preview_target_time = 120.0
            seek_point = preview_target_time if duration > preview_target_time else duration / 2
            temp_img_path = os.path.join(self.params['base_path'], "preview.jpg")
            
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            vf_chain = f"ass=filename='{escaped_ass_path}'"
            
            command = [self.ffmpeg_path, '-y', '-i', video_file, '-ss', str(seek_point), '-vf', vf_chain, '-vframes', '1', temp_img_path]
            
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

            if os.path.exists(temp_img_path):
                self.finished.emit(True, temp_img_path)
            else:
                self.finished.emit(False, f"生成预览图片失败！\n{result.stderr}")

        except subprocess.CalledProcessError as e:
            self.finished.emit(False, f"FFmpeg执行预览失败:\n{e.stderr}")
        except Exception as e:
            self.finished.emit(False, f"生成预览时发生未知错误: {e}")
        finally:
            if temp_ass_path and os.path.exists(temp_ass_path):
                try:
                    os.remove(temp_ass_path)
                except OSError:
                    pass