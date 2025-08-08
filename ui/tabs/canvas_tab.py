# ui/tabs/canvas_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QProgressBar, QComboBox, QTextEdit, QMessageBox, QGridLayout,
                               QSpinBox, QFrame, QApplication, QFontComboBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import QThread, Slot, Qt

from core.workers.canvas_worker import CanvasBurnWorker, CanvasPreviewWorker
from core.utils import get_video_dimensions
from ui.dialogs import PreviewDialog

class CanvasTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None
        self.video_width = 0
        self.video_height = 0
        
        self.color_map = {
            "浅蓝色": ("#ADD8E6", "&HE6D8AD"),
            "粉色": ("#FFC0CB", "&HFFCBCOFF"),
            "白色": ("#FFFFFF", "&H00FFFFFF"),
            "黑色": ("#000000", "&H00000000"),
            "黄色": ("#FFFF00", "&H00FFFF"),
            "灰色": ("#808080", "&H808080"),
        }
        
        # 【新增】定义通用的字幕文件过滤器
        self.subtitle_filter = "字幕文件 (*.lrc *.srt *.vtt *.txt);;所有文件 (*.*)"

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.load_default_preset()

    def create_widgets(self):
        # --- 输入/输出 ---
        self.video_file_path = QLineEdit()
        self.browse_video_btn = QPushButton("浏览视频...")
        self.lrc_file_path = QLineEdit()
        self.browse_lrc_btn = QPushButton("浏览字幕...")
        self.output_dir = QLineEdit()
        self.output_dir_browse_btn = QPushButton("浏览...")

        # --- 画布参数 ---
        self.canvas_width_spin = QSpinBox()
        self.canvas_width_spin.setRange(1280, 3840)
        self.canvas_width_spin.setToolTip("最终视频的宽度，通常为1920")
        
        # --- 字幕样式参数 ---
        self.font_name_combo = QFontComboBox()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 200)
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(-10, 50)
        self.outline_spin = QSpinBox()
        self.outline_spin.setRange(0, 20)
        self.wrap_width_spin = QSpinBox()
        self.wrap_width_spin.setRange(5, 50)
        
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(0, 200)
        self.line_spacing_spin.setToolTip("换行时两行文字间的额外空隙高度")
        
        self.canvas_color_combo = QComboBox()
        self.canvas_color_combo.addItems(self.color_map.keys())
        self.primary_color_combo = QComboBox()
        self.primary_color_combo.addItems(self.color_map.keys())

        # --- 编码与控制 ---
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["h264_nvenc (N卡)", "hevc_nvenc (N卡)", "libx264 (CPU)"])
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["mp4", "mkv", "mov", "webm", "avi", "flv", "ts"])
        self.preview_button = QPushButton("生成预览图")
        self.start_button = QPushButton("开始制作")
        self.load_defaults_button = QPushButton("加载默认参数")

        # --- 日志与进度条 ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

    def create_layouts(self):
        main_layout = QVBoxLayout(self)
        input_frame = QFrame()
        input_layout = QGridLayout(input_frame)
        input_layout.addWidget(QLabel("视频文件:"), 0, 0)
        input_layout.addWidget(self.video_file_path, 0, 1)
        input_layout.addWidget(self.browse_video_btn, 0, 2)
        input_layout.addWidget(QLabel("字幕文件:"), 1, 0)
        input_layout.addWidget(self.lrc_file_path, 1, 1)
        input_layout.addWidget(self.browse_lrc_btn, 1, 2)
        input_layout.addWidget(QLabel("输出文件夹:"), 2, 0)
        input_layout.addWidget(self.output_dir, 2, 1)
        input_layout.addWidget(self.output_dir_browse_btn, 2, 2)
        
        params_frame = QFrame()
        params_layout = QGridLayout(params_frame)
        params_layout.addWidget(QLabel("画布宽度:"), 0, 0)
        params_layout.addWidget(self.canvas_width_spin, 0, 1)
        params_layout.addWidget(QLabel("画布颜色:"), 0, 2)
        params_layout.addWidget(self.canvas_color_combo, 0, 3)
        
        params_layout.addWidget(QLabel("字体名称:"), 1, 0)
        params_layout.addWidget(self.font_name_combo, 1, 1)
        params_layout.addWidget(QLabel("字体大小:"), 1, 2)
        params_layout.addWidget(self.font_size_spin, 1, 3)
        
        params_layout.addWidget(QLabel("字体颜色:"), 2, 0)
        params_layout.addWidget(self.primary_color_combo, 2, 1)
        params_layout.addWidget(QLabel("描边宽度:"), 2, 2)
        params_layout.addWidget(self.outline_spin, 2, 3)
        
        params_layout.addWidget(QLabel("字间距:"), 3, 0)
        params_layout.addWidget(self.spacing_spin, 3, 1)
        params_layout.addWidget(QLabel("行间距:"), 3, 2)
        params_layout.addWidget(self.line_spacing_spin, 3, 3)
        
        params_layout.addWidget(QLabel("自动换行字数:"), 4, 0)
        params_layout.addWidget(self.wrap_width_spin, 4, 1)
        params_layout.addWidget(QLabel("编码器:"), 5, 0)
        params_layout.addWidget(self.codec_combo, 5, 1)
        params_layout.addWidget(QLabel("输出格式:"), 5, 2)
        params_layout.addWidget(self.output_format_combo, 5, 3)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.load_defaults_button)
        control_layout.addStretch()
        control_layout.addWidget(self.preview_button)
        control_layout.addWidget(self.start_button)

        main_layout.addWidget(input_frame)
        main_layout.addWidget(params_frame)
        main_layout.addStretch()
        main_layout.addWidget(QLabel("日志输出:"))
        main_layout.addWidget(self.log_output)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(control_layout)

    def create_connections(self):
        self.browse_video_btn.clicked.connect(lambda: self.main_window.browse_file(self.video_file_path, "选择视频文件", self.main_window.video_filter))
        # 【修改】使用新的通用字幕文件过滤器
        self.browse_lrc_btn.clicked.connect(lambda: self.main_window.browse_file(self.lrc_file_path, "选择字幕文件", self.subtitle_filter))
        self.output_dir_browse_btn.clicked.connect(lambda: self.main_window.browse_output_dir(self.output_dir))
        
        self.video_file_path.textChanged.connect(self.update_ui_for_video)
        
        self.load_defaults_button.clicked.connect(self.load_default_preset)
        self.preview_button.clicked.connect(self.generate_preview)
        self.start_button.clicked.connect(self.start_canvas_burn)

    def load_default_preset(self):
        self.canvas_width_spin.setValue(1920)
        self.canvas_color_combo.setCurrentText("浅蓝色")
        self.font_name_combo.setCurrentFont(QFont("黑体"))
        self.font_size_spin.setValue(90)
        self.primary_color_combo.setCurrentText("白色")
        self.outline_spin.setValue(4)
        self.spacing_spin.setValue(5)
        # 【修复Bug】将行间距默认值改为15
        self.line_spacing_spin.setValue(15)
        self.wrap_width_spin.setValue(10)
        self.log_output.append("ℹ️ 已加载参考代码中的默认参数。")

    def update_ui_for_video(self):
        video_path = self.video_file_path.text()
        if not (video_path and os.path.exists(video_path)):
            self.video_width, self.video_height = 0, 0
            return
            
        width, height, _ = get_video_dimensions(video_path, self.main_window.ffprobe_path)
        if width and height:
            self.video_width, self.video_height = width, height
            if not self.output_dir.text():
                self.output_dir.setText(os.path.dirname(video_path))
        
    def _get_current_params(self):
        video_file = self.video_file_path.text()
        lrc_file = self.lrc_file_path.text()
        output_dir = self.output_dir.text()

        if not (video_file and os.path.exists(video_file)):
            QMessageBox.warning(self, "错误", "请先选择有效的视频文件！"); return None
        if not (lrc_file and os.path.exists(lrc_file)):
            QMessageBox.warning(self, "错误", "请先选择有效的字幕文件！"); return None
        if not (output_dir and os.path.isdir(output_dir)):
            QMessageBox.warning(self, "错误", "请选择有效的输出文件夹！"); return None
        if self.video_width <= 0:
            QMessageBox.warning(self, "错误", "无法获取视频宽度，请重新选择视频文件！"); return None
            
        canvas_color_name = self.canvas_color_combo.currentText()
        font_color_name = self.primary_color_combo.currentText()
        
        style_params = {
            'font_name': self.font_name_combo.currentFont().family(),
            'font_size': self.font_size_spin.value(),
            'primary_colour': self.color_map[font_color_name][1],
            'spacing': self.spacing_spin.value(),
            'outline': self.outline_spin.value(),
            'line_spacing': self.line_spacing_spin.value(),
            'wrap_width': self.wrap_width_spin.value(),
            'wrap_style': 0, 
            'canvas_color': self.color_map[canvas_color_name][0],
        }

        return {
            'video_file': video_file,
            'lrc_file': lrc_file, # 参数名保持不变，但内容已是通用路径
            'output_dir': output_dir,
            'base_path': self.main_window.base_path,
            'canvas_width': self.canvas_width_spin.value(),
            'codec': self.codec_combo.currentText().split(" ")[0],
            'output_format': self.output_format_combo.currentText(),
            'style_params': style_params,
        }

    def generate_preview(self):
        params = self._get_current_params()
        if not params: return
        self.set_controls_enabled(False)
        self.log_output.clear()
        
        self.thread = QThread()
        self.worker = CanvasPreviewWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, params)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.log_output.append)
        self.worker.finished.connect(self.on_preview_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
        
    @Slot(bool, str)
    def on_preview_finished(self, success, result_or_msg):
        self.set_controls_enabled(True)
        self.log_output.clear()
        if success:
            preview_dialog = PreviewDialog(result_or_msg, self)
            preview_dialog.exec()
            if os.path.exists(result_or_msg):
                try: os.remove(result_or_msg)
                except OSError: pass
        else:
            QMessageBox.critical(self, "预览失败", result_or_msg)

    def start_canvas_burn(self):
        params = self._get_current_params()
        if not params: return
        self.set_controls_enabled(False)
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        self.progress_bar.setValue(0)

        self.thread = QThread()
        self.worker = CanvasBurnWorker(self.main_window.ffmpeg_path, self.main_window.ffprobe_path, params)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.log_output.append)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_burn_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_burn_finished(self, return_code, message):
        self.progress_bar.setValue(100)
        QApplication.processEvents()
        if return_code == 0:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        self.set_controls_enabled(True)
        self.progress_bar.setVisible(False)

    def set_controls_enabled(self, enabled: bool):
        widgets_to_toggle = (
            self.findChildren(QPushButton) + 
            self.findChildren(QSpinBox) + 
            self.findChildren(QFontComboBox) +
            self.findChildren(QComboBox)
        )
        for widget in widgets_to_toggle:
            widget.setEnabled(enabled)