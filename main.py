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
    【最终稳定版】智能判断路径，完美兼容开发和打包模式，
    并确保能识别用户自己配置的全局FFmpeg。
    """
    paths = {}
    is_packaged = getattr(sys, 'frozen', False)
    
    # --- 确定 base_path ---
    # base_path 是我们查找 assets 等内部资源的基准
    if is_packaged:
        if hasattr(sys, '_MEIPASS'):
            # --onefile 模式, 资源在 _MEIPASS 临时文件夹
            base_path = sys._MEIPASS
        else:
            # --onedir 模式, 资源和 exe 在同一级目录
            base_path = os.path.dirname(sys.executable)
    else:
        # 开发模式, 资源在项目根目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    paths['base'] = base_path
    
    # --- FFmpeg 路径查找 (保留您的核心功能) ---
    
    # 1. 定义项目内部的期望路径
    #    这个路径是相对于 base_path 的，对于所有模式都有效
    project_ffmpeg_path = os.path.join(base_path, 'dependencies', 'ffmpeg.exe')
    project_ffprobe_path = os.path.join(base_path, 'dependencies', 'ffprobe.exe')
    
    # 2. 使用 find_executable 进行智能查找
    #    它会先检查我们定义的 project_..._path，如果找不到，再检查系统PATH
    paths['ffmpeg'] = find_executable('ffmpeg.exe', project_ffmpeg_path)
    paths['ffprobe'] = find_executable('ffprobe.exe', project_ffprobe_path)
    
    # --- 为第三方库设置 PATH ---
    # 这一步是为了让 whisper 等库也能找到 ffmpeg
    if paths['ffmpeg']:
        ffmpeg_dir = os.path.dirname(paths['ffmpeg'])
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
    
    return paths, is_packaged

if __name__ == '__main__':
    # 设置高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    app_paths, is_packaged = get_app_paths()

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