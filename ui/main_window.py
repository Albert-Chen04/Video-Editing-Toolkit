# ui/main_window.py
import os, sys, re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QLineEdit, QProgressBar, QFileDialog, QTabWidget,
                               QComboBox, QTextEdit, QMessageBox, QGridLayout, QSpinBox,
                               QDoubleSpinBox, QListWidget, QAbstractItemView, QFrame, QDialog,
                               QTableWidget, QTableWidgetItem, QHeaderView, QRubberBand)
from PySide6.QtCore import QThread, Slot, Qt, QRect, QPoint, QSize
from PySide6.QtGui import QIcon, QPixmap, QPalette, QPainter

from core.ffmpeg_handler import (BatchTranscodeWorker, SubtitleBurnWorker, PreviewWorker, 
                                 BatchClipWorker, VideoFromBgWorker, get_video_duration)
from core.subtitle_converter import get_video_dimensions, lrc_to_ass_chatbox_region

class ImageCropDialog(QDialog):
    def __init__(self, image_path, target_aspect_ratio, parent=None):
        super().__init__(parent); self.setWindowTitle("裁剪背景图 (拖动/滚轮缩放)"); self.image_path = image_path
        self.target_aspect_ratio = target_aspect_ratio; self.pixmap = QPixmap(image_path)
        self.current_scale = 1.0; self.current_pos = QPoint(0, 0); self.view_label = QLabel()
        self.view_label.setFixedSize(800, 600); self.view_label.setStyleSheet("background-color: #333;")
        self.view_label.setAlignment(Qt.AlignCenter); self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.view_label)
        main_layout = QVBoxLayout(); main_layout.addWidget(self.view_label)
        button_box = QHBoxLayout(); ok_button = QPushButton("确定"); cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept); cancel_button.clicked.connect(self.reject)
        button_box.addStretch(); button_box.addWidget(ok_button); button_box.addWidget(cancel_button)
        main_layout.addLayout(button_box); self.setLayout(main_layout); self.update_crop_area(); self.update_view()
    def update_crop_area(self):
        view_size = self.view_label.size(); view_ratio = view_size.width() / view_size.height()
        if self.target_aspect_ratio > view_ratio: width = view_size.width(); height = int(width / self.target_aspect_ratio)
        else: height = view_size.height(); width = int(height * self.target_aspect_ratio)
        top_left = QPoint((view_size.width() - width) // 2, (view_size.height() - height) // 2)
        self.rubber_band.setGeometry(QRect(top_left, QSize(width, height)))
    def update_view(self):
        canvas = QPixmap(self.view_label.size()); canvas.fill(Qt.darkGray); painter = QPainter(canvas)
        scaled_pixmap = self.pixmap.scaled(int(self.pixmap.width() * self.current_scale), int(self.pixmap.height() * self.current_scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        draw_pos = self.current_pos + QPoint((self.view_label.width() - scaled_pixmap.width()) // 2, (self.view_label.height() - scaled_pixmap.height()) // 2)
        painter.drawPixmap(draw_pos, scaled_pixmap); painter.end(); self.view_label.setPixmap(canvas)
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0: self.current_scale *= 1.1
        else: self.current_scale *= 0.9
        self.update_view()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_start_position = event.pos()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton: self.current_pos += event.pos() - self.drag_start_position; self.drag_start_position = event.pos(); self.update_view()
    def get_crop_filter(self):
        crop_rect = self.rubber_band.geometry(); view_size = self.view_label.size()
        scaled_pixmap_size = self.pixmap.size() * self.current_scale
        img_top_left = self.current_pos + QPoint((view_size.width() - scaled_pixmap_size.width()) // 2, (view_size.height() - scaled_pixmap_size.height()) // 2)
        crop_x_in_img = crop_rect.x() - img_top_left.x(); crop_y_in_img = crop_rect.y() - img_top_left.y()
        final_x = int(crop_x_in_img / self.current_scale); final_y = int(crop_y_in_img / self.current_scale)
        final_w = int(crop_rect.width() / self.current_scale); final_h = int(crop_rect.height() / self.current_scale)
        return f"crop={final_w}:{final_h}:{final_x}:{final_y}"

class ClipDialog(QDialog):
    def __init__(self, parent=None, name="", start="", end=""):
        super().__init__(parent); self.setWindowTitle("添加/编辑片段"); layout = QGridLayout(self)
        self.name_edit = QLineEdit(name); self.start_edit = QLineEdit(start); self.end_edit = QLineEdit(end)
        layout.addWidget(QLabel("片段名称:"), 0, 0); layout.addWidget(self.name_edit, 0, 1)
        layout.addWidget(QLabel("开始时间 (HH:MM:SS):"), 1, 0); layout.addWidget(self.start_edit, 1, 1)
        layout.addWidget(QLabel("结束时间 (HH:MM:SS):"), 2, 0); layout.addWidget(self.end_edit, 2, 1)
        button_box = QHBoxLayout(); ok_button = QPushButton("确定"); cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept); cancel_button.clicked.connect(self.reject)
        button_box.addStretch(); button_box.addWidget(ok_button); button_box.addWidget(cancel_button)
        layout.addLayout(button_box, 3, 0, 1, 2)
    def get_data(self): return self.name_edit.text(), self.start_edit.text(), self.end_edit.text()

class PreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent); self.setWindowTitle("效果预览 (滚动滚轮缩放)"); self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull(): self.label = QLabel(f"错误：无法加载预览图片！\n路径: {image_path}", self); layout = QVBoxLayout(); layout.addWidget(self.label); self.setLayout(layout); return
        self.image_label = QLabel(); self.image_label.setAlignment(Qt.AlignCenter)
        main_layout = QVBoxLayout(); main_layout.addWidget(self.image_label); self.setLayout(main_layout)
        self.scale_factor = 1.0; initial_width = self.original_pixmap.width()
        if initial_width > 800: self.scale_factor = 800 / initial_width
        self.update_image_display()
    def update_image_display(self):
        if self.original_pixmap.isNull(): return
        new_width = int(self.original_pixmap.width() * self.scale_factor); new_height = int(self.original_pixmap.height() * self.scale_factor)
        scaled_pixmap = self.original_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap); self.resize(new_width + 20, new_height + 20)
    def wheelEvent(self, event):
        if self.original_pixmap.isNull(): return
        if event.angleDelta().y() > 0: self.scale_factor *= 1.25
        else: self.scale_factor *= 0.8
        if self.original_pixmap.width() * self.scale_factor < 100: self.scale_factor = 100 / self.original_pixmap.width()
        self.update_image_display()

class MainWindow(QMainWindow):
# 在 ui/main_window.py 中替换 __init__ 函数

    def __init__(self):
        super().__init__()

        # --- 【核心修正】智能判断路径，兼容开发和打包环境 ---
        if getattr(sys, 'frozen', False):
            # 如果程序被打包了 (sys.frozen为True)
            # 则可执行文件的根目录是 sys._MEIPASS
            # 在这种情况下，我们之前在 .spec 文件里已经指定了
            # ffmpeg.exe 和 assets/ 会被放在根目录。
            self.base_path = sys._MEIPASS
            # 打包后，依赖文件在根目录
            self.ffmpeg_path = os.path.join(self.base_path, 'ffmpeg.exe')
            self.ffprobe_path = os.path.join(self.base_path, 'ffprobe.exe')
        else:
            # 如果是正常运行 .py 脚本 (开发环境)
            # 根目录是 main.py 的上级目录 (ffmpeg_suite/)
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # 在开发环境下，依赖文件在 'dependencies' 子目录中
            self.ffmpeg_path = os.path.join(self.base_path, 'dependencies', 'ffmpeg.exe')
            self.ffprobe_path = os.path.join(self.base_path, 'dependencies', 'ffprobe.exe')
        # --- 路径修正结束 ---

        # --- 状态和实例变量定义 ---
        self.thread = None
        self.worker = None
        self.vbg_crop_filter = None # 你新增的变量，予以保留

        # --- 窗口基本设置 ---
        self.setWindowTitle("口袋48视频剪辑工具箱 v0.1.0 (测试版)")
        self.setGeometry(100, 100, 900, 800)
        # 图标路径也要用新的base_path来找，并确保它指向正确的子目录
        icon_path = os.path.join(self.base_path, 'assets', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # --- 补全缺失的变量定义 ---
        self.video_filter = "视频文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm);;所有文件 (*.*)"
        self.media_filter = "媒体文件 (*.mp4 *.mkv *.ts *.flv *.mov *.avi *.webm *.mp3 *.aac *.m4a *.wav);;所有文件 (*.*)"
        
        # --- 创建主控件和功能标签页 ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 调用你定义的创建函数 (确保这些函数在MainWindow类中已存在)
        self.create_subtitle_tab()
        self.create_batch_transcode_tab()
        self.create_batch_clip_tab()
        self.create_video_from_bg_tab()
        
    

    def create_subtitle_tab(self):
        tab = QWidget(); main_layout = QVBoxLayout(tab)
        video_input_layout = QHBoxLayout(); self.video_file_path_sub = QLineEdit(); self.browse_video_sub_btn = QPushButton("浏览视频...")
        video_input_layout.addWidget(QLabel("视频文件:")); video_input_layout.addWidget(self.video_file_path_sub); video_input_layout.addWidget(self.browse_video_sub_btn)
        lrc_input_layout = QHBoxLayout(); self.lrc_file_path_sub = QLineEdit(); self.browse_lrc_sub_btn = QPushButton("浏览字幕文件...")
        lrc_input_layout.addWidget(QLabel("字幕文件:")); lrc_input_layout.addWidget(self.lrc_file_path_sub); lrc_input_layout.addWidget(self.browse_lrc_sub_btn)
        main_layout.addLayout(video_input_layout); main_layout.addLayout(lrc_input_layout)
        output_path_layout = QHBoxLayout(); self.output_dir_sub = QLineEdit(); self.output_dir_sub_browse_btn = QPushButton("浏览...")
        output_path_layout.addWidget(QLabel("输出文件夹:")); output_path_layout.addWidget(self.output_dir_sub); output_path_layout.addWidget(self.output_dir_sub_browse_btn)
        main_layout.addLayout(output_path_layout)
        preset_layout = QHBoxLayout(); self.preset_bilibili_btn = QPushButton("手机B站参数"); self.preset_weibo_btn = QPushButton("手机微博参数")
        preset_layout.addWidget(QLabel("加载预设:")); preset_layout.addWidget(self.preset_bilibili_btn); preset_layout.addWidget(self.preset_weibo_btn); preset_layout.addStretch()
        main_layout.addLayout(preset_layout)
        params_layout = QGridLayout(); self.sub_font_name = QLineEdit(); self.sub_font_size = QSpinBox(); self.sub_font_size.setRange(10, 200)
        self.sub_line_spacing = QSpinBox(); self.sub_line_spacing.setRange(0, 100); self.sub_letter_spacing = QSpinBox(); self.sub_letter_spacing.setRange(-10, 100)
        self.sub_wrap_width = QSpinBox(); self.sub_wrap_width.setRange(10, 200); self.sub_chatbox_duration = QSpinBox(); self.sub_chatbox_duration.setRange(1, 300)
        self.sub_margin_left = QSpinBox(); self.sub_margin_left.setRange(0, 4000); self.sub_margin_bottom = QSpinBox(); self.sub_margin_bottom.setRange(0, 4000)
        self.sub_chatbox_height_ratio = QDoubleSpinBox(); self.sub_chatbox_height_ratio.setRange(0.1, 1.0); self.sub_chatbox_height_ratio.setSingleStep(0.01)
        params_layout.addWidget(QLabel("字体名称:"), 0, 0); params_layout.addWidget(self.sub_font_name, 0, 1); params_layout.addWidget(QLabel("字体大小:"), 0, 2); params_layout.addWidget(self.sub_font_size, 0, 3)
        params_layout.addWidget(QLabel("额外行间距:"), 1, 0); params_layout.addWidget(self.sub_line_spacing, 1, 1); params_layout.addWidget(QLabel("额外字间距:"), 1, 2); params_layout.addWidget(self.sub_letter_spacing, 1, 3)
        params_layout.addWidget(QLabel("自动换行宽度 (字符):"), 2, 0); params_layout.addWidget(self.sub_wrap_width, 2, 1); params_layout.addWidget(QLabel("弹幕框高度比例:"), 2, 2); params_layout.addWidget(self.sub_chatbox_height_ratio, 2, 3)
        params_layout.addWidget(QLabel("左边距:"), 3, 0); params_layout.addWidget(self.sub_margin_left, 3, 1); params_layout.addWidget(QLabel("下边距:"), 3, 2); params_layout.addWidget(self.sub_margin_bottom, 3, 3)
        params_layout.addWidget(QLabel("最后弹幕持续(秒):"), 4, 0); params_layout.addWidget(self.sub_chatbox_duration, 4, 1)
        main_layout.addLayout(params_layout)
        codec_layout = QHBoxLayout(); self.sub_codec_combo = QComboBox(); self.sub_codec_combo.addItems(["h264_nvenc (N卡)", "hevc_nvenc (N卡)", "libx264 (CPU)"])
        codec_layout.addWidget(QLabel("视频编码器:")); codec_layout.addWidget(self.sub_codec_combo); codec_layout.addStretch()
        main_layout.addLayout(codec_layout); main_layout.addStretch()
        self.log_output_sub = QTextEdit(); self.log_output_sub.setReadOnly(True); self.progress_bar_sub = QProgressBar(); self.progress_bar_sub.setVisible(False)
        main_layout.addWidget(QLabel("日志输出:")); main_layout.addWidget(self.log_output_sub); main_layout.addWidget(self.progress_bar_sub)
        self.load_bilibili_preset()
        button_layout = QHBoxLayout(); self.preview_button_sub = QPushButton("生成预览图"); self.start_button_sub = QPushButton("开始制作")
        button_layout.addStretch(); button_layout.addWidget(self.preview_button_sub); button_layout.addWidget(self.start_button_sub)
        main_layout.addLayout(button_layout)
        self.tabs.addTab(tab, "Chatbox弹幕视频制作")
        self.browse_video_sub_btn.clicked.connect(lambda: self.browse_file(self.video_file_path_sub, "选择视频文件", self.video_filter))
        self.browse_lrc_sub_btn.clicked.connect(lambda: self.browse_file(self.lrc_file_path_sub, "选择字幕文件", "文本文件 (*.lrc *.txt)"))
        self.output_dir_sub_browse_btn.clicked.connect(lambda: self.browse_output_dir(self.output_dir_sub))
        self.video_file_path_sub.textChanged.connect(self.update_subtitle_output_dir)
        self.preset_bilibili_btn.clicked.connect(self.load_bilibili_preset)
        self.preset_weibo_btn.clicked.connect(self.load_weibo_preset)
        self.preview_button_sub.clicked.connect(self.generate_preview)
        self.start_button_sub.clicked.connect(self.start_subtitle_burn)

    def load_bilibili_preset(self):
        self.sub_font_name.setText("楷体"); self.sub_font_size.setValue(18); self.sub_line_spacing.setValue(0); self.sub_letter_spacing.setValue(0)
        self.sub_wrap_width.setValue(18); self.sub_chatbox_height_ratio.setValue(0.20); self.sub_margin_left.setValue(40)
        self.sub_margin_bottom.setValue(198); self.sub_chatbox_duration.setValue(10)
        self.log_output_sub.append("ℹ️ 已加载 [手机B站] 参数预设。")

    def load_weibo_preset(self):
        self.sub_font_name.setText("楷体"); self.sub_font_size.setValue(15); self.sub_line_spacing.setValue(0); self.sub_letter_spacing.setValue(0)
        self.sub_wrap_width.setValue(15); self.sub_chatbox_height_ratio.setValue(0.22); self.sub_margin_left.setValue(50)
        self.sub_margin_bottom.setValue(190); self.sub_chatbox_duration.setValue(10)
        self.log_output_sub.append("ℹ️ 已加载 [手机微博] 参数预设。")

    def update_subtitle_output_dir(self):
        video_path = self.video_file_path_sub.text()
        if video_path and os.path.isfile(video_path): self.output_dir_sub.setText(os.path.dirname(video_path))

    def generate_preview(self):
        video_file = self.video_file_path_sub.text(); lrc_file = self.lrc_file_path_sub.text()
        if not (video_file and os.path.exists(video_file)): QMessageBox.warning(self, "错误", "请先选择有效的视频文件！"); return
        if not (lrc_file and os.path.exists(lrc_file)): QMessageBox.warning(self, "错误", "请先选择有效的字幕文件！"); return
        self.preview_button_sub.setEnabled(False); self.start_button_sub.setEnabled(False)
        self.progress_bar_sub.setVisible(False); self.log_output_sub.clear()
        params = { 'video_file': video_file, 'lrc_file': lrc_file, 'base_path': self.base_path,
            'ass_options': { 'font_name': self.sub_font_name.text(), 'font_size': self.sub_font_size.value(), 'line_spacing': self.sub_line_spacing.value(), 'letter_spacing': self.sub_letter_spacing.value(), 'chatbox_max_height_ratio': self.sub_chatbox_height_ratio.value(), 'margin_left': self.sub_margin_left.value(), 'margin_bottom': self.sub_margin_bottom.value(), 'chatbox_duration_after_last': self.sub_chatbox_duration.value(), 'wrap_width': self.sub_wrap_width.value() } }
        self.thread = QThread(); self.worker = PreviewWorker(self.ffmpeg_path, self.ffprobe_path, params, lrc_to_ass_chatbox_region)
        self.worker.moveToThread(self.thread); self.worker.log_message.connect(self.log_output_sub.append)
        self.worker.finished.connect(self.on_preview_finished); self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run); self.thread.start()
        
    @Slot(bool, str)
    def on_preview_finished(self, success, result_or_msg):
        self.preview_button_sub.setEnabled(True); self.start_button_sub.setEnabled(True)
        self.log_output_sub.clear()
        if success:
            preview_dialog = PreviewDialog(result_or_msg, self); preview_dialog.exec()
            if os.path.exists(result_or_msg): os.remove(result_or_msg)
        else: QMessageBox.critical(self, "预览失败", result_or_msg)

    def start_subtitle_burn(self):
        video_file = self.video_file_path_sub.text(); lrc_file = self.lrc_file_path_sub.text(); output_dir = self.output_dir_sub.text()
        if not (video_file and os.path.exists(video_file)): QMessageBox.warning(self, "错误", "请输入有效的视频文件路径！"); return
        if not (lrc_file and os.path.exists(lrc_file)): QMessageBox.warning(self, "错误", "请输入有效的字幕文件！"); return
        if not (output_dir and os.path.isdir(output_dir)): QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return
        self.preview_button_sub.setEnabled(False); self.start_button_sub.setEnabled(False)
        self.progress_bar_sub.setVisible(True); self.log_output_sub.clear(); self.progress_bar_sub.setValue(0)
        params = { 'video_file': video_file, 'lrc_file': lrc_file, 'codec': self.sub_codec_combo.currentText().split(" ")[0], 'output_dir': output_dir,
            'ass_options': { 'font_name': self.sub_font_name.text(), 'font_size': self.sub_font_size.value(), 'line_spacing': self.sub_line_spacing.value(), 'letter_spacing': self.sub_letter_spacing.value(), 'chatbox_max_height_ratio': self.sub_chatbox_height_ratio.value(), 'margin_left': self.sub_margin_left.value(), 'margin_bottom': self.sub_margin_bottom.value(), 'chatbox_duration_after_last': self.sub_chatbox_duration.value(), 'wrap_width': self.sub_wrap_width.value() } }
        self.thread = QThread(); self.worker = SubtitleBurnWorker(self.ffmpeg_path, self.ffprobe_path, params, lrc_to_ass_chatbox_region)
        self.worker.moveToThread(self.thread); self.worker.log_message.connect(self.log_output_sub.append)
        self.worker.progress.connect(self.progress_bar_sub.setValue); self.worker.finished.connect(self.on_subtitle_burn_finished)
        self.worker.finished.connect(self.thread.quit); self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater); self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_subtitle_burn_finished(self, return_code, message):
        self.progress_bar_sub.setValue(100); QApplication.processEvents()
        if return_code == 0: QMessageBox.information(self, "成功", message)
        else: QMessageBox.critical(self, "失败", message)
        self.preview_button_sub.setEnabled(True); self.start_button_sub.setEnabled(True)

    def create_batch_transcode_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        list_control_layout = QHBoxLayout(); self.add_files_button = QPushButton("添加文件..."); self.clear_list_button = QPushButton("清空列表")
        list_control_layout.addWidget(self.add_files_button); list_control_layout.addWidget(self.clear_list_button); list_control_layout.addStretch()
        self.batch_list_widget = QListWidget(); self.batch_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addLayout(list_control_layout); layout.addWidget(self.batch_list_widget)
        output_path_layout = QHBoxLayout(); self.output_dir_line_edit = QLineEdit(); self.output_dir_browse_button = QPushButton("浏览...")
        output_path_layout.addWidget(QLabel("输出文件夹:")); output_path_layout.addWidget(self.output_dir_line_edit); output_path_layout.addWidget(self.output_dir_browse_button)
        layout.addLayout(output_path_layout)
        params_layout = QHBoxLayout(); self.batch_format_combo = QComboBox()
        self.batch_format_combo.addItems(["mp4", "mkv", "mov", "ts", "flv", "webm", "avi", "提取 aac", "提取 mp3", "提取 flac", "提取 wav", "提取 opus"])
        self.batch_codec_combo = QComboBox(); self.batch_codec_combo.addItems(["h264_nvenc (N卡)", "hevc_nvenc (N卡)", "libx264 (CPU)", "copy (不转码)"])
        params_layout.addWidget(QLabel("目标格式:")); params_layout.addWidget(self.batch_format_combo); params_layout.addStretch()
        params_layout.addWidget(QLabel("视频编码器:")); params_layout.addWidget(self.batch_codec_combo)
        layout.addLayout(params_layout)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); layout.addWidget(line)
        self.batch_progress_label = QLabel("等待任务..."); self.batch_progress_bar = QProgressBar()
        self.batch_log_output = QTextEdit(); self.batch_log_output.setReadOnly(True)
        layout.addWidget(self.batch_progress_label); layout.addWidget(self.batch_progress_bar)
        layout.addWidget(QLabel("日志输出:")); layout.addWidget(self.batch_log_output)
        self.start_batch_button = QPushButton("开始处理列表"); layout.addWidget(self.start_batch_button)
        self.tabs.addTab(tab, "批量转码")
        self.add_files_button.clicked.connect(self.add_files_to_batch)
        self.clear_list_button.clicked.connect(self.batch_list_widget.clear)
        self.output_dir_browse_button.clicked.connect(lambda: self.browse_output_dir(self.output_dir_line_edit))
        self.start_batch_button.clicked.connect(self.start_batch_transcoding)
        
    def start_batch_transcoding(self):
        if self.batch_list_widget.count() == 0: QMessageBox.warning(self, "提示", "请先添加要处理的文件到列表！"); return
        output_dir = self.output_dir_line_edit.text()
        if not output_dir or not os.path.isdir(output_dir): QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return
        file_queue = [self.batch_list_widget.item(i).text() for i in range(self.batch_list_widget.count())]
        transcode_options = {'format': self.batch_format_combo.currentText(), 'codec': self.batch_codec_combo.currentText(), 'output_dir': output_dir}
        self.start_batch_button.setEnabled(False); self.add_files_button.setEnabled(False); self.clear_list_button.setEnabled(False)
        self.batch_log_output.clear()
        self.thread = QThread()
        self.worker = BatchTranscodeWorker(self.ffmpeg_path, self.ffprobe_path, file_queue, transcode_options)
        self.worker.moveToThread(self.thread)
        self.worker.file_started.connect(self.batch_progress_label.setText)
        self.worker.file_progress.connect(self.batch_progress_bar.setValue)
        self.worker.log_message.connect(self.batch_log_output.append)
        self.worker.file_finished.connect(self.on_batch_file_finished)
        self.worker.batch_finished.connect(self.on_batch_all_finished)
        self.worker.batch_finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def add_files_to_batch(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要处理的文件", "", self.media_filter)
        if files: self.batch_list_widget.addItems(files)

    @Slot(int)
    def on_batch_file_finished(self, return_code):
        self.batch_progress_bar.setValue(100)
        if return_code != 0: self.batch_log_output.append(f"\n❌ 上一个任务失败 (代码: {return_code})。\n")
        else: self.batch_log_output.append(f"\n✅ 上一个任务成功。\n")

    @Slot()
    def on_batch_all_finished(self):
        self.start_batch_button.setEnabled(True); self.add_files_button.setEnabled(True); self.clear_list_button.setEnabled(True)
        self.batch_progress_label.setText("所有任务已完成！")
        self.batch_progress_bar.setValue(0)
        QMessageBox.information(self, "完成", "批量处理已全部完成！")

    def browse_file(self, line_edit_widget, caption, file_filter="所有文件 (*.*)"):
        file_path, _ = QFileDialog.getOpenFileName(self, caption, "", file_filter)
        if file_path: line_edit_widget.setText(file_path)

    def browse_output_dir(self, line_edit_widget):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if dir_path:
            line_edit_widget.setText(dir_path)

    def create_batch_clip_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        source_video_layout = QHBoxLayout()
        self.clip_source_video = QLineEdit(); self.clip_source_browse_btn = QPushButton("浏览源视频...")
        source_video_layout.addWidget(QLabel("源视频文件:")); source_video_layout.addWidget(self.clip_source_video)
        source_video_layout.addWidget(self.clip_source_browse_btn); layout.addLayout(source_video_layout)
        self.clip_table = QTableWidget()
        self.clip_table.setColumnCount(3)
        self.clip_table.setHorizontalHeaderLabels(["片段名称", "开始时间", "结束时间"])
        self.clip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        clip_buttons_layout = QHBoxLayout()
        self.add_clip_btn = QPushButton("添加片段..."); self.remove_clip_btn = QPushButton("删除选中"); self.clear_clips_btn = QPushButton("清空列表")
        clip_buttons_layout.addWidget(self.add_clip_btn); clip_buttons_layout.addWidget(self.remove_clip_btn)
        clip_buttons_layout.addWidget(self.clear_clips_btn); clip_buttons_layout.addStretch()
        layout.addLayout(clip_buttons_layout); layout.addWidget(self.clip_table)
        output_path_layout = QHBoxLayout(); self.clip_output_dir = QLineEdit(); self.clip_output_browse_btn = QPushButton("浏览...")
        output_path_layout.addWidget(QLabel("输出文件夹:")); output_path_layout.addWidget(self.clip_output_dir)
        output_path_layout.addWidget(self.clip_output_browse_btn); layout.addLayout(output_path_layout)
        params_layout = QHBoxLayout(); self.clip_format_combo = QComboBox()
        self.clip_format_combo.addItems(["mp4", "mkv", "ts", "mp3", "aac", "flac"])
        self.clip_codec_combo = QComboBox(); self.clip_codec_combo.addItems(["copy (无损复制)", "h264_nvenc (N卡)", "libx264 (CPU)"])
        params_layout.addWidget(QLabel("输出格式:")); params_layout.addWidget(self.clip_format_combo); params_layout.addStretch()
        params_layout.addWidget(QLabel("视频编码器:")); params_layout.addWidget(self.clip_codec_combo)
        layout.addLayout(params_layout)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); layout.addWidget(line)
        self.clip_progress_label = QLabel("等待任务...")
        self.clip_log_output = QTextEdit(); self.clip_log_output.setReadOnly(True)
        layout.addWidget(self.clip_progress_label); layout.addWidget(QLabel("日志输出:")); layout.addWidget(self.clip_log_output)
        self.start_clip_button = QPushButton("开始批量裁剪"); layout.addWidget(self.start_clip_button)
        self.tabs.addTab(tab, "批量裁剪")
        self.clip_source_browse_btn.clicked.connect(lambda: self.browse_file(self.clip_source_video, "选择源视频", self.video_filter))
        self.add_clip_btn.clicked.connect(self.add_clip_item)
        self.remove_clip_btn.clicked.connect(self.remove_clip_item)
        self.clear_clips_btn.clicked.connect(lambda: self.clip_table.setRowCount(0))
        self.clip_table.itemDoubleClicked.connect(self.edit_clip_item)
        self.clip_output_browse_btn.clicked.connect(lambda: self.browse_output_dir(self.clip_output_dir))
        self.start_clip_button.clicked.connect(self.start_batch_clipping)

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

    def edit_clip_item(self, item):
        row = item.row()
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
        for index in sorted(selected_rows, reverse=True):
            self.clip_table.removeRow(index.row())

    def start_batch_clipping(self):
        source_video = self.clip_source_video.text(); output_dir = self.clip_output_dir.text()
        if not (source_video and os.path.exists(source_video)): QMessageBox.warning(self, "错误", "请选择一个有效的源视频文件！"); return
        if not (output_dir and os.path.isdir(output_dir)): QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return
        if self.clip_table.rowCount() == 0: QMessageBox.warning(self, "提示", "请至少添加一个裁剪片段！"); return
        time_pattern = re.compile(r'^\d{1,2}:\d{2}:\d{2}(\.\d+)?$|^\d{1,2}:\d{2}(\.\d+)?$')
        clip_list = []
        for row in range(self.clip_table.rowCount()):
            name = self.clip_table.item(row, 0).text(); start = self.clip_table.item(row, 1).text(); end = self.clip_table.item(row, 2).text()
            if not time_pattern.match(start): QMessageBox.warning(self, "格式错误", f"片段 '{name}' 的开始时间 '{start}' 格式不正确！\n\n有效格式为 HH:MM:SS 或 MM:SS。"); return
            if not time_pattern.match(end): QMessageBox.warning(self, "格式错误", f"片段 '{name}' 的结束时间 '{end}' 格式不正确！\n\n有效格式为 HH:MM:SS 或 MM:SS。"); return
            clip_list.append({'name': name, 'start': start, 'end': end})
        options = {'output_dir': output_dir, 'format': self.clip_format_combo.currentText(), 'codec': self.clip_codec_combo.currentText()}
        self.start_clip_button.setEnabled(False); self.clip_log_output.clear()
        self.thread = QThread(); self.worker = BatchClipWorker(self.ffmpeg_path, source_video, clip_list, options)
        self.worker.moveToThread(self.thread); self.worker.clip_started.connect(self.clip_progress_label.setText)
        self.worker.log_message.connect(self.clip_log_output.append); self.worker.clip_finished.connect(self.on_clip_file_finished)
        self.worker.batch_finished.connect(self.on_clip_all_finished); self.worker.batch_finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run); self.thread.start()

    @Slot(int, str)
    def on_clip_file_finished(self, return_code, temp_filepath):
        if return_code != 0: self.clip_log_output.append(f"❌ 文件 {os.path.basename(temp_filepath)} 裁剪失败 (代码: {return_code})。\n")
        else: self.clip_log_output.append(f"✅ 文件 {os.path.basename(temp_filepath)} 裁剪成功。\n")

    @Slot()
    def on_clip_all_finished(self):
        self.clip_log_output.append("\n--- 所有片段裁剪完成，开始重命名并生成记录... ---")
        output_dir = self.worker.options['output_dir']; ext = self.worker.options['format']; clip_list = self.worker.clip_list
        for i, clip_info in enumerate(clip_list):
            temp_filename = f"{i+1:03d}.{ext}"; temp_filepath = os.path.join(output_dir, temp_filename)
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", clip_info['name'])
            final_filename = f"{safe_name}.{ext}"; final_filepath = os.path.join(output_dir, final_filename)
            if os.path.exists(temp_filepath):
                try: os.rename(temp_filepath, final_filepath); self.clip_log_output.append(f"重命名: {temp_filename} -> {final_filename}")
                except OSError as e: self.clip_log_output.append(f"❌ 重命名失败: {e}")
        record_file_path = os.path.join(output_dir, "clip_record.txt")
        try:
            with open(record_file_path, 'w', encoding='utf-8') as f:
                f.write("--- 批量裁剪记录 ---\n"); f.write(f"源文件: {self.worker.source_video}\n\n")
                for clip in clip_list: f.write(f"名称: {clip['name']}\n"); f.write(f"开始: {clip['start']}\n"); f.write(f"结束: {clip['end']}\n\n")
            self.clip_log_output.append(f"✅ 裁剪记录已保存到: {record_file_path}")
        except IOError as e: self.clip_log_output.append(f"❌ 保存记录文件失败: {e}")
        self.start_clip_button.setEnabled(True); self.clip_progress_label.setText("所有任务已完成！")
        QMessageBox.information(self, "完成", "批量裁剪已全部完成！")

    def create_video_from_bg_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        audio_source_layout = QHBoxLayout()
        self.vbg_audio_source = QLineEdit()
        self.vbg_audio_browse_btn = QPushButton("浏览音频/视频源...")
        audio_source_layout.addWidget(QLabel("音频源文件:"))
        audio_source_layout.addWidget(self.vbg_audio_source)
        audio_source_layout.addWidget(self.vbg_audio_browse_btn)
        layout.addLayout(audio_source_layout)
        bg_image_layout = QHBoxLayout()
        self.vbg_bg_image = QLineEdit()
        self.vbg_bg_browse_btn = QPushButton("浏览背景图片...")
        self.vbg_preview_crop_btn = QPushButton("裁剪预览...")
        bg_image_layout.addWidget(QLabel("背景图片:"))
        bg_image_layout.addWidget(self.vbg_bg_image)
        bg_image_layout.addWidget(self.vbg_bg_browse_btn); bg_image_layout.addWidget(self.vbg_preview_crop_btn)
        layout.addLayout(bg_image_layout)
        output_path_layout = QHBoxLayout()
        self.vbg_output_dir = QLineEdit()
        self.vbg_output_browse_btn = QPushButton("浏览...")
        output_path_layout.addWidget(QLabel("输出文件夹:"))
        output_path_layout.addWidget(self.vbg_output_dir)
        output_path_layout.addWidget(self.vbg_output_browse_btn)
        layout.addLayout(output_path_layout)
        params_layout = QGridLayout()
        self.vbg_resolution_combo = QComboBox()
        self.vbg_resolution_combo.addItems(["1920x1080 (1080p 横屏)", "1080x1920 (1080p 竖屏)", "1280x720 (720p 横屏)"])
        self.vbg_format_combo = QComboBox()
        self.vbg_format_combo.addItems(["mp4", "mkv", "mov"])
        self.vbg_codec_combo = QComboBox()
        self.vbg_codec_combo.addItems(["h264_nvenc (N卡)", "hevc_nvenc (N卡)", "libx264 (CPU)"])
        params_layout.addWidget(QLabel("输出分辨率:"), 0, 0); params_layout.addWidget(self.vbg_resolution_combo, 0, 1)
        params_layout.addWidget(QLabel("输出格式:"), 1, 0); params_layout.addWidget(self.vbg_format_combo, 1, 1)
        params_layout.addWidget(QLabel("视频编码器:"), 2, 0); params_layout.addWidget(self.vbg_codec_combo, 2, 1)
        layout.addLayout(params_layout)
        layout.addStretch()
        self.vbg_progress_bar = QProgressBar()
        self.vbg_log_output = QTextEdit(); self.vbg_log_output.setReadOnly(True)
        layout.addWidget(self.vbg_progress_bar)
        layout.addWidget(QLabel("日志输出:")); layout.addWidget(self.vbg_log_output)
        self.start_vbg_button = QPushButton("开始合成")
        layout.addWidget(self.start_vbg_button)
        self.tabs.addTab(tab, "视频换背景")
        self.vbg_audio_browse_btn.clicked.connect(lambda: self.browse_file(self.vbg_audio_source, "选择音频或视频源", self.media_filter))
        self.vbg_bg_browse_btn.clicked.connect(lambda: self.browse_file(self.vbg_bg_image, "选择背景图片", "图片文件 (*.jpg *.jpeg *.png)"))
        self.vbg_preview_crop_btn.clicked.connect(self.open_crop_dialog)
        self.vbg_output_browse_btn.clicked.connect(lambda: self.browse_output_dir(self.vbg_output_dir))
        self.start_vbg_button.clicked.connect(self.start_video_from_bg)

    def open_crop_dialog(self):
        bg_image = self.vbg_bg_image.text()
        if not (bg_image and os.path.exists(bg_image)): QMessageBox.warning(self, "错误", "请先选择一个有效的背景图片！"); return
        res_text = self.vbg_resolution_combo.currentText().split(" ")[0]
        w, h = map(int, res_text.split('x'))
        target_ratio = w / h
        dialog = ImageCropDialog(bg_image, target_ratio, self)
        if dialog.exec():
            self.vbg_crop_filter = dialog.get_crop_filter()
            self.vbg_log_output.append(f"ℹ️ 已设置裁剪参数: {self.vbg_crop_filter}")
        else:
            self.vbg_crop_filter = None
            self.vbg_log_output.append("ℹ️ 用户取消了裁剪操作。")

    def start_video_from_bg(self):
        audio_source = self.vbg_audio_source.text(); bg_image = self.vbg_bg_image.text(); output_dir = self.vbg_output_dir.text()
        if not (audio_source and os.path.exists(audio_source)): QMessageBox.warning(self, "错误", "请选择一个有效的音频/视频源文件！"); return
        if not (bg_image and os.path.exists(bg_image)): QMessageBox.warning(self, "错误", "请选择一个有效的背景图片！"); return
        if not (output_dir and os.path.isdir(output_dir)): QMessageBox.warning(self, "错误", "请选择一个有效的输出文件夹！"); return
        self.start_vbg_button.setEnabled(False); self.vbg_log_output.clear(); self.vbg_progress_bar.setValue(0)
        params = {
            'audio_source': audio_source, 'bg_image': bg_image, 'output_dir': output_dir,
            'resolution': self.vbg_resolution_combo.currentText().split(" ")[0],
            'format': self.vbg_format_combo.currentText(), 'codec': self.vbg_codec_combo.currentText(),
            'crop_filter': self.vbg_crop_filter
        }
        self.thread = QThread()
        self.worker = VideoFromBgWorker(self.ffmpeg_path, self.ffprobe_path, params)
        self.worker.moveToThread(self.thread)
        self.worker.log_message.connect(self.vbg_log_output.append)
        self.worker.progress.connect(self.vbg_progress_bar.setValue)
        self.worker.finished.connect(self.on_vbg_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(int, str)
    def on_vbg_finished(self, return_code, message):
        self.vbg_progress_bar.setValue(100); QApplication.processEvents()
        if return_code == 0: QMessageBox.information(self, "成功", message)
        else: QMessageBox.critical(self, "失败", message)
        self.start_vbg_button.setEnabled(True)
        self.vbg_crop_filter = None