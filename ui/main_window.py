# ui/main_window.py
import os
import sys
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QFileDialog, QApplication, QPushButton)
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtCore import Qt

# 导入每个功能选项卡的UI类
from ui.tabs.subtitle_tab import SubtitleTab
from ui.tabs.transcode_tab import TranscodeTab
from ui.tabs.clip_tab import ClipTab
from ui.tabs.vbg_tab import VideoFromBgTab
from ui.tabs.canvas_tab import CanvasTab
from ui.tabs.horizontal_tab import HorizontalTab
from ui.tabs.frame_export_tab import FrameExportTab
from ui.tabs.merge_tab import MergeTab
from ui.tabs.transcribe_tab import TranscribeTab

class MainWindow(QMainWindow):
    # 【最终修复】__init__ 方法现在接收一个 'paths' 字典作为参数
    def __init__(self, paths):
        super().__init__()

        # 【最终修复】不再进行智能判断，而是直接使用从 main.py 传递进来的路径
        self.base_path = paths['base']
        self.ffmpeg_path = paths['ffmpeg']
        self.ffprobe_path = paths['ffprobe']

        # --- 状态和实例变量 ---
        self.thread = None
        self.worker = None
        self.is_dark_mode = True  # 默认使用深色主题

        # --- 窗口基本设置 ---
        self.setWindowTitle("Video Editing Toolkit - v1.1.1")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(900, 700)

        # 设置窗口图标
        # 【修正】图标路径现在也基于 self.base_path
        icon_path = os.path.join(self.base_path, 'assets', 'favicon1.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 设置应用程序样式
        self.setup_styles()

        # --- 通用文件过滤器 ---
        self.video_filter = "视频文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm);;所有文件 (*.*)"
        self.media_filter = "媒体文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm *.mp3 *.aac *.m4a *.wav);;所有文件 (*.*)"

        # --- 创建主控件和功能标签页 ---
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(False)
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(True)
        self.setCentralWidget(self.tabs)

        # --- 实例化并添加每个功能选项卡 ---
        transcribe_tab_widget = TranscribeTab(self)
        canvas_tab_widget = CanvasTab(self)
        horizontal_tab_widget = HorizontalTab(self)
        subtitle_tab_widget = SubtitleTab(self)
        merge_tab_widget = MergeTab(self)
        transcode_tab_widget = TranscodeTab(self)
        clip_tab_widget = ClipTab(self)
        frame_export_tab = FrameExportTab(self)
        vbg_tab_widget = VideoFromBgTab(self)

        # --- 按期望的顺序将选项卡添加到主窗口 ---
        self.tabs.addTab(transcribe_tab_widget, "🎤 语音转文本")
        self.tabs.addTab(canvas_tab_widget, "📱 竖屏画布字幕")
        self.tabs.addTab(horizontal_tab_widget, "🖥️ 横屏字幕视频")
        self.tabs.addTab(subtitle_tab_widget, "💬 Chatbox弹幕")
        self.tabs.addTab(merge_tab_widget, "🔗 合并媒体")
        self.tabs.addTab(transcode_tab_widget, "🔄 批量转码")
        self.tabs.addTab(clip_tab_widget, "✂️ 批量裁剪")
        self.tabs.addTab(frame_export_tab, "🖼️ 静帧导出")
        self.tabs.addTab(vbg_tab_widget, "🎨 视频换背景")

        # 设置标签页图标（如果存在）
        self.setup_tab_icons()

        # 添加主题切换按钮
        self.add_theme_toggle_button()

    def setup_styles(self):
        """
        设置应用程序样式
        """
        # 设置应用程序样式
        QApplication.setStyle("Fusion")

        if self.is_dark_mode:
            # 深色主题
            self.set_dark_theme()
        else:
            # 浅色主题
            self.set_light_theme()

    def set_dark_theme(self):
        """
        设置深色主题
        """
        # 创建深色主题调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(palette)

        # 设置深色主题样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #333;
            }
            QTabBar::tab {
                background-color: #444;
                color: #ddd;
                padding: 10px 20px;
                margin: 2px;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #555;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #666;
            }
            QPushButton#themeToggle {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton#themeToggle:hover {
                background-color: #555;
            }
            QStatusBar::item {
                border: none;
            }
        """)

    def set_light_theme(self):
        """
        设置浅色主题
        """
        # 重置为默认调色板
        QApplication.setPalette(QApplication.style().standardPalette())

        # 设置浅色主题样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #333;
                padding: 10px 20px;
                margin: 2px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f0f0f0;
            }
            QPushButton#themeToggle {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton#themeToggle:hover {
                background-color: #d0d0d0;
            }
            QStatusBar::item {
                border: none;
            }
        """)

    def toggle_theme(self):
        """
        切换主题
        """
        self.is_dark_mode = not self.is_dark_mode
        self.setup_styles()
        # 更新按钮文本
        if self.is_dark_mode:
            self.theme_toggle_button.setText("☀️ 切换到浅色")
        else:
            self.theme_toggle_button.setText("🌙 切换到深色")

    def add_theme_toggle_button(self):
        """
        添加主题切换按钮到状态栏
        """
        self.theme_toggle_button = QPushButton("☀️ 切换到浅色" if self.is_dark_mode else "🌙 切换到深色")
        self.theme_toggle_button.setObjectName("themeToggle")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        
        # 将按钮添加到状态栏的永久部件区域，它会自动靠右显示
        self.statusBar().addPermanentWidget(self.theme_toggle_button)

    def setup_tab_icons(self):
        """
        为标签页设置图标
        """
        # 如果有图标文件，可以为每个标签页设置图标
        icons_dir = os.path.join(self.base_path, 'assets', 'icons')
        if os.path.exists(icons_dir):
            icon_files = {
                0: 'mic.png',        # 语音转文本
                1: 'phone.png',      # 竖屏画布字幕
                2: 'monitor.png',    # 横屏字幕视频
                3: 'chat.png',       # Chatbox弹幕
                4: 'merge.png',      # 合并媒体
                5: 'convert.png',    # 批量转码
                6: 'cut.png',        # 批量裁剪
                7: 'image.png',      # 静帧导出
                8: 'background.png'  # 视频换背景
            }

            for index, icon_name in icon_files.items():
                icon_path = os.path.join(icons_dir, icon_name)
                if os.path.exists(icon_path) and index < self.tabs.count():
                    self.tabs.setTabIcon(index, QIcon(icon_path))

    def browse_file(self, line_edit_widget, caption, file_filter="所有文件 (*.*)"):
        """
        打开文件选择对话框，并将选择的路径设置到指定的QLineEdit控件中。
        """
        file_path, _ = QFileDialog.getOpenFileName(self, caption, "", file_filter)
        if file_path:
            line_edit_widget.setText(file_path)

    def browse_output_dir(self, line_edit_widget):
        """
        打开文件夹选择对话框，并将选择的路径设置到指定的QLineEdit控件中。
        """
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if dir_path:
            line_edit_widget.setText(dir_path)