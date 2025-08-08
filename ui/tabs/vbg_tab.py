# ui/tabs/vbg_tab.py

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QProgressBar, QComboBox, QTextEdit, QMessageBox, QGridLayout, QApplication)
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.vbg_worker import VideoFromBgWorker
from core.codec_config import get_codec_options_for_ui
# 【移除】不再需要 ImageCropDialog
# from ui.dialogs import ImageCropDialog

class VideoFromBgTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.thread = None
        self.worker = None
        # 【移除】不再需要裁剪参数
        # self.vbg_crop_filter = None

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        # --- 输入 ---
        self.vbg_audio_source = QLineEdit()
        self.vbg_audio_browse_btn = QPushButton("浏览音频/视频源...")
        self.vbg_bg_image = QLineEdit()
        self.vbg_bg_browse_btn = QPushButton("浏览背景图片...")
        # 【移除】裁剪按钮
        # self.vbg_preview_crop_btn = QPushButton("裁剪预览...")
        
        # --- 输出 ---
        self.vbg_output_dir = QLineEdit()
        self.vbg_output_browse_btn = QPushButton("浏览...")
        
        # --- 参数 ---
        # 【移除】分辨率下拉框
        # self.vbg_resolution_combo = QComboBox()
        # self.vbg_resolution_combo.addItems(["1920x1080 (1080p 横屏)", "1080x1920 (1080p 竖屏)", "1280x720 (720p 横屏)"])
        self.vbg_format_combo = QComboBox()
        self.vbg_format_combo.addItems(["mp4", "mkv", "mov", "flv", "ts"])
        self.vbg_codec_combo = QComboBox()
        self.vbg_codec_combo.addItems(get_codec_options_for_ui(include_copy=False, include_h265=True))
        
        # --- 进度和日志 ---
        self.vbg_progress_bar = QProgressBar()
        self.vbg_progress_bar.setVisible(False)
        self.vbg_log_output = QTextEdit()
        self.vbg_log_output.setReadOnly(True)
        self.start_vbg_button = QPushButton("开始合成")
        
        # --- 设置默认选项 ---
        self.vbg_codec_combo.setCurrentText("h264_nvenc (N卡)")

    def create_layouts(self):
        layout = QVBoxLayout(self)

        audio_source_layout = QHBoxLayout()
        audio_source_layout.addWidget(QLabel("音频源文件:"))
        audio_source_layout.addWidget(self.vbg_audio_source)
        audio_source_layout.addWidget(self.vbg_audio_browse_btn)

        bg_image_layout = QHBoxLayout()
        bg_image_layout.addWidget(QLabel("背景图片:"))
        bg_image_layout.addWidget(self.vbg_bg_image)
        bg_image_layout.addWidget(self.vbg_bg_browse_btn)
        # 【移除】裁剪按钮的布局
        # bg_image_layout.addWidget(self.vbg_preview_crop_btn)

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("输出文件夹:"))
        output_path_layout.addWidget(self.vbg_output_dir)
        output_path_layout.addWidget(self.vbg_output_browse_btn)

        params_layout = QGridLayout()
        # 【移除】分辨率相关的布局
        # params_layout.addWidget(QLabel("输出分辨率:"), 0, 0)
        # params_layout.addWidget(self.vbg_resolution_combo, 0, 1)
        params_layout.addWidget(QLabel("输出格式:"), 0, 0)
        params_layout.addWidget(self.vbg_format_combo, 0, 1)
        params_layout.addWidget(QLabel("视频编码器:"), 1, 0)
        params_layout.addWidget(self.vbg_codec_combo, 1, 1)

        layout.addLayout(audio_source_layout)
        layout.addLayout(bg_image_layout)
        layout.addLayout(output_path_layout)
        layout.addLayout(params_layout)
        layout.addStretch()
        layout.addWidget(self.vbg_progress_bar)
        layout.addWidget(QLabel("日志输出:"))
        layout.addWidget(self.vbg_log_output)
        layout.addWidget(self.start_vbg_button, alignment=Qt.AlignCenter)

    def create_connections(self):
        self.vbg_audio_browse_btn.clicked.connect(lambda: self.main_window.browse_file(self.vbg_audio_source, "选择音频或视频源", self.main_window.media_filter))
        self.vbg_audio_source.textChanged.connect(self.update_vbg_output_dir)
        self.vbg_bg_browse_btn.clicked.connect(lambda: self.main_window.browse_file(self.vbg_bg_image, "选择背景图片", "图片文件 (*.jpg *.jpeg *.png)"))
        # 【移除】裁剪按钮的连接
        # self.vbg_preview_crop_btn.clicked.connect(self.open_crop_dialog)
        self.vbg_output_browse_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.vbg_output_dir))
        self.start_vbg_button.clicked.connect(self.start_video_from_bg)
        
    def update_vbg_output_dir(self):
        audio_path = self.vbg_audio_source.text()
        if audio_path and os.path.exists(audio_path):
             self.vbg_output_dir.setText(os.path.dirname(audio_path))

    # 【移除】整个 open_crop_dialog 方法
    # def open_crop_dialog(self): ...

    def start_video_from_bg(self):
        audio_source = self.vbg_audio_source.text()
        bg_image = self.vbg_bg_image.text()
        output_dir = self.vbg_output_dir.text()

        if not (audio_source and os.path.exists(audio_source)):
            QMessageBox.warning(self, "错误", "请选择一个有效的音频/视频源文件！")
            return
        if not (bg_image and os.path.exists(bg_image)):
            QMessageBox.warning(self, "错误", "请选择一个有效的背景图片！")
            return
        if not (output_dir and os.path.isdir(output_dir)):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！")
            return

        self.set_controls_enabled(False)
        self.vbg_log_output.clear()
        self.vbg_progress_bar.setVisible(True)
        self.vbg_progress_bar.setValue(0)
        
        # 【修改】简化传递的参数，不再包含分辨率和裁剪信息
        params = {
            'audio_source': audio_source, 
            'bg_image': bg_image, 
            'output_dir': output_dir,
            'format': self.vbg_format_combo.currentText(),
            'codec': self.vbg_codec_combo.currentText()
        }
        
        self.thread = QThread()
        self.worker = VideoFromBgWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, params)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.vbg_log_output.append)
        self.worker.progress.connect(self.vbg_progress_bar.setValue)
        self.worker.finished.connect(self.on_vbg_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_vbg_finished(self, return_code, message):
        self.vbg_progress_bar.setValue(100)
        QApplication.processEvents()
        if return_code == 0:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        
        self.set_controls_enabled(True)
        self.vbg_progress_bar.setVisible(False)

    def set_controls_enabled(self, enabled: bool):
        self.start_vbg_button.setEnabled(enabled)
        self.vbg_audio_browse_btn.setEnabled(enabled)
        self.vbg_bg_browse_btn.setEnabled(enabled)
        self.vbg_output_browse_btn.setEnabled(enabled)