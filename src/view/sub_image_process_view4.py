from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsView, QGraphicsScene, QDoubleSpinBox, QPushButton, QFileDialog
from PyQt5.QtGui import QPixmap, QColor

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


    # 其他方法保持不变...
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

    # 其他方法保持不变...