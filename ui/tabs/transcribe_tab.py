# ui/tabs/transcribe_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QProgressBar, QComboBox, QTextEdit, QMessageBox, QGridLayout,
                               QFrame, QCheckBox, QGroupBox)
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.transcribe_worker import TranscribeWorker

class TranscribeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None

        # Language mapping from display name to Whisper code
        self.language_map = {
            "自动检测": "auto",
            "简体中文": "zh-hans", # 【新增】简体中文选项
            "中文": "zh",       # 这个可以保留，作为通用中文或繁体中文的备用
            "英语": "en",
            "日语": "ja",
            "韩语": "ko",
            "粤语": "yue",
            "法语": "fr",
            "德语": "de",
            "西班牙语": "es",
            "俄语": "ru",
            "葡萄牙语": "pt",
            "意大利语": "it",
        }
        
        # Available Whisper models
        self.model_list = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"]

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.set_default_settings()

    def create_widgets(self):
        # --- Input ---
        self.media_file_path = QLineEdit()
        self.browse_media_btn = QPushButton("浏览文件...")

        # --- Output ---
        self.output_dir_edit = QLineEdit()
        self.browse_output_btn = QPushButton("浏览文件夹...")
        self.output_filename_edit = QLineEdit()

        # --- Parameters ---
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.model_list)
        self.language_combo = QComboBox()
        self.language_combo.addItems(self.language_map.keys())
        
        # 【新增】计算设备选择框
        self.device_combo = QComboBox()
        self.device_combo.addItems(["自动 (优先GPU)", "GPU (CUDA)", "CPU"])
        
        # --- Export Formats ---
        self.export_groupbox = QGroupBox("导出格式 (可多选)")
        self.chk_lrc = QCheckBox("LRC (歌词文件)")
        self.chk_txt = QCheckBox("TXT (带时间戳)") # 【修改】明确TXT带时间戳
        self.chk_srt = QCheckBox("SRT (字幕)")
        self.chk_vtt = QCheckBox("VTT (WebVTT 字幕)")
        self.chk_lrc.setChecked(True)
        # self.chk_txt.setChecked(True) # 默认也勾选TXT

        # --- Control & Feedback ---
        self.start_button = QPushButton("开始转录")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100) # 【修改】设置固定范围

    def create_layouts(self):
        main_layout = QVBoxLayout(self)

        # --- Input/Output Section ---
        io_frame = QFrame()
        io_layout = QGridLayout(io_frame)
        io_layout.addWidget(QLabel("媒体文件:"), 0, 0)
        io_layout.addWidget(self.media_file_path, 0, 1)
        io_layout.addWidget(self.browse_media_btn, 0, 2)
        io_layout.addWidget(QLabel("输出文件夹:"), 1, 0)
        io_layout.addWidget(self.output_dir_edit, 1, 1)
        io_layout.addWidget(self.browse_output_btn, 1, 2)
        io_layout.addWidget(QLabel("输出文件名 (不含后缀):"), 2, 0)
        io_layout.addWidget(self.output_filename_edit, 2, 1, 1, 2)

        # --- Parameters Section ---
        params_frame = QFrame()
        params_layout = QGridLayout(params_frame) # 【修改】使用网格布局更整齐
        params_layout.addWidget(QLabel("识别模型:"), 0, 0)
        params_layout.addWidget(self.model_combo, 0, 1)
        params_layout.addWidget(QLabel("识别语言:"), 0, 2)
        params_layout.addWidget(self.language_combo, 0, 3)
        # 【新增】添加设备选择到布局中
        params_layout.addWidget(QLabel("计算设备:"), 1, 0)
        params_layout.addWidget(self.device_combo, 1, 1)
        params_layout.setColumnStretch(1, 1) # 让下拉框部分占据更多空间
        params_layout.setColumnStretch(3, 1)

        # --- Export Formats Layout ---
        export_layout = QHBoxLayout(self.export_groupbox)
        export_layout.addWidget(self.chk_lrc)
        export_layout.addWidget(self.chk_txt)
        export_layout.addWidget(self.chk_srt)
        export_layout.addWidget(self.chk_vtt)
        export_layout.addStretch()
        
        main_layout.addWidget(io_frame)
        main_layout.addWidget(params_frame)
        main_layout.addWidget(self.export_groupbox)
        main_layout.addStretch()
        main_layout.addWidget(QLabel("日志输出:"))
        main_layout.addWidget(self.log_output)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.start_button)

    def create_connections(self):
        self.browse_media_btn.clicked.connect(lambda: self.main_window.browse_file(self.media_file_path, "选择媒体文件", "所有文件 (*.*)"))
        self.browse_output_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.output_dir_edit))
        self.media_file_path.textChanged.connect(self.update_defaults_from_path)
        self.start_button.clicked.connect(self.start_transcription)

    def set_default_settings(self):
        self.model_combo.setCurrentText("base")
        self.language_combo.setCurrentText("自动检测")
    
    def update_defaults_from_path(self, path):
        if path and os.path.exists(path):
            dir_name = os.path.dirname(path)
            base_name = os.path.splitext(os.path.basename(path))[0]
            self.output_dir_edit.setText(dir_name)
            self.output_filename_edit.setText(base_name)

    def _get_current_params(self):
        media_file = self.media_file_path.text()
        output_dir = self.output_dir_edit.text()
        output_filename = self.output_filename_edit.text()

        if not (media_file and os.path.exists(media_file)):
            QMessageBox.warning(self, "错误", "请先选择一个有效的媒体文件！"); return None
        if not (output_dir and os.path.isdir(output_dir)):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return None
        if not output_filename:
            QMessageBox.warning(self, "错误", "请输入输出文件名！"); return None
            
        selected_formats = []
        if self.chk_lrc.isChecked(): selected_formats.append('lrc')
        if self.chk_txt.isChecked(): selected_formats.append('txt')
        if self.chk_srt.isChecked(): selected_formats.append('srt')
        if self.chk_vtt.isChecked(): selected_formats.append('vtt')

        if not selected_formats:
            QMessageBox.warning(self, "错误", "请至少选择一种导出格式！"); return None

        params = {
            'media_file': media_file,
            'output_dir': output_dir,
            'output_filename': output_filename,
            'model': self.model_combo.currentText(),
            'language': self.language_map[self.language_combo.currentText()],
            'device': self.device_combo.currentText(), # 【新增】获取设备选择
            'export_formats': selected_formats,
            'model_root': os.path.join(self.main_window.base_path, 'models', 'whisper')
        }
        return params

    def start_transcription(self):
        params = self._get_current_params()
        if not params:
            return
            
        self.set_controls_enabled(False)
        self.log_output.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0) # 【修改】从0开始
        self.progress_bar.setFormat("准备中...")

        self.thread = QThread()
        # 【修改】将 self.progress_bar 传递给 Worker
        self.worker = TranscribeWorker(params)
        self.worker.moveToThread(self.thread)

        self.worker.log_message.connect(self.log_output.append)
        # 【修改】连接新的进度信号
        self.worker.progress_update.connect(self.update_progress_bar)
        self.worker.finished.connect(self.on_transcription_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    # 【新增】新的进度更新槽函数
    @Slot(int, str)
    def update_progress_bar(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(text)

    @Slot(bool, str)
    def on_transcription_finished(self, success, message):
        self.progress_bar.setValue(100 if success else 0)
        self.progress_bar.setFormat("任务完成" if success else "任务失败")
        self.set_controls_enabled(True)

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        self.progress_bar.setVisible(False)

    def set_controls_enabled(self, enabled):
        widgets_to_toggle = (
            self.findChildren(QPushButton) + 
            self.findChildren(QComboBox) +
            self.findChildren(QCheckBox) +
            self.findChildren(QLineEdit)
        )
        for widget in widgets_to_toggle:
            widget.setEnabled(enabled)