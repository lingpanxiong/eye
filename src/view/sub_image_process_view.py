from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsView, QGraphicsScene, QDoubleSpinBox, QPushButton, QFileDialog
from PyQt5.QtGui import QPixmap
#from src.utils.ImageTransform import ImageTransform  # 假设 ImageTransform 模块存在

"""导入python内置模块"""
import os
import sys
"""导入python三方模块"""
import cv2
import piexif
import numpy as np
from PyQt5 import QtWidgets
from PIL import Image, ImageEnhance
from PyQt5.QtGui import QPixmap, QMouseEvent, QColor, QTransform , QImage
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QFileDialog)

class ImageTransform:
    """图片旋转exif信息调整类"""
    # 定义EXIF方向值对应的QTransform变换
    _ORIENTATION_TRANSFORMS = {
        1: QTransform(),  # 0度 - 正常
        2: QTransform().scale(-1, 1),  # 水平翻转
        3: QTransform().rotate(180),  # 180度
        4: QTransform().scale(1, -1),  # 垂直翻转
        5: QTransform().rotate(90).scale(-1, 1),  # 顺时针90度+水平翻转
        6: QTransform().rotate(90),  # 顺时针90度
        7: QTransform().rotate(-90).scale(-1, 1),  # 逆时针90度+水平翻转
        8: QTransform().rotate(-90)  # 逆时针90度
    }

    @classmethod
    def get_orientation(cls, image_path):
        """获取图片的EXIF方向信息"""
        try:
            img = Image.open(image_path)
            exif_dict = piexif.load(img.info.get('exif', b''))
            if '0th' in exif_dict and piexif.ImageIFD.Orientation in exif_dict['0th']:
                return exif_dict['0th'][piexif.ImageIFD.Orientation]
            return 1  # 默认方向
        except piexif.InvalidImageDataError:
            print("图片没有EXIF信息，使用默认方向")
            return 1  # 无EXIF信息时返回默认方向
        except Exception as e:
            print(f"读取EXIF方向信息失败: {str(e)}")
            return 1  # 出错时返回默认方向
        finally:
            if 'img' in locals():
                img.close()

    @classmethod
    def auto_rotate_image(cls, icon_path: str) -> QPixmap:
        try:
            # 获取EXIF方向信息
            orientation = cls.get_orientation(icon_path)
            
            # 创建QPixmap
            pixmap = QPixmap(icon_path)
            
            # 应用方向变换
            transform = cls._ORIENTATION_TRANSFORMS.get(orientation, QTransform())
            if not transform.isIdentity():  # 只在需要变换时执行
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
            
            return pixmap
            
        except Exception as e:
            print(f"处理图片失败 {icon_path}: {str(e)}")
            return QPixmap()





class GraphicsView(QGraphicsView):
    zoomChanged = pyqtSignal(float)  # 缩放变化信号，通知外部
    
    def __init__(self, parent=None, pick_color_callback=None):
        super().__init__(parent)
        self.pick_color_callback = pick_color_callback
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # 设置缩放锚点为鼠标位置
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.zoom_factor = 1.0  # 初始缩放因子
        
    def wheelEvent(self, event):
        """重写鼠标滚轮事件以实现缩放功能"""
        # 获取 Alt 键状态
        alt_pressed = event.modifiers() & Qt.AltModifier
        
        # 计算缩放因子
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        
        # 保存当前鼠标在场景中的位置
        old_pos = self.mapToScene(event.pos())
        
        # 进行缩放
        self.scale(zoom_factor, zoom_factor)
        
        # 更新缩放因子并发送信号
        self.zoom_factor *= zoom_factor
        self.zoomChanged.emit(self.zoom_factor)
        
        # 如果按住 Alt 键，确保鼠标位置保持不变
        if alt_pressed:
            new_pos = self.mapToScene(event.pos())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())


class SubCompare(QWidget):
    closed = pyqtSignal()  # 添加关闭信号
    
    def __init__(self, image_path=None):
        super().__init__()
        
        # 初始化变量
        self.sync_zoom = True  # 是否同步缩放两张图片
        self.last_zoom_factor = 1.0  # 上次缩放因子
        
        # 获取鼠标所在屏幕，并根据当前屏幕计算界面大小与居中位置，调整大小并移动到该位置
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        screen_geometry = QtWidgets.QApplication.desktop().screenGeometry(screen)
        width = int(screen_geometry.width() * 0.6)
        height = int(screen_geometry.height() * 0.8)
        self.resize(width, height)
        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
        # 初始化UI
        self.initUI()
        
        # 存储选中的颜色
        self.selected_color = None  
        
        # 初始化图片
        if image_path:
            self.original_pixmap = ImageTransform.auto_rotate_image(image_path)
            if self.original_pixmap.isNull():
                self.original_pixmap = QPixmap()  # 设置为空
            else:
                self.update_images()
        else:
            self.original_pixmap = QPixmap()  # 默认空白


    def initUI(self):
        # 创建布局
        main_layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        image_layout = QHBoxLayout()
        control_layout = QHBoxLayout()
        
        # 创建标签
        label_before = QLabel('修改前', self)
        label_after = QLabel('修改后', self)
        
        # 设置标签的对齐方式为水平和垂直居中
        label_before.setAlignment(Qt.AlignCenter)
        label_after.setAlignment(Qt.AlignCenter)
        
        # 将标签添加到标签布局
        label_layout.addWidget(label_before)
        label_layout.addWidget(label_after)
        
        # 创建QGraphicsView和QGraphicsScene用于显示图片
        self.view_before = GraphicsView(self)  # 原始图片视图，支持缩放
        self.view_after = GraphicsView(self, pick_color_callback=self.pick_color)  # 修改后图片视图，支持取色和缩放
        
        # 设置背景色为 #7F7F7F
        self.view_before.setStyleSheet("background-color: #7F7F7F;")
        self.view_after.setStyleSheet("background-color: #7F7F7F;")
        
        self.scene_before = QGraphicsScene(self)
        self.scene_after = QGraphicsScene(self)
        # 设置场景到视图
        self.view_before.setScene(self.scene_before)
        self.view_after.setScene(self.scene_after)
        
        # 连接缩放信号
        self.view_before.zoomChanged.connect(lambda factor: self.on_zoom_changed(factor, True))
        self.view_after.zoomChanged.connect(lambda factor: self.on_zoom_changed(factor, False))
        
        # 将视图添加到图片布局
        image_layout.addWidget(self.view_before)
        image_layout.addWidget(self.view_after)
        
        # 创建双精度旋转框和标签
        red_label = QLabel('红色:', self)
        self.red_spinbox = QDoubleSpinBox(self)
        self.red_spinbox.setRange(-255.0, 255.0)
        self.red_spinbox.setValue(0.0)

        green_label = QLabel('绿色:', self)
        self.green_spinbox = QDoubleSpinBox(self)
        self.green_spinbox.setRange(-255.0, 255.0)
        self.green_spinbox.setValue(0.0)

        blue_label = QLabel('蓝色:', self)
        self.blue_spinbox = QDoubleSpinBox(self)
        self.blue_spinbox.setRange(-255.0, 255.0)
        self.blue_spinbox.setValue(0.0)

        saturation_label = QLabel('饱和度:', self)
        self.saturation_spinbox = QDoubleSpinBox(self)
        self.saturation_spinbox.setRange(-1.0, 1.0)
        self.saturation_spinbox.setSingleStep(0.01)  # 增加精度
        self.saturation_spinbox.setValue(0.0)

        contrast_label = QLabel('对比度:', self)
        self.contrast_spinbox = QDoubleSpinBox(self)
        self.contrast_spinbox.setRange(-1.0, 1.0)
        self.contrast_spinbox.setSingleStep(0.01)  # 增加精度
        self.contrast_spinbox.setValue(0.0)

        exposure_label = QLabel('曝光:', self)
        self.exposure_spinbox = QDoubleSpinBox(self)
        self.exposure_spinbox.setRange(-1.0, 1.0)
        self.exposure_spinbox.setSingleStep(0.01)
        self.exposure_spinbox.setValue(0.0)

        sharpness_label = QLabel('锐度:', self)
        self.sharpness_spinbox = QDoubleSpinBox(self)
        self.sharpness_spinbox.setRange(-1.0, 1.0)
        self.sharpness_spinbox.setSingleStep(0.01)
        self.sharpness_spinbox.setValue(0.0)

        hue_label = QLabel('色相:', self)
        self.hue_spinbox = QDoubleSpinBox(self)
        self.hue_spinbox.setRange(-1.0, 1.0)
        self.hue_spinbox.setSingleStep(0.01)
        self.hue_spinbox.setValue(0.0)

        # 新增取色器按钮
        self.color_picker_button = QPushButton('取色器', self)
        self.color_picker_button.setCheckable(True)
        self.color_picker_button.clicked.connect(self.toggle_color_picker)

        # 新增本地导入图片按钮
        self.import_button = QPushButton('导入图片', self)
        self.import_button.clicked.connect(self.import_image)

        # 新增同步缩放按钮
        self.sync_zoom_button = QPushButton('同步缩放', self)
        self.sync_zoom_button.setCheckable(True)
        self.sync_zoom_button.setChecked(True)
        self.sync_zoom_button.clicked.connect(self.toggle_sync_zoom)

        compare_button = QPushButton('按下对比')
        reset_button = QPushButton('重置')
        save_as_button = QPushButton('另存为')

        # 将控件添加到控制布局
        control_layout.addWidget(red_label)
        control_layout.addWidget(self.red_spinbox)
        control_layout.addWidget(green_label)
        control_layout.addWidget(self.green_spinbox)
        control_layout.addWidget(blue_label)
        control_layout.addWidget(self.blue_spinbox)
        control_layout.addWidget(saturation_label)
        control_layout.addWidget(self.saturation_spinbox)
        control_layout.addWidget(exposure_label)
        control_layout.addWidget(self.exposure_spinbox)
        control_layout.addWidget(contrast_label)
        control_layout.addWidget(self.contrast_spinbox)
        control_layout.addWidget(sharpness_label)
        control_layout.addWidget(self.sharpness_spinbox)
        control_layout.addWidget(hue_label)
        control_layout.addWidget(self.hue_spinbox)
        # 将按钮添加到控制布局
        control_layout.addWidget(self.color_picker_button)  # 添加取色器按钮
        control_layout.addWidget(self.import_button)  # 添加导入图片按钮
        control_layout.addWidget(self.sync_zoom_button)  # 添加同步缩放按钮
        control_layout.addWidget(compare_button)
        control_layout.addWidget(reset_button)
        control_layout.addWidget(save_as_button)
        
        # 连接旋转框的值改变信号到on_slider_change方法
        self.saturation_spinbox.valueChanged.connect(self.on_slider_change)
        self.exposure_spinbox.valueChanged.connect(self.on_slider_change)
        self.contrast_spinbox.valueChanged.connect(self.on_slider_change)
        self.red_spinbox.valueChanged.connect(self.on_slider_change)
        self.green_spinbox.valueChanged.connect(self.on_slider_change)
        self.blue_spinbox.valueChanged.connect(self.on_slider_change)
        self.sharpness_spinbox.valueChanged.connect(self.on_slider_change)
        self.hue_spinbox.valueChanged.connect(self.on_slider_change)
        
        # 设置主布局
        main_layout.addLayout(label_layout)
        main_layout.addLayout(image_layout)
        main_layout.addLayout(control_layout)
        
        # 连接按钮功能
        compare_button.pressed.connect(self.compare_images)
        compare_button.released.connect(self.restore_modified_image)
        reset_button.clicked.connect(self.reset_parameters)
        save_as_button.clicked.connect(self.save_as)

        # 设置主布局
        self.setLayout(main_layout)

        # 显示窗口
        self.show()

        # 初始加载时自适应窗口大小
        self.reset_zoom()


    def reset_zoom(self):
        """重置两个视图的缩放比例，使其适应窗口大小"""
        if not self.scene_before.items() or not self.scene_after.items():
            return
            
        # 计算适应窗口的缩放比例
        rect_before = self.scene_before.itemsBoundingRect()
        rect_after = self.scene_after.itemsBoundingRect()
        
        # 计算两个视图的适应比例
        scale_before = min(
            self.view_before.width() / rect_before.width(),
            self.view_before.height() / rect_before.height()
        ) * 0.95  # 稍微缩小一点，避免边缘被裁剪
        
        scale_after = min(
            self.view_after.width() / rect_after.width(),
            self.view_after.height() / rect_after.height()
        ) * 0.95  # 稍微缩小一点，避免边缘被裁剪
        
        # 使用相同的缩放比例，确保两个视图同步
        scale_factor = min(scale_before, scale_after)
        
        # 重置变换并应用新的缩放
        self.view_before.resetTransform()
        self.view_after.resetTransform()
        self.view_before.scale(scale_factor, scale_factor)
        self.view_after.scale(scale_factor, scale_factor)
        
        # 更新缩放因子
        self.view_before.zoom_factor = scale_factor
        self.view_after.zoom_factor = scale_factor
        self.last_zoom_factor = scale_factor


    def on_zoom_changed(self, factor, is_before):
        """处理缩放变化事件"""
        # 如果启用了同步缩放且不是Alt键单独缩放模式
        if self.sync_zoom and not (QApplication.keyboardModifiers() & Qt.AltModifier):
            # 更新另一个视图的缩放
            if is_before:
                self.view_after.setTransform(self.view_before.transform())
                self.view_after.zoom_factor = factor
            else:
                self.view_before.setTransform(self.view_after.transform())
                self.view_before.zoom_factor = factor
        
        # 保存当前缩放因子
        self.last_zoom_factor = factor


    def toggle_sync_zoom(self, checked):
        """切换同步缩放模式"""
        self.sync_zoom = checked
        if checked:
            # 如果启用同步，强制两个视图使用相同的缩放
            self.view_after.setTransform(self.view_before.transform())
            self.view_after.zoom_factor = self.view_before.zoom_factor

    def import_image(self):
        """导入本地图片"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
            options=options
        )
        if file_path:
            new_pixmap = ImageTransform.auto_rotate_image(file_path)
            if new_pixmap.isNull():
                print(f"[sub_image_process_view]--[import_image]-->无法加载图片: {file_path}")
                return
            self.original_pixmap = new_pixmap
            self.update_images()
            self.reset_zoom()  # 重置缩放比例

    def toggle_color_picker(self, checked):
        """切换取色器模式"""

        self.view_after.set_pick_mode(checked)
        if checked:
            # 设置按钮高亮
            self.color_picker_button.setStyleSheet("background-color: yellow;")
        else:
            # 取消按钮高亮
            self.color_picker_button.setStyleSheet("")
            self.selected_color = None  # 取消选色时清除选中的颜色
            self.update_images()

    def pick_color(self, color: QColor):
        """处理取色器选中的颜色"""

        self.selected_color = color
        self.color_picker_button.setChecked(False)  # 取消按钮的选中状态
        self.update_images()

    def update_images(self):
        if self.original_pixmap.isNull():
            print(f"[sub_image_process_view]--[update_images]-->没有加载图片，无法更新图像。")
            self.scene_before.clear()
            self.scene_after.clear()
            return
        # 将原始图片添加到左侧视图
        self.scene_before.clear()
        self.scene_before.addPixmap(self.original_pixmap)
        # 自适应左侧视图
        self.view_before.fitInView(self.scene_before.sceneRect(), Qt.KeepAspectRatio)

        # 在这里对图片进行修改，然后更新右侧视图
        modified_pixmap = self.modify_image(self.original_pixmap)
        self.scene_after.clear()
        self.scene_after.addPixmap(modified_pixmap)
        # 自适应右侧视图
        self.view_after.fitInView(self.scene_after.sceneRect(), Qt.KeepAspectRatio)


    def modify_image(self, pixmap):
        if pixmap.isNull():
            return QPixmap()

        # 将 QPixmap 转换为 OpenCV 图像
        image = self.qpixmap_to_cv(pixmap)
        if image is None:
            print(f"[sub_image_process_view]--[modify_image]-->转换 QPixmap 到 OpenCV 图像失败。")
            return QPixmap()

        # 获取旋转框的值
        saturation_increment = self.saturation_spinbox.value()
        exposure_increment = self.exposure_spinbox.value()
        contrast_increment = self.contrast_spinbox.value()
        red_increment = self.red_spinbox.value()
        green_increment = self.green_spinbox.value()
        blue_increment = self.blue_spinbox.value()
        sharpness_increment = self.sharpness_spinbox.value()
        hue_increment = self.hue_spinbox.value()


        # 如果选择了颜色，获取其 HSV 值
        if self.selected_color:
            selected_hue = self.selected_color.hue() % 180  # OpenCV HSV hue范围为0-179
            selected_sat = self.selected_color.saturation()
            selected_val = self.selected_color.value()
            # 定义颜色匹配的容差
            hue_tolerance = 10  # 色相容差
            sat_tolerance = 50  # 饱和度容差
            val_tolerance = 50  # 明度容差
            # 转换为 HSV
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            # 创建掩码
            lower_bound = np.array([
                max(selected_hue - hue_tolerance, 0),
                max(selected_sat - sat_tolerance, 0),
                max(selected_val - val_tolerance, 0)
            ])
            upper_bound = np.array([
                min(selected_hue + hue_tolerance, 179),
                min(selected_sat + sat_tolerance, 255),
                min(selected_val + val_tolerance, 255)
            ])
            mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
            non_zero = cv2.countNonZero(mask)
        else:
            mask = None  # 如果未选择颜色，则对整个图像应用

        # 调整饱和度
        if saturation_increment != 0:
            if mask is not None:
                hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv_image[..., 1][mask != 0] *= (1 + saturation_increment)
                hsv_image[..., 1] = np.clip(hsv_image[..., 1], 0, 255)
                image = cv2.cvtColor(hsv_image.astype(np.uint8), cv2.COLOR_HSV2BGR)
            else:
                hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv_image[..., 1] *= (1 + saturation_increment)
                hsv_image[..., 1] = np.clip(hsv_image[..., 1], 0, 255)
                image = cv2.cvtColor(hsv_image.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 调整曝光
        if exposure_increment != 0:
            image = cv2.convertScaleAbs(image, alpha=1.0, beta=exposure_increment * 255)

        # 使用 PIL 调整对比度
        if contrast_increment != 0:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            enhancer = ImageEnhance.Contrast(pil_image)
            factor = 1.0 + contrast_increment  # 对比度因子
            pil_image = enhancer.enhance(factor)
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # 调整颜色通道
        if red_increment != 0 or green_increment != 0 or blue_increment != 0:
            b, g, r = cv2.split(image)
            if blue_increment != 0:
                b = cv2.add(b, blue_increment)
            if green_increment != 0:
                g = cv2.add(g, green_increment)
            if red_increment != 0:
                r = cv2.add(r, red_increment)
            image = cv2.merge([b, g, r])

        # 使用 PIL 调整锐度
        if sharpness_increment != 0:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            enhancer = ImageEnhance.Sharpness(pil_image)
            factor = 2.0 + sharpness_increment
            pil_image = enhancer.enhance(factor)
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # 调整色相
        if hue_increment != 0:
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            hue_shift = hue_increment * 180  # OpenCV中hue范围为0-179
            if mask is not None:
                hsv_image[..., 0][mask != 0] = (hsv_image[..., 0][mask != 0] + hue_shift) % 180
            else:
                hsv_image[..., 0] = (hsv_image[..., 0] + hue_shift) % 180
            image = cv2.cvtColor(hsv_image.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 将 OpenCV 图像转换回 QPixmap
        return self.cv_to_qpixmap(image)

    def qpixmap_to_cv(self, pixmap):
        if pixmap.isNull():
            print(f"[sub_image_process_view]--[qpixmap_to_cv]-->尝试转换一个空的 QPixmap。")
            return None
        # 将 QPixmap 转换为 OpenCV 图像
        image = pixmap.toImage()
        image = image.convertToFormat(QImage.Format.Format_RGB888)
        width, height = image.width(), image.height()
        bytes_per_line = image.bytesPerLine()
        ptr = image.bits()
        try:
            ptr.setsize(bytes_per_line * height)
        except AttributeError:
            print(f"[sub_image_process_view]--[qpixmap_to_cv]-->无法设置指针大小，可能是 QPixmap 无效。")
            return None
        # 将数据重塑为 (height, bytes_per_line)
        arr = np.array(ptr).reshape(height, bytes_per_line)
        # 去除每行的填充字节，只保留实际图像数据
        arr = arr[:, :width * 3]
        # 将数据重塑为 (height, width, 3)
        try:
            arr = arr.reshape(height, width, 3)
        except ValueError as e:
            print(f"[sub_image_process_view]--[qpixmap_to_cv]-->重塑数组失败: {e}")
            return None
        # 转换为 BGR 格式以适应 OpenCV
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def cv_to_qpixmap(self, cv_img):
        # 将 OpenCV 的 BGR 图像转换为 RGB
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        # 获取图像的高度、宽度和通道数
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        # 创建 QImage 对象
        q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        # 转换为 QPixmap 并返回
        return QPixmap.fromImage(q_img)

    # 在滑块值改变时调用update_images方法
    def on_slider_change(self):
        self.update_images()

    def resizeEvent(self, event):
        # 调整视图以适应窗口大小
        self.view_before.fitInView(self.scene_before.sceneRect(), Qt.KeepAspectRatio)
        self.view_after.fitInView(self.scene_after.sceneRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)

    # 按钮功能实现示例
    def compare_images(self):
        if self.original_pixmap.isNull():
            print(f"[sub_image_process_view]--[compare_images]-->没有加载图片，无法进行对比。")
            return
        # 将原始图片覆盖到右侧视图
        self.scene_after.clear()
        self.scene_after.addPixmap(self.original_pixmap)
        self.view_after.fitInView(self.scene_after.sceneRect(), Qt.KeepAspectRatio)

    def reset_parameters(self):
        # 重置所有参数到初始值
        self.red_spinbox.setValue(0.0)
        self.green_spinbox.setValue(0.0)
        self.blue_spinbox.setValue(0.0)
        self.saturation_spinbox.setValue(0.0)
        self.exposure_spinbox.setValue(0.0)
        self.contrast_spinbox.setValue(0.0)
        self.sharpness_spinbox.setValue(0.0)
        self.hue_spinbox.setValue(0.0)
        self.selected_color = None  # 重置选中的颜色
        self.update_images()

    def save_as(self):
        if self.original_pixmap.isNull():
            print(f"[sub_image_process_view]--[save_as]-->没有加载图片，无法保存。")
            return
        # 弹出文件保存对话框
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "另存为", 
            "", 
            "Images (*.jpg *.png *.bmp *.gif)", 
            options=options
        )
        if file_path:
            # 将修改后的图片保存到用户选择的路径
            print(f"[sub_image_process_view]--[save_as]-->保存修改后的图片到: {file_path}")
            modified_pixmap = self.modify_image(self.original_pixmap)
            if not modified_pixmap.isNull():
                modified_pixmap.save(file_path)
            else:
                print(f"[sub_image_process_view]--[save_as]-->修改后的图片为空，无法保存。")

    def restore_modified_image(self):
        # 恢复修改后的图片
        self.update_images()

    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        if event.key() == Qt.Key_Escape:
            self.close()  
            event.accept()

    def closeEvent(self, event):
        """重写关闭事件"""
        # 发射关闭信号（新增），统一在这里发送信号
        self.closed.emit()
        
        # 接受关闭事件（重要！这会告诉Qt正常关闭窗口）
        event.accept()

class GraphicsView(QGraphicsView):
    zoomChanged = pyqtSignal(float)  # 缩放变化信号，通知外部
    def __init__(self, parent=None, pick_color_callback=None):
        super().__init__(parent)
        self.pick_color_callback = pick_color_callback
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # 设置缩放锚点为鼠标位置
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.zoom_factor = 1.0  # 初始缩放因子
        self.pick_mode = False

    def wheelEvent(self, event):
        """重写鼠标滚轮事件以实现缩放功能"""
        # 获取 Alt 键状态
        alt_pressed = event.modifiers() & Qt.AltModifier
        
        # 计算缩放因子
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        
        # 保存当前鼠标在场景中的位置
        old_pos = self.mapToScene(event.pos())
        
        # 进行缩放
        self.scale(zoom_factor, zoom_factor)
        
        # 更新缩放因子并发送信号
        self.zoom_factor *= zoom_factor
        self.zoomChanged.emit(self.zoom_factor)
        
        # 如果按住 Alt 键，确保鼠标位置保持不变
        if alt_pressed:
            new_pos = self.mapToScene(event.pos())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())

    def set_pick_mode(self, mode: bool):
        """设置是否处于取色模式"""
        self.pick_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if self.pick_mode and event.button() == Qt.LeftButton:
            # 获取点击位置
            scene_pos = self.mapToScene(event.pos())
            x = int(scene_pos.x())
            y = int(scene_pos.y())
            # 转换为 OpenCV 坐标
            img = self.parent.qpixmap_to_cv(self.parent.original_pixmap)
            if img is None:
                print(f"[sub_image_process_view]--[mousePressEvent]-->无法获取图片数据进行取色。")
                return
            height, width, _ = img.shape
            if 0 <= x < width and 0 <= y < height:
                b, g, r = img[y, x]
                color = QColor(r, g, b)
                if self.pick_color_callback:
                    self.pick_color_callback(color)
        else:
            super().mousePressEvent(event)

			
if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    ex = SubCompare(image_path)
    sys.exit(app.exec_())