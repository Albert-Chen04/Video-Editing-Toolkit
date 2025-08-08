# ui/tabs/frame_export_tab.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QSlider, QFrame, QApplication, QFileDialog, QMessageBox, QStyle)
from PySide6.QtCore import Qt, QUrl, QThread, Slot
# 【修改】额外导入 QAudioOutput 用于处理音频
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.workers.frame_export_worker import FrameExportWorker

class FrameExportTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.player = None
        self.audio_output = None # 【新增】为音频输出声明一个变量
        self.current_video_path = ""
        self.thread = None
        self.worker = None

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        # --- 视频播放器核心组件 ---
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)

        # 【新增】创建并设置音频输出
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # --- 控制按钮 ---
        self.open_button = QPushButton("打开视频文件...")
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.prev_frame_button = QPushButton("上一帧")
        self.next_frame_button = QPushButton("下一帧")
        self.export_button = QPushButton("导出当前静帧...")
        
        # --- 进度条和时间显示 ---
        self.position_slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        
        # --- 初始状态 ---
        self.set_controls_enabled(False)

    def create_layouts(self):
        main_layout = QVBoxLayout(self)
        
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.open_button)
        top_layout.addStretch()

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.play_pause_button)
        control_layout.addWidget(self.prev_frame_button)
        control_layout.addWidget(self.next_frame_button)
        control_layout.addWidget(self.position_slider)
        control_layout.addWidget(self.time_label)
        control_layout.addWidget(self.export_button)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.video_widget, 1) # 视频区域占据主要空间
        main_layout.addLayout(control_layout)

    def create_connections(self):
        self.open_button.clicked.connect(self.open_video_file)
        self.play_pause_button.clicked.connect(self.play_pause_video)
        
        self.player.playbackStateChanged.connect(self.update_play_button_icon)
        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.setup_slider_duration)
        
        self.position_slider.sliderMoved.connect(self.set_player_position)
        self.position_slider.sliderReleased.connect(self.sync_time_label)

        self.prev_frame_button.clicked.connect(lambda: self.step_frame(forward=False))
        self.next_frame_button.clicked.connect(lambda: self.step_frame(forward=True))

        self.export_button.clicked.connect(self.export_current_frame)

    def open_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", self.main_window.video_filter)
        if file_path:
            self.current_video_path = file_path
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.set_controls_enabled(True)
            self.player.play()

    def play_pause_video(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def update_play_button_icon(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def update_slider_position(self, position_ms):
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position_ms)
        self.update_time_label(position_ms)
        
    def setup_slider_duration(self, duration_ms):
        self.position_slider.setRange(0, duration_ms)
        self.update_time_label(self.player.position())

    def set_player_position(self, position_ms):
        self.player.setPosition(position_ms)
        self.update_time_label(position_ms)

    def step_frame(self, forward=True):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        
        current_pos = self.player.position()
        frame_duration_ms = 40 
        
        target_pos = current_pos + frame_duration_ms if forward else max(0, current_pos - frame_duration_ms)
        self.player.setPosition(target_pos)
        QApplication.processEvents()
        self.update_time_label(self.player.position())

    def update_time_label(self, position_ms):
        duration_ms = self.player.duration()
        self.time_label.setText(f"{self.format_time(position_ms)} / {self.format_time(duration_ms)}")

    def sync_time_label(self):
        self.update_time_label(self.player.position())

    def export_current_frame(self):
        if not self.current_video_path or self.player.duration() <= 0:
            QMessageBox.warning(self, "错误", "请先加载一个有效的视频。")
            return
        
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            
        current_pos_ms = self.player.position()
        timestamp_secs = current_pos_ms / 1000.0

        base_name = os.path.splitext(os.path.basename(self.current_video_path))[0]
        time_str = self.format_time(current_pos_ms).replace(":", "-").replace(".", "_")
        default_filename = f"{base_name}_frame_at_{time_str}.png"
        
        output_path, _ = QFileDialog.getSaveFileName(self, "保存静帧为...", default_filename, "PNG 高质量 (*.png);;JPEG 高质量 (*.jpg);;BMP 无损 (*.bmp);;TIFF 无损 (*.tiff)")
        
        if not output_path:
            return

        self.export_button.setEnabled(False)
        self.thread = QThread()
        self.worker = FrameExportWorker(
            self.main_window.ffmpeg_path,
            self.current_video_path,
            timestamp_secs,
            output_path
        )
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @Slot(bool, str)
    def on_export_finished(self, success, msg):
        self.export_button.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", f"静帧已成功导出到：\n{msg}")
        else:
            QMessageBox.critical(self, "导出失败", msg)

    def set_controls_enabled(self, enabled):
        self.play_pause_button.setEnabled(enabled)
        self.prev_frame_button.setEnabled(enabled)
        self.next_frame_button.setEnabled(enabled)
        self.position_slider.setEnabled(enabled)
        self.export_button.setEnabled(enabled)

    @staticmethod
    def format_time(ms):
        s = ms // 1000
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        ms = ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"