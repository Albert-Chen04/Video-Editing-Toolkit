# ui/tabs/transcode_tab.py

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QProgressBar, QFileDialog, QComboBox, QTextEdit, QMessageBox,
                               QListWidget, QAbstractItemView, QFrame)
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.transcode_worker import BatchTranscodeWorker
# 【新增】导入统一编码器配置模块
from core.codec_config import get_encoder_options, get_copy_tooltip

class TranscodeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.thread = None
        self.worker = None

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        # 【新增】调用设置默认值
        self.set_default_options()

    def create_widgets(self):
        # --- 文件列表 ---
        self.add_files_button = QPushButton("添加文件...")
        self.clear_list_button = QPushButton("清空列表")
        self.batch_list_widget = QListWidget()
        self.batch_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # --- 输出路径 ---
        self.output_dir_line_edit = QLineEdit()
        self.output_dir_browse_button = QPushButton("浏览...")

        # --- 参数选项 ---
        self.batch_format_combo = QComboBox()
        self.batch_format_combo.addItems([
            "mp4", "mkv", "mov", "ts", "flv", "webm", "avi", 
            "提取 aac", "提取 mp3", "提取 flac", "提取 wav", "提取 opus"
        ])
        
        self.batch_codec_combo = QComboBox()
        # 【修改】从统一配置模块动态加载编码器选项
        encoder_options = get_encoder_options()
        self.batch_codec_combo.addItems(encoder_options)
        # 【修改】为 "直接复制" 选项添加 ToolTip
        copy_index = -1
        try:
            copy_index = encoder_options.index("直接复制 (无损/极速)")
        except ValueError:
            pass
        if copy_index != -1:
            self.batch_codec_combo.setItemData(copy_index, get_copy_tooltip(), Qt.ToolTipRole)

        # --- 进度和日志 ---
        self.batch_progress_label = QLabel("等待任务...")
        self.batch_progress_bar = QProgressBar()
        self.batch_log_output = QTextEdit()
        self.batch_log_output.setReadOnly(True)

        # --- 控制按钮 ---
        self.start_batch_button = QPushButton("开始处理列表")

    def create_layouts(self):
        layout = QVBoxLayout(self)

        list_control_layout = QHBoxLayout()
        list_control_layout.addWidget(self.add_files_button)
        list_control_layout.addWidget(self.clear_list_button)
        list_control_layout.addStretch()

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("输出文件夹:"))
        output_path_layout.addWidget(self.output_dir_line_edit)
        output_path_layout.addWidget(self.output_dir_browse_button)
        
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("目标格式:"))
        params_layout.addWidget(self.batch_format_combo)
        params_layout.addStretch()
        params_layout.addWidget(QLabel("视频编码器:"))
        params_layout.addWidget(self.batch_codec_combo)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        layout.addLayout(list_control_layout)
        layout.addWidget(self.batch_list_widget)
        layout.addLayout(output_path_layout)
        layout.addLayout(params_layout)
        layout.addWidget(line)
        layout.addWidget(self.batch_progress_label)
        layout.addWidget(self.batch_progress_bar)
        layout.addWidget(QLabel("日志输出:"))
        layout.addWidget(self.batch_log_output)
        layout.addWidget(self.start_batch_button, alignment=Qt.AlignCenter)

    def create_connections(self):
        self.add_files_button.clicked.connect(self.add_files_to_batch)
        self.clear_list_button.clicked.connect(self.batch_list_widget.clear)
        self.output_dir_browse_button.clicked.connect(lambda: self.main_window.browse_output_dir(self.output_dir_line_edit))
        self.start_batch_button.clicked.connect(self.start_batch_transcoding)
        # 【新增】连接信号，当格式改变时更新编码器状态
        self.batch_format_combo.currentTextChanged.connect(self.on_format_changed)

    # 【新增】设置默认选项的函数
    def set_default_options(self):
        self.batch_codec_combo.setCurrentText("直接复制 (无损/极速)")

    # 【新增】当格式下拉框变化时调用的函数
    def on_format_changed(self, text):
        is_audio_extract = "提取" in text
        self.batch_codec_combo.setEnabled(not is_audio_extract)
        if is_audio_extract:
            self.batch_codec_combo.setToolTip("提取音频时，视频编码器无效。")
        else:
            self.batch_codec_combo.setToolTip("") # 清除提示

    def add_files_to_batch(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要处理的文件", "", self.main_window.media_filter)
        if files:
            self.batch_list_widget.addItems(files)
            if not self.output_dir_line_edit.text():
                self.output_dir_line_edit.setText(os.path.dirname(files[0]))

    def start_batch_transcoding(self):
        if self.batch_list_widget.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加要处理的文件到列表！")
            return
            
        output_dir = self.output_dir_line_edit.text()
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！")
            return
            
        file_queue = [self.batch_list_widget.item(i).text() for i in range(self.batch_list_widget.count())]
        
        # 【修改】获取编码器名称
        transcode_options = {
            'format': self.batch_format_combo.currentText(),
            'codec_name': self.batch_codec_combo.currentText(),
            'output_dir': output_dir
        }

        self.set_controls_enabled(False)
        self.batch_log_output.clear()

        self.thread = QThread()
        self.worker = BatchTranscodeWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, file_queue, transcode_options)
        self.worker.moveToThread(self.thread)

        self.worker.file_started.connect(self.batch_progress_label.setText)
        self.worker.file_progress.connect(self.batch_progress_bar.setValue)
        self.worker.log_message.connect(self.batch_log_output.append)
        self.worker.file_finished.connect(self.on_batch_file_finished)
        self.worker.batch_finished.connect(self.on_batch_all_finished)
        self.worker.batch_finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int)
    def on_batch_file_finished(self, return_code):
        self.batch_progress_bar.setValue(100)
        if return_code != 0:
            self.batch_log_output.append(f"\n❌ 上一个任务失败 (代码: {return_code})。\n")
        else:
            self.batch_log_output.append(f"\n✅ 上一个任务成功。\n")

    @Slot()
    def on_batch_all_finished(self):
        self.set_controls_enabled(True)
        self.batch_progress_label.setText("所有任务已完成！")
        self.batch_progress_bar.setValue(0)
        QMessageBox.information(self, "完成", "批量处理已全部完成！")

    def set_controls_enabled(self, enabled: bool):
        self.start_batch_button.setEnabled(enabled)
        self.add_files_button.setEnabled(enabled)
        self.clear_list_button.setEnabled(enabled)
        self.output_dir_browse_button.setEnabled(enabled)
        # 【修改】确保在禁用时，编码器下拉框状态正确
        if enabled:
            self.on_format_changed(self.batch_format_combo.currentText())
        else:
            self.batch_codec_combo.setEnabled(False)