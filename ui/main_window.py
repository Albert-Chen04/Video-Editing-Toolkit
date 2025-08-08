# ui/main_window.py
# 文件作用：应用程序的主窗口框架。
# 它的职责是初始化窗口、设置依赖路径、并作为容器组装所有从 ui.tabs 导入的功能模块。

import os
import sys
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QFileDialog)
from PySide6.QtGui import QIcon

# 导入每个功能选项卡的UI类
from ui.tabs.subtitle_tab import SubtitleTab
from ui.tabs.transcode_tab import TranscodeTab
from ui.tabs.clip_tab import ClipTab
from ui.tabs.vbg_tab import VideoFromBgTab
from ui.tabs.canvas_tab import CanvasTab
from ui.tabs.horizontal_tab import HorizontalTab
from ui.tabs.frame_export_tab import FrameExportTab
from ui.tabs.merge_tab import MergeTab
# 【新增】导入新的“语音转文本”功能选项卡类
from ui.tabs.transcribe_tab import TranscribeTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- 智能判断路径，兼容开发和打包环境 ---
        if getattr(sys, 'frozen', False):
            # 如果程序被PyInstaller打包
            self.base_path = sys._MEIPASS
            self.ffmpeg_path = os.path.join(self.base_path, 'ffmpeg.exe')
            self.ffprobe_path = os.path.join(self.base_path, 'ffprobe.exe')
        else:
            # 如果是直接运行 .py 脚本 (开发环境)
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.ffmpeg_path = os.path.join(self.base_path, 'dependencies', 'ffmpeg.exe')
            self.ffprobe_path = os.path.join(self.base_path, 'dependencies', 'ffprobe.exe')

        # --- 状态和实例变量 ---
        # 线程和worker的管理已下放给各自的Tab负责
        self.thread = None
        self.worker = None

        # --- 窗口基本设置 ---
        self.setWindowTitle("Video Editing Toolkit-v-1.1.0测试版")
        self.setGeometry(100, 100, 900, 800)
        icon_path = os.path.join(self.base_path, 'assets', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # --- 通用文件过滤器 ---
        self.video_filter = "视频文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm);;所有文件 (*.*)"
        self.media_filter = "媒体文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm *.mp3 *.aac *.m4a *.wav);;所有文件 (*.*)"
        
        # --- 创建主控件和功能标签页 ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # --- 实例化并添加每个功能选项卡 ---
        # 【新增】实例化新的语音转文本功能页
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
        # 【新增】将新功能页添加到第一个位置
        self.tabs.addTab(transcribe_tab_widget, "语音转文本")
        
        self.tabs.addTab(canvas_tab_widget, "竖屏画布字幕视频")
        self.tabs.addTab(horizontal_tab_widget, "横屏字幕视频")
        self.tabs.addTab(subtitle_tab_widget, "Chatbox弹幕视频")
        self.tabs.addTab(merge_tab_widget, "合并媒体")
        self.tabs.addTab(transcode_tab_widget, "批量转码")
        self.tabs.addTab(clip_tab_widget, "批量裁剪")
        self.tabs.addTab(frame_export_tab, "静帧导出")
        self.tabs.addTab(vbg_tab_widget, "视频换背景")
        

    # --- 通用辅助方法 ---
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