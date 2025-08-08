# ui/dialogs.py
# 文件作用：存放项目中所有自定义的对话框窗口。
# 例如：预览图显示、片段信息编辑、背景图裁剪，以及新增的可视化定位。

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QGridLayout, QRubberBand)
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen

class ImageCropDialog(QDialog):
    """
    一个用于裁剪背景图片的对话框。
    允许用户通过拖动和滚轮缩放来选择图片的裁剪区域。
    """
    def __init__(self, image_path, target_aspect_ratio, parent=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪背景图 (拖动/滚轮缩放)")
        self.image_path = image_path
        self.target_aspect_ratio = target_aspect_ratio
        self.pixmap = QPixmap(image_path)
        self.current_scale = 1.0
        self.current_pos = QPoint(0, 0)
        self.view_label = QLabel()
        self.view_label.setFixedSize(800, 600)
        self.view_label.setStyleSheet("background-color: #333;")
        self.view_label.setAlignment(Qt.AlignCenter)
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.view_label)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.view_label)
        button_box = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        main_layout.addLayout(button_box)
        self.setLayout(main_layout)
        self.update_crop_area()
        self.update_view()

    def update_crop_area(self):
        view_size = self.view_label.size()
        view_ratio = view_size.width() / view_size.height()
        if self.target_aspect_ratio > view_ratio:
            width = view_size.width()
            height = int(width / self.target_aspect_ratio)
        else:
            height = view_size.height()
            width = int(height * self.target_aspect_ratio)
        top_left = QPoint((view_size.width() - width) // 2, (view_size.height() - height) // 2)
        self.rubber_band.setGeometry(QRect(top_left, QSize(width, height)))

    def update_view(self):
        canvas = QPixmap(self.view_label.size())
        canvas.fill(Qt.darkGray)
        painter = QPainter(canvas)
        scaled_pixmap = self.pixmap.scaled(int(self.pixmap.width() * self.current_scale), int(self.pixmap.height() * self.current_scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        draw_pos = self.current_pos + QPoint((self.view_label.width() - scaled_pixmap.width()) // 2, (self.view_label.height() - scaled_pixmap.height()) // 2)
        painter.drawPixmap(draw_pos, scaled_pixmap)
        painter.end()
        self.view_label.setPixmap(canvas)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.current_scale *= 1.1
        else:
            self.current_scale *= 0.9
        self.update_view()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.current_pos += event.pos() - self.drag_start_position
            self.drag_start_position = event.pos()
            self.update_view()

    def get_crop_filter(self):
        crop_rect = self.rubber_band.geometry()
        view_size = self.view_label.size()
        scaled_pixmap_size = self.pixmap.size() * self.current_scale
        img_top_left = self.current_pos + QPoint((view_size.width() - scaled_pixmap_size.width()) // 2, (view_size.height() - scaled_pixmap_size.height()) // 2)
        crop_x_in_img = crop_rect.x() - img_top_left.x()
        crop_y_in_img = crop_rect.y() - img_top_left.y()
        final_x = int(crop_x_in_img / self.current_scale)
        final_y = int(crop_y_in_img / self.current_scale)
        final_w = int(crop_rect.width() / self.current_scale)
        final_h = int(crop_rect.height() / self.current_scale)
        return f"crop={final_w}:{final_h}:{final_x}:{final_y}"

class ClipDialog(QDialog):
    """
    一个用于添加或编辑裁剪片段信息的对话框。
    包含名称、开始时间和结束时间的输入框。
    """
    def __init__(self, parent=None, name="", start="", end=""):
        super().__init__(parent)
        self.setWindowTitle("添加/编辑片段")
        layout = QGridLayout(self)
        self.name_edit = QLineEdit(name)
        self.start_edit = QLineEdit(start)
        self.end_edit = QLineEdit(end)
        layout.addWidget(QLabel("片段名称:"), 0, 0)
        layout.addWidget(self.name_edit, 0, 1)
        layout.addWidget(QLabel("开始时间 (HH:MM:SS):"), 1, 0)
        layout.addWidget(self.start_edit, 1, 1)
        layout.addWidget(QLabel("结束时间 (HH:MM:SS):"), 2, 0)
        layout.addWidget(self.end_edit, 2, 1)
        button_box = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box, 3, 0, 1, 2)

    def get_data(self):
        return self.name_edit.text(), self.start_edit.text(), self.end_edit.text()

class PreviewDialog(QDialog):
    """
    一个用于显示预览图的对话框。
    支持鼠标滚轮缩放图片。
    """
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("效果预览 (滚动滚轮缩放)")
        self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull():
            self.label = QLabel(f"错误：无法加载预览图片！\n路径: {image_path}", self)
            layout = QVBoxLayout()
            layout.addWidget(self.label)
            self.setLayout(layout)
            return

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.image_label)
        self.setLayout(main_layout)
        self.scale_factor = 1.0
        initial_width = self.original_pixmap.width()
        if initial_width > 800:
            self.scale_factor = 800 / initial_width
        self.update_image_display()

    def update_image_display(self):
        if self.original_pixmap.isNull(): return
        new_width = int(self.original_pixmap.width() * self.scale_factor)
        new_height = int(self.original_pixmap.height() * self.scale_factor)
        scaled_pixmap = self.original_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.resize(new_width + 20, new_height + 20)

    def wheelEvent(self, event):
        if self.original_pixmap.isNull(): return
        if event.angleDelta().y() > 0:
            self.scale_factor *= 1.25
        else:
            self.scale_factor *= 0.8
        if self.original_pixmap.width() * self.scale_factor < 100:
            self.scale_factor = 100 / self.original_pixmap.width()
        self.update_image_display()

class PositioningPreviewDialog(QDialog):
    """
    一个用于可视化拖动定位视频位置的对话框。
    """
    def __init__(self, canvas_size, video_size, initial_x, parent=None):
        super().__init__(parent)
        self.setWindowTitle("可视化视频定位 (请拖动内部方块)")

        # 1. 原始尺寸和位置
        self.canvas_width, self.canvas_height = canvas_size
        self.video_width, self.video_height = video_size
        self.current_x = initial_x
        
        # 2. 计算缩放比例以适应对话框
        self.view_width = 800  # 对话框预览区域的固定宽度
        self.scale_factor = self.view_width / self.canvas_width
        self.view_height = int(self.canvas_height * self.scale_factor)
        
        # 3. UI设置
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(self.view_width, self.view_height)
        self.preview_label.setStyleSheet("background-color: #555;")
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.preview_label)
        
        button_box = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        main_layout.addLayout(button_box)
        
        self.setLayout(main_layout)

        self._dragging = False
        self._drag_start_x_offset = 0
        self.update_preview()

    def update_preview(self):
        """重新绘制预览区域"""
        pixmap = QPixmap(self.view_width, self.view_height)
        pixmap.fill(QColor("#333333")) # 深灰色背景
        painter = QPainter(pixmap)

        # 绘制画布
        canvas_rect_scaled = QRect(0, 0, self.view_width, self.view_height)
        painter.setBrush(QBrush(QColor("#ADD8E6"))) # 浅蓝色画布
        painter.setPen(Qt.NoPen)
        painter.drawRect(canvas_rect_scaled)

        # 绘制视频
        video_rect_scaled = QRect(
            int(self.current_x * self.scale_factor),
            0,
            int(self.video_width * self.scale_factor),
            self.view_height
        )
        painter.setBrush(QBrush(QColor("#808080"))) # 灰色代表视频
        painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
        painter.drawRect(video_rect_scaled)
        
        painter.end()
        self.preview_label.setPixmap(pixmap)
    
    def mousePressEvent(self, event):
        # PySide6/PyQt6 use event.position() which returns a QPointF
        mouse_pos = event.position()
        scaled_video_rect = QRect(
            int(self.current_x * self.scale_factor),
            0,
            int(self.video_width * self.scale_factor),
            self.view_height
        )
        
        # 判断鼠标是否点在视频区域内
        if scaled_video_rect.contains(QPoint(int(mouse_pos.x()), int(mouse_pos.y()))):
            self._dragging = True
            self._drag_start_x_offset = mouse_pos.x() - scaled_video_rect.x()
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            mouse_pos = event.position()
            # 计算新的X坐标（以缩放后的尺寸为准）
            new_scaled_x = mouse_pos.x() - self._drag_start_x_offset
            
            # 限制拖动范围
            max_scaled_x = self.view_width - (self.video_width * self.scale_factor)
            new_scaled_x = max(0, min(new_scaled_x, max_scaled_x))
            
            # 将缩放后的坐标转换回原始坐标
            self.current_x = int(new_scaled_x / self.scale_factor)
            self.update_preview()
            
    def mouseReleaseEvent(self, event):
        self._dragging = False

    def get_position(self):
        """返回最终确定的原始X坐标"""
        return self.current_x