# ui/tabs/subtitle_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QProgressBar, QComboBox, QTextEdit, QMessageBox, 
                               QGridLayout, QSpinBox, QDoubleSpinBox, QApplication, QFontComboBox, QFrame)
from PySide6.QtGui import QFont
from PySide6.QtCore import QThread, Slot

from core.workers.subtitle_worker import SubtitleBurnWorker, PreviewWorker
from core.subtitle_converter import lrc_to_ass_chatbox_region
from ui.dialogs import PreviewDialog

class SubtitleTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None

        self.color_map = {
            "白色": "&H00FFFFFF",
            "黑色": "&H00000000",
            "黄色": "&H00FFFF",
            "红色": "&H0000FF",
        }

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.load_bilibili_preset()

    def create_widgets(self):
        # --- 输入/输出路径 ---
        self.video_file_path_sub = QLineEdit()
        self.browse_video_sub_btn = QPushButton("浏览视频...")
        self.lrc_file_path_sub = QLineEdit()
        self.browse_lrc_sub_btn = QPushButton("浏览弹幕...")
        self.output_dir_sub = QLineEdit()
        self.output_dir_sub_browse_btn = QPushButton("浏览...")

        # --- 预设 ---
        self.preset_bilibili_btn = QPushButton("手机B站参数")
        self.preset_weibo_btn = QPushButton("手机微博参数")
        
        # --- 字幕参数 ---
        self.sub_font_name = QFontComboBox()
        self.sub_font_size = QSpinBox()
        self.sub_font_size.setRange(10, 200)

        self.sub_primary_color_combo = QComboBox()
        self.sub_primary_color_combo.addItems(self.color_map.keys())
        self.sub_outline_spin = QSpinBox()
        self.sub_outline_spin.setRange(0, 20)
        
        self.sub_line_spacing = QSpinBox()
        self.sub_line_spacing.setRange(0, 100)
        self.sub_letter_spacing = QSpinBox()
        self.sub_letter_spacing.setRange(-10, 100)
        self.sub_wrap_width = QSpinBox()
        self.sub_wrap_width.setRange(10, 200)
        self.sub_chatbox_duration = QSpinBox()
        self.sub_chatbox_duration.setRange(1, 300)
        self.sub_margin_left = QSpinBox()
        self.sub_margin_left.setRange(0, 4000)
        self.sub_margin_bottom = QSpinBox()
        self.sub_margin_bottom.setRange(0, 4000)
        self.sub_chatbox_height_ratio = QDoubleSpinBox()
        self.sub_chatbox_height_ratio.setRange(0.1, 1.0)
        self.sub_chatbox_height_ratio.setSingleStep(0.01)

        # --- 编码器和控制按钮 ---
        self.sub_codec_combo = QComboBox()
        self.sub_codec_combo.addItems(["h264_nvenc (N卡)", "hevc_nvenc (N卡)", "libx264 (CPU)"])
        self.sub_output_format_combo = QComboBox()
        self.sub_output_format_combo.addItems(["mp4", "mkv", "mov", "webm", "avi", "flv", "ts"])
        self.preview_button_sub = QPushButton("生成预览图")
        self.start_button_sub = QPushButton("开始制作")

        # --- 日志和进度条 ---
        self.log_output_sub = QTextEdit()
        self.log_output_sub.setReadOnly(True)
        self.progress_bar_sub = QProgressBar()
        self.progress_bar_sub.setVisible(False)

    def create_layouts(self):
        main_layout = QVBoxLayout(self)

        input_frame = QFrame()
        input_layout = QGridLayout(input_frame)
        input_layout.addWidget(QLabel("视频文件:"), 0, 0)
        input_layout.addWidget(self.video_file_path_sub, 0, 1)
        input_layout.addWidget(self.browse_video_sub_btn, 0, 2)
        input_layout.addWidget(QLabel("弹幕文件:"), 1, 0)
        input_layout.addWidget(self.lrc_file_path_sub, 1, 1)
        input_layout.addWidget(self.browse_lrc_sub_btn, 1, 2)
        input_layout.addWidget(QLabel("输出文件夹:"), 2, 0)
        input_layout.addWidget(self.output_dir_sub, 2, 1)
        input_layout.addWidget(self.output_dir_sub_browse_btn, 2, 2)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("加载预设:"))
        preset_layout.addWidget(self.preset_bilibili_btn)
        preset_layout.addWidget(self.preset_weibo_btn)
        preset_layout.addStretch()

        params_frame = QFrame()
        params_layout = QGridLayout(params_frame)
        params_layout.addWidget(QLabel("字体名称:"), 0, 0)
        params_layout.addWidget(self.sub_font_name, 0, 1)
        params_layout.addWidget(QLabel("字体大小:"), 0, 2)
        params_layout.addWidget(self.sub_font_size, 0, 3)

        params_layout.addWidget(QLabel("字体颜色:"), 1, 0)
        params_layout.addWidget(self.sub_primary_color_combo, 1, 1)
        params_layout.addWidget(QLabel("描边宽度:"), 1, 2)
        params_layout.addWidget(self.sub_outline_spin, 1, 3)
        
        params_layout.addWidget(QLabel("额外行间距:"), 2, 0)
        params_layout.addWidget(self.sub_line_spacing, 2, 1)
        params_layout.addWidget(QLabel("额外字间距:"), 2, 2)
        params_layout.addWidget(self.sub_letter_spacing, 2, 3)

        params_layout.addWidget(QLabel("自动换行宽度 (字符):"), 3, 0)
        params_layout.addWidget(self.sub_wrap_width, 3, 1)
        params_layout.addWidget(QLabel("弹幕框高度比例:"), 3, 2)
        params_layout.addWidget(self.sub_chatbox_height_ratio, 3, 3)
        
        params_layout.addWidget(QLabel("左边距:"), 4, 0)
        params_layout.addWidget(self.sub_margin_left, 4, 1)
        params_layout.addWidget(QLabel("下边距:"), 4, 2)
        params_layout.addWidget(self.sub_margin_bottom, 4, 3)
        
        params_layout.addWidget(QLabel("最后弹幕持续(秒):"), 5, 0)
        params_layout.addWidget(self.sub_chatbox_duration, 5, 1)

        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("视频编码器:"))
        codec_layout.addWidget(self.sub_codec_combo)
        codec_layout.addStretch(1)
        codec_layout.addWidget(QLabel("输出格式:"))
        codec_layout.addWidget(self.sub_output_format_combo)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.preview_button_sub)
        button_layout.addWidget(self.start_button_sub)

        main_layout.addWidget(input_frame)
        main_layout.addLayout(preset_layout)
        main_layout.addWidget(params_frame)
        main_layout.addLayout(codec_layout)
        main_layout.addStretch()
        main_layout.addWidget(QLabel("日志输出:"))
        main_layout.addWidget(self.log_output_sub)
        main_layout.addWidget(self.progress_bar_sub)
        main_layout.addLayout(button_layout)
        
    def create_connections(self):
        self.browse_video_sub_btn.clicked.connect(lambda: self.main_window.browse_file(self.video_file_path_sub, "选择视频文件", self.main_window.video_filter))
        self.browse_lrc_sub_btn.clicked.connect(lambda: self.main_window.browse_file(self.lrc_file_path_sub, "选择字幕文件", "文本文件 (*.lrc *.txt);;所有文件 (*.*)"))
        self.output_dir_sub_browse_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.output_dir_sub))
        self.video_file_path_sub.textChanged.connect(self.update_subtitle_output_dir)
        self.preset_bilibili_btn.clicked.connect(self.load_bilibili_preset)
        self.preset_weibo_btn.clicked.connect(self.load_weibo_preset)
        self.preview_button_sub.clicked.connect(self.generate_preview)
        self.start_button_sub.clicked.connect(self.start_subtitle_burn)

    def load_bilibili_preset(self):
        self.sub_font_name.setCurrentFont(QFont("楷体"))
        self.sub_font_size.setValue(18)
        self.sub_primary_color_combo.setCurrentText("白色")
        self.sub_outline_spin.setValue(0)
        self.sub_line_spacing.setValue(0)
        self.sub_letter_spacing.setValue(0)
        self.sub_wrap_width.setValue(18)
        self.sub_chatbox_height_ratio.setValue(0.20)
        self.sub_margin_left.setValue(40)
        self.sub_margin_bottom.setValue(198)
        self.sub_chatbox_duration.setValue(10)
        self.log_output_sub.append("ℹ️ 已加载 [手机B站] 参数预设。")

    def load_weibo_preset(self):
        self.sub_font_name.setCurrentFont(QFont("楷体"))
        self.sub_font_size.setValue(15)
        self.sub_primary_color_combo.setCurrentText("白色")
        self.sub_outline_spin.setValue(0)
        self.sub_line_spacing.setValue(0)
        self.sub_letter_spacing.setValue(0)
        self.sub_wrap_width.setValue(15)
        self.sub_chatbox_height_ratio.setValue(0.22)
        self.sub_margin_left.setValue(50)
        self.sub_margin_bottom.setValue(190)
        self.sub_chatbox_duration.setValue(10)
        self.log_output_sub.append("ℹ️ 已加载 [手机微博] 参数预设。")

    def update_subtitle_output_dir(self):
        video_path = self.video_file_path_sub.text()
        if video_path and os.path.isfile(video_path):
            self.output_dir_sub.setText(os.path.dirname(video_path))

    def _get_current_params(self):
        video_file = self.video_file_path_sub.text()
        lrc_file = self.lrc_file_path_sub.text()
        output_dir = self.output_dir_sub.text()

        if not (video_file and os.path.exists(video_file)):
            QMessageBox.warning(self, "错误", "请先选择有效的视频文件！"); return None
        if not (lrc_file and os.path.exists(lrc_file)):
            QMessageBox.warning(self, "错误", "请先选择有效的字幕文件！"); return None
        
        ass_options = {
            'font_name': self.sub_font_name.currentFont().family(),
            'font_size': self.sub_font_size.value(),
            'line_spacing': self.sub_line_spacing.value(),
            'letter_spacing': self.sub_letter_spacing.value(),
            'chatbox_max_height_ratio': self.sub_chatbox_height_ratio.value(),
            'margin_left': self.sub_margin_left.value(),
            'margin_bottom': self.sub_margin_bottom.value(),
            'chatbox_duration_after_last': self.sub_chatbox_duration.value(),
            'wrap_width': self.sub_wrap_width.value(),
            'primary_colour': self.color_map[self.sub_primary_color_combo.currentText()],
            'outline': self.sub_outline_spin.value()
        }
        
        return {
            'video_file': video_file,
            'lrc_file': lrc_file,
            'output_dir': output_dir,
            'base_path': self.main_window.base_path,
            'codec': self.sub_codec_combo.currentText().split(" ")[0],
            'output_format': self.sub_output_format_combo.currentText(),
            'ass_options': ass_options
        }

    def generate_preview(self):
        params = self._get_current_params()
        if not params: return
        self.set_controls_enabled(False)
        self.progress_bar_sub.setVisible(False)
        self.log_output_sub.clear()
        
        self.thread = QThread()
        self.worker = PreviewWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, params, lrc_to_ass_chatbox_region)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.log_output_sub.append)
        self.worker.finished.connect(self.on_preview_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def start_subtitle_burn(self):
        params = self._get_current_params()
        if not params: return
        if not (params['output_dir'] and os.path.isdir(params['output_dir'])):
            QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return
        self.set_controls_enabled(False)
        self.progress_bar_sub.setVisible(True)
        self.log_output_sub.clear()
        self.progress_bar_sub.setValue(0)

        self.thread = QThread()
        self.worker = SubtitleBurnWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, params, lrc_to_ass_chatbox_region)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.log_output_sub.append)
        self.worker.progress.connect(self.progress_bar_sub.setValue)
        self.worker.finished.connect(self.on_subtitle_burn_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(bool, str)
    def on_preview_finished(self, success, result_or_msg):
        self.set_controls_enabled(True)
        self.log_output_sub.clear()
        if success:
            preview_dialog = PreviewDialog(result_or_msg, self)
            preview_dialog.exec()
            if os.path.exists(result_or_msg):
                try: os.remove(result_or_msg)
                except OSError: pass
        else:
            QMessageBox.critical(self, "预览失败", result_or_msg)

    @Slot(int, str)
    def on_subtitle_burn_finished(self, return_code, message):
        self.progress_bar_sub.setValue(100)
        QApplication.processEvents()
        if return_code == 0:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        self.set_controls_enabled(True)
        self.progress_bar_sub.setVisible(False)

    def set_controls_enabled(self, enabled: bool):
        widgets_to_toggle = (
            self.findChildren(QPushButton) + 
            self.findChildren(QSpinBox) + 
            self.findChildren(QDoubleSpinBox) + 
            self.findChildren(QFontComboBox) +
            self.findChildren(QComboBox)
        )
        for widget in widgets_to_toggle:
            widget.setEnabled(enabled)