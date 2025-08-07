# core/ffmpeg_handler.py
import subprocess, re, os
from PySide6.QtCore import QObject, Signal

from .subtitle_converter import get_video_dimensions

def get_video_duration(video_path, ffprobe_path):
    if not os.path.exists(video_path): return 0
    command = [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception: return 0

class BatchTranscodeWorker(QObject):
    batch_finished = Signal()
    file_started = Signal(str)
    file_progress = Signal(int)
    file_finished = Signal(int)
    log_message = Signal(str)
    def __init__(self, ffmpeg_path, ffprobe_path, file_queue, transcode_options):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.ffprobe_path = ffprobe_path
        self.file_queue = file_queue; self.options = transcode_options
        self._is_running = True
    def run(self):
        total_files = len(self.file_queue)
        for i, input_file in enumerate(self.file_queue):
            if not self._is_running: break
            progress_text = f"正在处理: {i + 1}/{total_files} - {os.path.basename(input_file)}"
            self.file_started.emit(progress_text); self.file_progress.emit(0)
            selected_format = self.options['format']; output_dir = self.options['output_dir']
            ext = selected_format.split(" ")[1] if "提取" in selected_format else selected_format
            base_name, _ = os.path.splitext(os.path.basename(input_file))
            output_file = os.path.join(output_dir, f"{base_name}_converted.{ext}").replace("\\", "/")
            command = ['-hide_banner', '-i', input_file]
            if "提取" in selected_format:
                codec_map = {"aac": "aac", "mp3": "libmp3lame", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
                command.extend(['-vn', '-c:a', codec_map.get(ext, 'aac')])
            else:
                codec = self.options['codec'].split(" ")[0]
                command.extend(['-c:v', codec, '-c:a', 'copy'])
            command.extend(['-y', output_file])
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            duration = get_video_duration(input_file, self.ffprobe_path)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            for line in iter(process.stdout.readline, ''):
                if not line: break
                line_strip = line.strip(); self.log_message.emit(line_strip)
                match = time_pattern.search(line_strip)
                if match and duration > 0:
                    h, m, s, ms = map(int, match.groups()); current_seconds = h * 3600 + m * 60 + s + ms / 100
                    progress = int((current_seconds / duration) * 100)
                    self.file_progress.emit(min(progress, 100))
            process.wait()
            self.file_finished.emit(process.returncode)
        self.batch_finished.emit()
    def stop(self): self._is_running = False

class SubtitleBurnWorker(QObject):
    finished = Signal(int, str)
    progress = Signal(int)
    log_message = Signal(str)
    def __init__(self, ffmpeg_path, ffprobe_path, params, ass_converter):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.ffprobe_path = ffprobe_path
        self.params = params; self.lrc_to_ass_converter = ass_converter
        self._is_running = True
    def run(self):
        video_file = self.params['video_file']; lrc_file = self.params['lrc_file']; temp_ass_path = None
        output_dir = self.params['output_dir']
        try:
            self.log_message.emit("▶️ 任务开始...\n正在检测视频尺寸...");
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            if not width: self.finished.emit(-1, f"无法获取视频尺寸: {msg}"); return
            self.log_message.emit(f"✅ 视频尺寸: {width}x{height}")
            self.log_message.emit("正在转换LRC为ASS字幕文件...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(os.path.dirname(video_file), f"{base_name}_temp.ass").replace("\\", "/")
            success, msg = self.lrc_to_ass_converter(lrc_file=lrc_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success: self.finished.emit(-1, f"生成ASS字幕失败: {msg}"); return
            self.log_message.emit(f"✅ {msg}")
            output_file = os.path.join(output_dir, f"{base_name}_danmaku.mp4").replace("\\", "/")
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            codec = self.params['codec']
            command = ['-hide_banner', '-i', video_file, '-vf', f"ass=filename='{escaped_ass_path}'", '-c:v', codec, '-preset', 'p5', '-cq', '18', '-c:a', 'copy', '-y', output_file]
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            duration = get_video_duration(video_file, self.ffprobe_path)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            for line in iter(process.stdout.readline, ''):
                if not self._is_running: process.terminate(); break
                if not line: break
                line_strip = line.strip(); self.log_message.emit(line_strip)
                match = time_pattern.search(line_strip)
                if match and duration > 0:
                    h, m, s, ms = map(int, match.groups()); current_seconds = h * 3600 + m * 60 + s + ms / 100
                    progress = int((current_seconds / duration) * 100)
                    self.progress.emit(min(progress, 100))
            process.wait()
            self.finished.emit(process.returncode, "处理完成！")
        except Exception as e: self.finished.emit(-1, f"发生严重错误: {e}")
        finally:
            if temp_ass_path and os.path.exists(temp_ass_path):
                try: os.remove(temp_ass_path)
                except: pass
    def stop(self): self._is_running = False

class PreviewWorker(QObject):
    finished = Signal(bool, str)
    log_message = Signal(str)
    def __init__(self, ffmpeg_path, ffprobe_path, params, ass_converter):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.ffprobe_path = ffprobe_path
        self.params = params; self.lrc_to_ass_converter = ass_converter
    def run(self):
        temp_ass_path = None; temp_img_path = None
        try:
            video_file = self.params['video_file']; lrc_file = self.params['lrc_file']
            self.log_message.emit("正在获取视频信息...")
            width, height, msg = get_video_dimensions(video_file, self.ffprobe_path)
            duration = get_video_duration(video_file, self.ffprobe_path)
            if not (width and duration > 0): self.finished.emit(False, f"无法获取视频信息: {msg}"); return
            self.log_message.emit("正在生成ASS字幕文件...")
            base_name, _ = os.path.splitext(os.path.basename(video_file))
            temp_ass_path = os.path.join(self.params['base_path'], f"{base_name}_preview.ass").replace("\\", "/")
            success, msg = self.lrc_to_ass_converter(lrc_file=lrc_file, ass_file=temp_ass_path, video_width=width, video_height=height, **self.params['ass_options'])
            if not success: self.finished.emit(False, f"生成ASS字幕失败: {msg}"); return
            self.log_message.emit("正在截取预览帧...")
            preview_target_time = 120.0; seek_point = preview_target_time if duration > preview_target_time else duration / 2
            temp_img_path = os.path.join(self.params['base_path'], "preview.jpg")
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            vf_chain = f"scale=iw/2:ih/2,ass=filename='{escaped_ass_path}'"
            command = [self.ffmpeg_path, '-y', '-i', video_file, '-ss', str(seek_point), '-vf', vf_chain, '-vframes', '1', temp_img_path]
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if os.path.exists(temp_img_path): self.finished.emit(True, temp_img_path)
            else: self.finished.emit(False, f"生成预览图片失败！\n{result.stderr}")
        except subprocess.CalledProcessError as e: self.finished.emit(False, f"FFmpeg执行预览失败:\n{e.stderr}")
        except Exception as e: self.finished.emit(False, f"生成预览时发生未知错误: {e}")
        finally:
            if temp_ass_path and os.path.exists(temp_ass_path): os.remove(temp_ass_path)

class BatchClipWorker(QObject):
    batch_finished = Signal()
    clip_started = Signal(str)
    clip_finished = Signal(int, str)
    log_message = Signal(str)
    def __init__(self, ffmpeg_path, source_video, clip_list, options):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.source_video = source_video
        self.clip_list = clip_list; self.options = options
        self._is_running = True
    def run(self):
        total_clips = len(self.clip_list); output_dir = self.options['output_dir']; ext = self.options['format']
        for i, clip_info in enumerate(self.clip_list):
            if not self._is_running: break
            clip_name = clip_info['name']; start_time = clip_info['start']; end_time = clip_info['end']
            progress_text = f"正在裁剪: {i + 1}/{total_clips} - {clip_name}"; self.clip_started.emit(progress_text)
            temp_filename = f"{i+1:03d}.{ext}"; temp_filepath = os.path.join(output_dir, temp_filename).replace("\\", "/")
            command = ['-hide_banner', '-i', self.source_video, '-ss', start_time, '-to', end_time]
            is_audio_only = ext in ['aac', 'mp3', 'flac', 'wav', 'opus']
            if is_audio_only:
                codec_map = {"aac": "aac", "mp3": "libmp3lame", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
                command.extend(['-vn', '-c:a', codec_map.get(ext, 'aac')])
            else:
                codec = self.options['codec'].split(" ")[0]
                if codec == 'copy': command.extend(['-c', 'copy'])
                else: command.extend(['-c:v', codec, '-c:a', 'copy'])
            command.extend(['-y', temp_filepath])
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            for line in iter(process.stdout.readline, ''):
                if not line: break
                self.log_message.emit(line.strip())
            process.wait()
            self.clip_finished.emit(process.returncode, temp_filepath)
        self.batch_finished.emit()
    def stop(self): self._is_running = False

class VideoFromBgWorker(QObject):
    finished = Signal(int, str)
    progress = Signal(int)
    log_message = Signal(str)
    def __init__(self, ffmpeg_path, ffprobe_path, params):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.ffprobe_path = ffprobe_path
        self.params = params; self._is_running = True
    def run(self):
        try:
            audio_source = self.params['audio_source']; bg_image = self.params['bg_image']
            output_dir = self.params['output_dir']; resolution = self.params['resolution']
            ext = self.params['format']; codec = self.params['codec'].split(" ")[0]
            crop_filter = self.params.get('crop_filter', None) # 【新增】获取裁剪滤镜
            base_name, _ = os.path.splitext(os.path.basename(audio_source))
            output_file = os.path.join(output_dir, f"{base_name}_with_bg.{ext}").replace("\\", "/")
            
            # 构建滤镜链
            vf_chain = []
            if crop_filter: vf_chain.append(crop_filter)
            vf_chain.append(f"scale={resolution}:flags=lanczos")
            vf_chain.append("format=yuv420p")
            
            command = [
                '-hide_banner', '-loop', '1', '-i', bg_image, '-i', audio_source,
                '-vf', ",".join(vf_chain), # 将滤镜用逗号连接
                '-c:v', codec, '-c:a', 'aac', '-b:a', '192k', '-shortest', '-y', output_file
            ]
            
            self.log_message.emit(f"🚀 执行命令: {' '.join(['ffmpeg'] + command)}")
            process = subprocess.Popen([self.ffmpeg_path] + command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            duration = get_video_duration(audio_source, self.ffprobe_path)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            for line in iter(process.stdout.readline, ''):
                if not self._is_running: process.terminate(); break
                if not line: break
                line_strip = line.strip(); self.log_message.emit(line_strip)
                match = time_pattern.search(line_strip)
                if match and duration > 0:
                    h, m, s, ms = map(int, match.groups()); current_seconds = h * 3600 + m * 60 + s + ms / 100
                    progress = int((current_seconds / duration) * 100)
                    self.progress.emit(min(progress, 100))
            process.wait()
            self.finished.emit(process.returncode, "处理完成！")
        except Exception as e:
            self.finished.emit(-1, f"发生严重错误: {e}")
    def stop(self): self._is_running = False