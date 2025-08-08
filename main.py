# main.py
import sys
import os

# ==============================================================================
#  【核心修正】 将项目根目录添加到Python的搜索路径中
# ==============================================================================
#  获取此脚本(main.py)所在的目录的绝对路径。
#  这正是我们的项目根目录。
project_root = os.path.dirname(os.path.abspath(__file__))

#  将这个路径插入到sys.path列表的最前面。
#  这样Python在寻找模块时，会第一个检查我们的项目文件夹。
sys.path.insert(0, project_root)
# ==============================================================================


# 现在路径已经设置好了，我们可以安全地从项目的任何地方导入模块。
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())