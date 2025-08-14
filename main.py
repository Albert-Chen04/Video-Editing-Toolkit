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
    【最终稳定版】智能判断路径，完美兼容开发、--onedir、--onefile三种模式。
    """
    paths = {}
    is_packaged = getattr(sys, 'frozen', False)
    
    # --- 确定查找 'dependencies' 和 'assets' 等数据文件夹的根目录 (lookup_dir) ---
    
    if is_packaged:
        # 如果是打包后的程序
        if hasattr(sys, '_MEIPASS'):
            # --onefile 模式: 数据文件被解压到 _MEIPASS 临时文件夹
            lookup_dir = sys._MEIPASS
        else:
            # --onedir 模式: 数据文件和 exe 在同一级目录
            lookup_dir = os.path.dirname(sys.executable)
    else:
        # 开发模式: 数据文件在项目根目录
        lookup_dir = os.path.dirname(os.path.abspath(__file__))

    # base_path 用于加载资源，它应该和数据文件夹的查找路径一致
    paths['base'] = lookup_dir
    
    # --- FFmpeg 路径查找 ---
    # 1. 定义项目内部的期望路径
    dependencies_dir = os.path.join(lookup_dir, 'dependencies')
    project_ffmpeg_path = os.path.join(dependencies_dir, 'ffmpeg.exe')
    project_ffprobe_path = os.path.join(dependencies_dir, 'ffprobe.exe')
    
    # 2. 使用 find_executable 进行智能查找
    # 它会先检查项目内部路径，如果找不到，再检查系统PATH
    paths['ffmpeg'] = find_executable('ffmpeg.exe', project_ffmpeg_path)
    paths['ffprobe'] = find_executable('ffprobe.exe', project_ffprobe_path)
    
    return paths, is_packaged, dependencies_dir

if __name__ == '__main__':
    # 设置高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    app_paths, is_packaged, dependencies_dir = get_app_paths()

    # --- 【最终修复】将 'dependencies' 目录添加到 PATH 环境变量 ---
    # 这确保了像 whisper 这样的第三方库也能找到 ffmpeg
    if os.path.exists(dependencies_dir):
        os.environ['PATH'] = dependencies_dir + os.pathsep + os.environ.get('PATH', '')

    # --- 启动前检查FFmpeg是否找到 ---
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

    # 只有在找到FFmpeg后，才继续创建和显示主窗口
    window = MainWindow(paths=app_paths)
    window.show()
    sys.exit(app.exec())