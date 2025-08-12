# main.py
import sys
import os

# ==============================================================================
#  将项目根目录添加到Python的搜索路径中
# ==============================================================================
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
# ==============================================================================


from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from core.utils import find_executable
from ui.main_window import MainWindow

def get_app_paths():
    """
    智能判断路径，并使用多级回退策略查找FFmpeg。
    返回包含所有核心路径的字典。
    """
    paths = {}
    is_packaged = getattr(sys, 'frozen', False)
    
    if is_packaged and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    paths['base'] = base_path
    
    lookup_dir = os.path.dirname(sys.executable) if is_packaged else base_path
    project_ffmpeg_path = os.path.join(lookup_dir, 'dependencies', 'ffmpeg.exe')
    project_ffprobe_path = os.path.join(lookup_dir, 'dependencies', 'ffprobe.exe')
    
    paths['ffmpeg'] = find_executable('ffmpeg.exe', project_ffmpeg_path)
    paths['ffprobe'] = find_executable('ffprobe.exe', project_ffprobe_path)
    
    return paths

if __name__ == '__main__':
    # 【最终修复】使用PySide6推荐的、更现代的方法来启用高DPI
    # 这可以避免 DeprecationWarning
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    app_paths = get_app_paths()

    if not app_paths['ffmpeg'] or not app_paths['ffprobe']:
        error_msg = (
            "错误：未找到 FFmpeg 组件！\n\n"
            "请确保满足以下任一条件：\n"
            "1. (推荐) 将 ffmpeg.exe 和 ffprobe.exe 放置在程序目录下的 'dependencies' 文件夹中。\n"
            "2. 将您自己电脑上 FFmpeg 的路径添加到了系统环境变量(PATH)中。\n\n"
            "程序即将退出。"
        )
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(error_msg)
        msg_box.setWindowTitle("依赖缺失")
        msg_box.exec()
        
        sys.exit(1)

    window = MainWindow(paths=app_paths)
    window.show()
    sys.exit(app.exec())