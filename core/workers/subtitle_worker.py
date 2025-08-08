# core/workers/subtitle_worker.py
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal

from core.utils import get_video_duration, get_video_dimensions
from core.codec_config import build_video_command_with_codec, get_actual_codec_name

class SubtitleBurnWorker(QObject):
    # 【修正】整个类的内容都需要缩进
    """
    在后台执行LRC到ASS的转换，并使用FFmpeg将字幕烧录到视频中。
    """
    finished = Signal(int, str)
    progress = Signal(int)
    log_message = Signal(str)

    def __init__(self, ffmpeg_path, ffprobe_path, params, ass_converter):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.params = params
        self.lrc_to_ass_converter = ass_converter
        self._is_running = True

    def run(self):
        video_file = self.params['video_file']
        lrc_file = self.params['lrc_file']
        output_dir = self.params['output_dir']
        temp_ass_path = None
        
        try:
            self.log_message.emit("▶️ 任务开始...\n正在检测视频尺寸...");
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            if not width:
                self.finished.emit(-1, f"无法获取视频尺寸: {msg}")
                return
            self.log_message.emit(f"✅ 视频尺寸: {width}x{height}")

            self.log_message.emit("正在转换LRC为ASS字幕文件...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(os.path.dirname(video_file), f"{base_name}_temp.ass").replace("\\", "/")
            
            # 动态调用传入的转换函数
            success, msg = self.lrc_to_ass_converter(lrc_file=lrc_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success:
                self.finished.emit(-1, f"生成ASS字幕失败: {msg}")
                return
            self.log_message.emit(f"✅ {msg}")

            # 从参数中获取用户选择的视频格式
            output_format = self.params['output_format']
            output_file = os.path.join(output_dir, f"{base_name}_danmaku.{output_format}").replace("\\", "/")
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            
            # 使用统一的编码器配置
            codec = get_actual_codec_name(self.params['codec'])
            base_command = [
                '-hide_banner', '-i', video_file, 
                '-vf', f"ass=filename='{escaped_ass_path}'", 
                '-c:v', codec, 
                '-c:a', 'copy'
            ]
            
            command = build_video_command_with_codec(base_command, codec, output_file)
            
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
    # 【修正】整个类的内容都需要缩进
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
        self.lrc_to_ass_converter = ass_converter

    def run(self):
        temp_ass_path = None
        temp_img_path = None
        try:
            video_file = self.params['video_file']
            lrc_file = self.params['lrc_file']
            
            self.log_message.emit("正在获取视频信息...")
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            duration = get_video_duration(video_file, self.ffprobe_path)
            if not (width and duration > 0):
                self.finished.emit(False, f"无法获取视频信息: {msg}")
                return

            self.log_message.emit("正在生成ASS字幕文件...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(self.params['base_path'], f"{base_name}_preview.ass").replace("\\", "/")
            
            success, msg = self.lrc_to_ass_converter(lrc_file=lrc_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success:
                self.finished.emit(False, f"生成ASS字幕失败: {msg}")
                return

            self.log_message.emit("正在截取预览帧...")
            preview_target_time = 120.0
            seek_point = preview_target_time if duration > preview_target_time else duration / 2
            temp_img_path = os.path.join(self.params['base_path'], "preview.jpg")
            
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            # 预览时将视频缩小一半，加快处理速度
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
                os.remove(temp_ass_path)