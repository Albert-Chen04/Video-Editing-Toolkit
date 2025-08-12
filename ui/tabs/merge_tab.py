# ui/tabs/merge_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QListWidget, QAbstractItemView, QFrame, QApplication, 
                               QFileDialog, QMessageBox, QComboBox, QTextEdit)
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.merge_worker import MergeWorker

class MergeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None
        self.first_file_ext = ""

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        # --- 文件列表与控制 ---
        self.add_files_button = QPushButton("添加文件...")
        self.clear_list_button = QPushButton("清空列表")
        
        self.merge_list_widget = QListWidget()
        self.merge_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.merge_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAcceptDrops(True)
        
        self.info_label = QLabel("提示：将文件拖入上方列表，或使用按钮添加。在列表中拖动可调整合并顺序。")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- 输出设置 ---
        self.output_dir_edit = QLineEdit()
        self.browse_output_btn = QPushButton("浏览...")
        self.output_filename_edit = QLineEdit("merged_output")
        self.output_format_combo = QComboBox()
        self.default_formats = ["mp4", "mkv", "ts", "mov", "avi", "flv", "webm", "mp3", "m4a", "aac", "flac", "wav", "opus"]
        self.output_format_combo.addItems(self.default_formats)

        # --- 控制与日志 ---
        self.start_button = QPushButton("开始合并 (无损/极速模式)")
        self.start_button.setToolTip(
            "使用无损、极速的直接复制模式合并文件。\n"
            "要求所有待合并文件的编码、分辨率、帧率等参数必须一致！"
        )
        self.progress_label = QLabel("等待任务...")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

    def create_layouts(self):
        main_layout = QVBoxLayout(self)
        
        list_control_layout = QHBoxLayout()
        list_control_layout.addWidget(self.add_files_button)
        list_control_layout.addWidget(self.clear_list_button)
        list_control_layout.addStretch()

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("输出文件夹:"))
        output_path_layout.addWidget(self.output_dir_edit)
        output_path_layout.addWidget(self.browse_output_btn)
        
        output_name_layout = QHBoxLayout()
        output_name_layout.addWidget(QLabel("输出文件名:"))
        output_name_layout.addWidget(self.output_filename_edit)
        output_name_layout.addWidget(QLabel("."))
        output_name_layout.addWidget(self.output_format_combo)

        main_layout.addLayout(list_control_layout)
        main_layout.addWidget(self.merge_list_widget, 1)
        main_layout.addWidget(self.info_label)
        
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line1)

        main_layout.addLayout(output_path_layout)
        main_layout.addLayout(output_name_layout)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line2)

        main_layout.addWidget(self.progress_label)
        main_layout.addWidget(self.log_output, 1)
        main_layout.addWidget(self.start_button)
        
    def create_connections(self):
        self.add_files_button.clicked.connect(self.add_files)
        self.clear_list_button.clicked.connect(self.clear_list)
        self.browse_output_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.output_dir_edit))
        self.start_button.clicked.connect(self.start_merge)
        self.merge_list_widget.model().rowsInserted.connect(self.on_list_changed)
        self.merge_list_widget.model().rowsRemoved.connect(self.on_list_changed)

    def add_files(self):
        media_filter = "媒体文件 (*.mp4 *.mkv *.ts *.mov *.avi *.flv *.webm *.mp3 *.m4a *.aac *.flac *.wav *.opus);;所有文件 (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择要合并的文件", "", media_filter)
        if files:
            self.merge_list_widget.addItems(files)

    def clear_list(self):
        self.merge_list_widget.clear()
        self.first_file_ext = ""
        self.output_format_combo.clear()
        self.output_format_combo.addItems(self.default_formats)

    def on_list_changed(self):
        """当列表内容变化时触发，优化了默认格式设置逻辑"""
        if self.merge_list_widget.count() == 0:
            self.clear_list()
            return
            
        first_item_path = self.merge_list_widget.item(0).text()
        
        if not self.output_dir_edit.text():
            self.output_dir_edit.setText(os.path.dirname(first_item_path))
        
        _, ext = os.path.splitext(first_item_path)
        ext = ext.lstrip('.').lower()

        if ext and ext != self.first_file_ext:
            self.first_file_ext = ext
            if ext not in self.default_formats:
                self.output_format_combo.clear()
                self.output_format_combo.addItems([ext] + self.default_formats)
                self.output_format_combo.setCurrentIndex(0)
            else:
                self.output_format_combo.setCurrentText(ext)

    def start_merge(self):
        if self.merge_list_widget.count() < 2:
            QMessageBox.warning(self, "提示", "请至少添加两个文件到列表中进行合并。")
            return

        output_dir = self.output_dir_edit.text()
        if not (output_dir and os.path.isdir(output_dir)):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！")
            return
            
        filename = self.output_filename_edit.text()
        file_format = self.output_format_combo.currentText()
        if not filename:
            QMessageBox.warning(self, "错误", "请输入一个有效的文件名！")
            return
            
        output_path = os.path.join(output_dir, f"{filename}.{file_format}").replace("\\", "/")
        
        file_list = [self.merge_list_widget.item(i).text().replace("\\", "/") for i in range(self.merge_list_widget.count())]

        self.set_controls_enabled(False)
        self.log_output.clear()
        
        self.thread = QThread()
        # 注意：这里的Worker还是旧的，它内部硬编码了-c copy，这是正确的
        self.worker = MergeWorker(self.main_window.ffmpeg_path, file_list, output_path)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.log_output.append)
        self.worker.progress.connect(self.progress_label.setText)
        self.worker.finished.connect(self.on_merge_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_merge_finished(self, return_code, message):
        self.set_controls_enabled(True)
        self.progress_label.setText("任务结束。")
        if return_code == 0:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
            
    def set_controls_enabled(self, enabled):
        self.add_files_button.setEnabled(enabled)
        self.clear_list_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)