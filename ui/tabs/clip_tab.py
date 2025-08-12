# ui/tabs/clip_tab.py

import os
import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QTextEdit, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QComboBox)
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.clip_worker import BatchClipWorker
from ui.dialogs import ClipDialog
# 【新增】导入统一编码器配置模块
from core.codec_config import get_encoder_options, get_copy_tooltip

class ClipTab(QWidget):
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
        # --- 源视频 ---
        self.clip_source_video = QLineEdit()
        self.clip_source_browse_btn = QPushButton("浏览源视频...")
        
        # --- 片段列表 ---
        self.add_clip_btn = QPushButton("添加片段...")
        self.edit_clip_btn = QPushButton("编辑选中")
        self.remove_clip_btn = QPushButton("删除选中")
        self.clear_clips_btn = QPushButton("清空列表")
        self.clip_table = QTableWidget()
        self.clip_table.setColumnCount(3)
        self.clip_table.setHorizontalHeaderLabels(["片段名称", "开始时间", "结束时间"])
        self.clip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.clip_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # --- 输出 ---
        self.clip_output_dir = QLineEdit()
        self.clip_output_browse_btn = QPushButton("浏览...")

        # --- 参数 ---
        self.clip_format_combo = QComboBox()
        self.clip_format_combo.addItems(["mp4", "mkv", "ts", "mp3", "aac", "flac", "wav"])
        
        self.clip_codec_combo = QComboBox()
        # 【修改】从统一配置模块动态加载编码器选项
        encoder_options = get_encoder_options()
        self.clip_codec_combo.addItems(encoder_options)
        # 【修改】为 "直接复制" 选项添加 ToolTip
        copy_index = -1
        try:
            copy_index = encoder_options.index("直接复制 (无损/极速)")
        except ValueError:
            pass
        if copy_index != -1:
            self.clip_codec_combo.setItemData(copy_index, get_copy_tooltip(), Qt.ToolTipRole)

        # --- 进度和日志 ---
        self.clip_progress_label = QLabel("等待任务...")
        self.clip_log_output = QTextEdit()
        self.clip_log_output.setReadOnly(True)
        self.start_clip_button = QPushButton("开始批量裁剪")

    def create_layouts(self):
        layout = QVBoxLayout(self)

        source_video_layout = QHBoxLayout()
        source_video_layout.addWidget(QLabel("源视频文件:"))
        source_video_layout.addWidget(self.clip_source_video)
        source_video_layout.addWidget(self.clip_source_browse_btn)

        clip_buttons_layout = QHBoxLayout()
        clip_buttons_layout.addWidget(self.add_clip_btn)
        clip_buttons_layout.addWidget(self.edit_clip_btn)
        clip_buttons_layout.addWidget(self.remove_clip_btn)
        clip_buttons_layout.addWidget(self.clear_clips_btn)
        clip_buttons_layout.addStretch()

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("输出文件夹:"))
        output_path_layout.addWidget(self.clip_output_dir)
        output_path_layout.addWidget(self.clip_output_browse_btn)

        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("输出格式:"))
        params_layout.addWidget(self.clip_format_combo)
        params_layout.addStretch()
        params_layout.addWidget(QLabel("视频编码器:"))
        params_layout.addWidget(self.clip_codec_combo)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        layout.addLayout(source_video_layout)
        layout.addLayout(clip_buttons_layout)
        layout.addWidget(self.clip_table)
        layout.addLayout(output_path_layout)
        layout.addLayout(params_layout)
        layout.addWidget(line)
        layout.addWidget(self.clip_progress_label)
        layout.addWidget(QLabel("日志输出:"))
        layout.addWidget(self.clip_log_output)
        layout.addWidget(self.start_clip_button, alignment=Qt.AlignCenter)

    def create_connections(self):
        self.clip_source_browse_btn.clicked.connect(lambda: self.main_window.browse_file(self.clip_source_video, "选择源视频", self.main_window.video_filter))
        self.clip_source_video.textChanged.connect(self.update_clip_output_dir)
        self.add_clip_btn.clicked.connect(self.add_clip_item)
        self.edit_clip_btn.clicked.connect(self.edit_clip_item)
        self.clip_table.itemDoubleClicked.connect(self.edit_clip_item)
        self.remove_clip_btn.clicked.connect(self.remove_clip_item)
        self.clear_clips_btn.clicked.connect(lambda: self.clip_table.setRowCount(0))
        self.clip_output_browse_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.clip_output_dir))
        self.start_clip_button.clicked.connect(self.start_batch_clipping)

    # 【新增】设置默认选项的函数
    def set_default_options(self):
        self.clip_codec_combo.setCurrentText("直接复制 (无损/极速)")
        
    def update_clip_output_dir(self):
        video_path = self.clip_source_video.text()
        if video_path and os.path.isfile(video_path):
            self.clip_output_dir.setText(os.path.dirname(video_path))

    def add_clip_item(self):
        dialog = ClipDialog(self)
        if dialog.exec():
            name, start, end = dialog.get_data()
            if name and start and end:
                row_position = self.clip_table.rowCount()
                self.clip_table.insertRow(row_position)
                self.clip_table.setItem(row_position, 0, QTableWidgetItem(name))
                self.clip_table.setItem(row_position, 1, QTableWidgetItem(start))
                self.clip_table.setItem(row_position, 2, QTableWidgetItem(end))

    def edit_clip_item(self, item=None):
        selected_items = self.clip_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先在表格中选择要编辑的行。")
            return
            
        row = self.clip_table.currentRow()
        if row == -1: return
        
        current_name = self.clip_table.item(row, 0).text()
        current_start = self.clip_table.item(row, 1).text()
        current_end = self.clip_table.item(row, 2).text()
        
        dialog = ClipDialog(self, current_name, current_start, current_end)
        if dialog.exec():
            new_name, new_start, new_end = dialog.get_data()
            if new_name and new_start and new_end:
                self.clip_table.setItem(row, 0, QTableWidgetItem(new_name))
                self.clip_table.setItem(row, 1, QTableWidgetItem(new_start))
                self.clip_table.setItem(row, 2, QTableWidgetItem(new_end))

    def remove_clip_item(self):
        selected_rows = self.clip_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在表格中选择要删除的行。")
            return
        for index in sorted(selected_rows, reverse=True):
            self.clip_table.removeRow(index.row())

    def start_batch_clipping(self):
        source_video = self.clip_source_video.text()
        output_dir = self.clip_output_dir.text()

        if not (source_video and os.path.exists(source_video)):
            QMessageBox.warning(self, "错误", "请选择一个有效的源视频文件！")
            return
        if not (output_dir and os.path.isdir(output_dir)):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！")
            return
        if self.clip_table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "请至少添加一个裁剪片段！")
            return

        time_pattern = re.compile(r'^\d{1,2}:\d{2}:\d{2}(\.\d+)?$|^\d+:\d{2}(\.\d+)?$|^\d+(\.\d+)?$')
        clip_list = []
        for row in range(self.clip_table.rowCount()):
            name = self.clip_table.item(row, 0).text()
            start = self.clip_table.item(row, 1).text()
            end = self.clip_table.item(row, 2).text()
            if not (time_pattern.match(start) and time_pattern.match(end)):
                QMessageBox.warning(self, "格式错误", f"片段 '{name}' 的时间格式不正确！\n\n有效格式为 HH:MM:SS, MM:SS 或纯秒数。")
                return
            clip_list.append({'name': name, 'start': start, 'end': end})

        # 【修改】获取编码器名称
        options = {
            'output_dir': output_dir,
            'format': self.clip_format_combo.currentText(),
            'codec_name': self.clip_codec_combo.currentText()
        }

        self.set_controls_enabled(False)
        self.clip_log_output.clear()

        self.thread = QThread()
        self.worker = BatchClipWorker(self.main_window.ffmpeg_path, source_video, clip_list, options)
        self.worker.moveToThread(self.thread)
        self.worker.clip_started.connect(self.clip_progress_label.setText)
        self.worker.log_message.connect(self.clip_log_output.append)
        self.worker.clip_finished.connect(self.on_clip_file_finished)
        self.worker.batch_finished.connect(self.on_clip_all_finished)
        self.worker.batch_finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_clip_file_finished(self, return_code, temp_filepath):
        if return_code != 0:
            self.clip_log_output.append(f"❌ 文件 {os.path.basename(temp_filepath)} 裁剪失败 (代码: {return_code})。\n")
        else:
            self.clip_log_output.append(f"✅ 文件 {os.path.basename(temp_filepath)} 裁剪成功。\n")

    @Slot()
    def on_clip_all_finished(self):
        self.clip_log_output.append("\n--- 所有片段裁剪完成，开始重命名并生成记录... ---")
        output_dir = self.worker.options['output_dir']
        ext = self.worker.options['format']
        clip_list = self.worker.clip_list
        
        for i, clip_info in enumerate(clip_list):
            temp_filename = f"{i+1:03d}.{ext}"
            temp_filepath = os.path.join(output_dir, temp_filename)
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", clip_info['name'])
            final_filename = f"{safe_name}.{ext}"
            final_filepath = os.path.join(output_dir, final_filename)
            if os.path.exists(temp_filepath):
                try:
                    os.rename(temp_filepath, final_filepath)
                    self.clip_log_output.append(f"重命名: {temp_filename} -> {final_filename}")
                except OSError as e:
                    self.clip_log_output.append(f"❌ 重命名失败: {e}")

        record_file_path = os.path.join(output_dir, "_clip_record.txt")
        try:
            with open(record_file_path, 'w', encoding='utf-8') as f:
                f.write("--- 批量裁剪记录 ---\n")
                f.write(f"源文件: {self.worker.source_video}\n\n")
                for clip in clip_list:
                    f.write(f"名称: {clip['name']}\n")
                    f.write(f"开始: {clip['start']}\n")
                    f.write(f"结束: {clip['end']}\n\n")
            self.clip_log_output.append(f"✅ 裁剪记录已保存到: {record_file_path}")
        except IOError as e:
            self.clip_log_output.append(f"❌ 保存记录文件失败: {e}")

        self.set_controls_enabled(True)
        self.clip_progress_label.setText("所有任务已完成！")
        QMessageBox.information(self, "完成", "批量裁剪已全部完成！")

    def set_controls_enabled(self, enabled: bool):
        self.start_clip_button.setEnabled(enabled)
        self.add_clip_btn.setEnabled(enabled)
        self.edit_clip_btn.setEnabled(enabled)
        self.remove_clip_btn.setEnabled(enabled)
        self.clear_clips_btn.setEnabled(enabled)