# core/workers/merge_worker.py
import subprocess
import os
from PySide6.QtCore import QObject, Signal

class MergeWorker(QObject):
    """
    在后台使用 FFmpeg 的 concat demuxer 合并多个媒体文件。
    """
    finished = Signal(int, str)
    log_message = Signal(str)
    progress = Signal(str)

    def __init__(self, ffmpeg_path, file_list, output_path):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.file_list = file_list
        self.output_path = output_path
        self._is_running = True

    def run(self):
        temp_list_file = None
        try:
            # 1. 创建一个临时的文本文件，列出所有要合并的文件
            # 这是 FFmpeg concat demuxer 的要求
            output_dir = os.path.dirname(self.output_path)
            temp_list_file = os.path.join(output_dir, "mergelist.txt")
            
            with open(temp_list_file, 'w', encoding='utf-8') as f:
                for file_path in self.file_list:
                    # FFmpeg 要求文件路径中的特殊字符需要转义，但作为 demuxer 的输入文件，
                    # 最好是路径本身是干净的。这里我们直接写入，并确保路径正确。
                    # 'file' 关键字是必须的
                    f.write(f"file '{file_path}'\n")
            
            self.log_message.emit("✅ 临时合并列表文件创建成功。")
            self.progress.emit("准备合并...")

            # 2. 构建 FFmpeg 命令
            # -f concat: 使用 concat demuxer
            # -safe 0: 允许使用绝对路径（重要！）
            # -i mergelist.txt: 输入文件列表
            # -c copy: 直接复制流，不重新编码，实现快速无损合并
            command = [
                self.ffmpeg_path,
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_file,
                '-c', 'copy',
                self.output_path
            ]

            self.log_message.emit(f"🚀 执行命令: {' '.join(command)}")
            self.progress.emit("正在合并文件，请稍候...")
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            
            for line in iter(process.stdout.readline, ''):
                if not line: break
                self.log_message.emit(line.strip())

            process.wait()

            if process.returncode == 0:
                self.log_message.emit(f"✅ 合并成功！输出文件位于:\n{self.output_path}")
                self.finished.emit(0, "所有文件合并成功！")
            else:
                self.log_message.emit(f"❌ 合并失败，FFmpeg 返回错误码: {process.returncode}")
                self.finished.emit(process.returncode, f"合并失败！请检查日志输出获取详细信息。")

        except Exception as e:
            error_msg = f"发生严重错误: {e}"
            self.log_message.emit(error_msg)
            self.finished.emit(-1, error_msg)
        finally:
            # 3. 清理临时的列表文件
            if temp_list_file and os.path.exists(temp_list_file):
                try:
                    os.remove(temp_list_file)
                    self.log_message.emit("ℹ️ 已清理临时文件。")
                except OSError:
                    pass

    def stop(self):
        self._is_running = False