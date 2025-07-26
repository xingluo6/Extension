import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QFileDialog,
    QTabWidget, QGroupBox, QMessageBox, QCheckBox, QProgressBar,
    QRadioButton, QButtonGroup
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from SpineAtlas import ReadAtlasFile, AtlasFrame, AtlasTex, Atlas, Anchor
from SpineAtlas import ImgPremultiplied, ImgNonPremultiplied
from PIL.Image import open as imgop

class SpineAtlasGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpineAtlas Tool")
        self.setGeometry(100, 100, 900, 700)
        
        # 主控件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 创建标签页
        self.create_basic_tab()
        self.create_convert_tab()
        self.create_anchor_tab()
        self.create_image_tab()
        
        # 状态变量
        self.current_atlas = None
        self.selected_files = []
        self.atlas_files = []
        
        # 批处理进度条
        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.setVisible(False)
    
    def create_basic_tab(self):
        """基本操作标签页 - 增强批处理功能"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 文件路径组 - 增强支持目录选择
        file_group = QGroupBox("Atlas 文件/目录")
        file_layout = QVBoxLayout()
        
        self.atlas_path_label = QLabel("未选择文件或目录")
        self.atlas_path_label.setWordWrap(True)
        
        browse_button = QPushButton("选择文件...")
        browse_button.clicked.connect(lambda: self.browse_atlas(False))
        
        browse_dir_button = QPushButton("选择目录...")
        browse_dir_button.clicked.connect(lambda: self.browse_atlas(True))
        
        # 递归子目录选项
        self.recursive_checkbox = QCheckBox("包含子目录")
        self.recursive_checkbox.setChecked(True)
        
        # 文件列表预览
        self.file_list_info = QLabel("0 个文件待处理")
        
        file_layout.addWidget(self.atlas_path_label)
        file_layout.addWidget(browse_button)
        file_layout.addWidget(browse_dir_button)
        file_layout.addWidget(self.recursive_checkbox)
        file_layout.addWidget(self.file_list_info)
        file_group.setLayout(file_layout)
        
        # 批处理选项组
        batch_options = QGroupBox("批处理选项")
        batch_layout = QVBoxLayout()
        
        # 文件保存选项
        save_options_layout = QHBoxLayout()
        self.save_option_group = QButtonGroup(self)
        
        self.overwrite_radio = QRadioButton("覆盖原文件")
        self.suffix_radio = QRadioButton("添加后缀")
        self.suffix_radio.setChecked(True)
        
        self.save_option_group.addButton(self.overwrite_radio)
        self.save_option_group.addButton(self.suffix_radio)
        
        self.suffix_input = QLineEdit("_modified")
        self.suffix_input.setEnabled(True)
        
        save_options_layout.addWidget(self.overwrite_radio)
        save_options_layout.addWidget(self.suffix_radio)
        save_options_layout.addWidget(self.suffix_input)
        
        batch_layout.addLayout(save_options_layout)
        batch_options.setLayout(batch_layout)
        
        # 连接覆盖选项变化
        self.overwrite_radio.toggled.connect(
            lambda: self.suffix_input.setEnabled(not self.overwrite_radio.isChecked())
        )
        
        # 操作组
        operation_group = QGroupBox("基本操作")
        operation_layout = QVBoxLayout()
        
        # 格式转换
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Atlas 4.0", "Atlas 3.0"])
        convert_button = QPushButton("转换格式")
        convert_button.clicked.connect(self.convert_format)
        
        format_layout.addWidget(QLabel("目标格式:"))
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(convert_button)
        
        # 检查纹理
        check_button = QPushButton("检查缺失纹理")
        check_button.clicked.connect(self.check_textures)
        
        # 缩放
        scale_button = QPushButton("应用纹理缩放")
        scale_button.clicked.connect(self.apply_scaling)
        
        # 导出帧
        export_layout = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Normal", "Premul", "NonPremul"])
        export_button = QPushButton("导出帧")
        export_button.clicked.connect(self.export_frames)
        
        export_layout.addWidget(QLabel("导出模式:"))
        export_layout.addWidget(self.mode_combo)
        export_layout.addWidget(export_button)
        
        operation_layout.addLayout(format_layout)
        operation_layout.addWidget(check_button)
        operation_layout.addWidget(scale_button)
        operation_layout.addLayout(export_layout)
        operation_group.setLayout(operation_layout)
        
        # 日志
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        
        layout.addWidget(file_group)
        layout.addWidget(batch_options)
        layout.addWidget(operation_group)
        layout.addWidget(QLabel("操作日志:"))
        layout.addWidget(self.log_area)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "基本操作")
    
    def create_convert_tab(self):
        """转换标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # JSON路径组
        json_group = QGroupBox("JSON 源文件")
        json_layout = QVBoxLayout()
        
        self.json_path_label = QLabel("未选择文件")
        json_browse_button = QPushButton("浏览...")
        json_browse_button.clicked.connect(self.browse_json)
        
        json_layout.addWidget(self.json_path_label)
        json_layout.addWidget(json_browse_button)
        json_group.setLayout(json_layout)
        
        # 转换组
        convert_group = QGroupBox("转换选项")
        convert_layout = QVBoxLayout()
        
        self.output_name = QLineEdit("output.atlas")
        convert_button = QPushButton("转换为Spine Atlas")
        convert_button.clicked.connect(self.convert_to_atlas)
        
        convert_layout.addWidget(QLabel("输出文件名:"))
        convert_layout.addWidget(self.output_name)
        convert_layout.addWidget(convert_button)
        convert_group.setLayout(convert_layout)
        
        layout.addWidget(json_group)
        layout.addWidget(convert_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "格式转换")
    
    def create_anchor_tab(self):
        """锚点标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 裁剪锚点组
        cut_group = QGroupBox("裁剪锚点")
        cut_layout = QVBoxLayout()
        
        self.cut_combo = QComboBox()
        for anchor in Anchor:
            self.cut_combo.addItem(anchor.name.replace("_", " "), anchor.value)
        
        cut_button = QPushButton("重新计算裁剪锚点")
        cut_button.clicked.connect(self.recalculate_cut_anchor)
        
        cut_layout.addWidget(QLabel("选择锚点:"))
        cut_layout.addWidget(self.cut_combo)
        cut_layout.addWidget(cut_button)
        cut_group.setLayout(cut_layout)
        
        # 偏移锚点组
        offset_group = QGroupBox("偏移锚点")
        offset_layout = QVBoxLayout()
        
        self.offset_combo = QComboBox()
        for anchor in Anchor:
            self.offset_combo.addItem(anchor.name.replace("_", " "), anchor.value)
        
        offset_button = QPushButton("重新计算偏移锚点")
        offset_button.clicked.connect(self.recalculate_offset_anchor)
        
        offset_layout.addWidget(QLabel("选择锚点:"))
        offset_layout.addWidget(self.offset_combo)
        offset_layout.addWidget(offset_button)
        offset_group.setLayout(offset_layout)
        
        layout.addWidget(cut_group)
        layout.addWidget(offset_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "锚点操作")
    
    def create_image_tab(self):
        """图像处理标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 图像路径组
        image_group = QGroupBox("图像文件")
        image_layout = QVBoxLayout()
        
        self.image_path_label = QLabel("未选择文件")
        image_browse_button = QPushButton("浏览...")
        image_browse_button.clicked.connect(self.browse_image)
        
        image_layout.addWidget(self.image_path_label)
        image_layout.addWidget(image_browse_button)
        image_group.setLayout(image_layout)
        
        # 处理组
        process_group = QGroupBox("图像处理")
        process_layout = QVBoxLayout()
        
        self.process_combo = QComboBox()
        self.process_combo.addItems(["转换为预乘", "转换为非预乘"])
        
        process_button = QPushButton("应用处理")
        process_button.clicked.connect(self.process_image)
        
        # 修复这里的语法错误
        process_layout.addWidget(QLabel("处理类型:"))
        process_layout.addWidget(self.process_combo)
        process_layout.addWidget(process_button)
        process_group.setLayout(process_layout)
        
        layout.addWidget(image_group)
        layout.addWidget(process_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "图像处理")
    
    def browse_atlas(self, is_directory=False):
        """浏览并选择 Atlas 文件或目录"""
        if is_directory:
            path = QFileDialog.getExistingDirectory(
                self, "选择 Atlas 目录", ""
            )
            if path:
                self.atlas_path_label.setText(f"目录: {path}")
                self.collect_files(path)
        else:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "选择 Atlas 文件", "", "Atlas Files (*.atlas)"
            )
            if paths:
                self.selected_files = paths
                self.atlas_path_label.setText(f"文件: {', '.join([Path(p).name for p in paths])}")
                self.file_list_info.setText(f"{len(paths)} 个文件待处理")
    
    def collect_files(self, directory_path):
        """收集目录中的所有 Atlas 文件"""
        recursive = self.recursive_checkbox.isChecked()
        self.selected_files = []
        
        try:
            path_obj = Path(directory_path)
            pattern = "*.atlas"
            
            if recursive:
                for file in path_obj.rglob(pattern):
                    if file.is_file():
                        self.selected_files.append(str(file))
            else:
                for file in path_obj.glob(pattern):
                    if file.is_file():
                        self.selected_files.append(str(file))
            
            self.file_list_info.setText(f"找到 {len(self.selected_files)} 个 Atlas 文件")
            self.log(f"在目录中收集到 {len(self.selected_files)} 个 Atlas 文件")
        except Exception as e:
            self.log(f"收集文件失败: {str(e)}", error=True)
    
    def browse_json(self):
        """浏览并选择 JSON 文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 JSON 文件", "", "JSON Files (*.json)"
        )
        if path:
            self.json_path_label.setText(Path(path).name)
    
    def browse_image(self):
        """浏览并选择图像文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", "Image Files (*.png *.jpg)"
        )
        if path:
            self.image_path_label.setText(Path(path).name)
    
    def log(self, message, error=False):
        """记录日志"""
        prefix = "[ERROR] " if error else "[INFO] "
        self.log_area.append(prefix + message)
    
    def start_batch_operation(self):
        """开始批处理操作"""
        if not self.selected_files:
            self.log("没有选择任何文件或目录", error=True)
            return False
        
        self.progress_bar.setRange(0, len(self.selected_files))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        return True
    
    def update_progress(self, index):
        """更新进度条"""
        self.progress_bar.setValue(index + 1)
        QApplication.processEvents()  # 确保UI更新
    
    def end_batch_operation(self):
        """结束批处理操作"""
        self.progress_bar.setVisible(False)
    
    def process_batch_file(self, file_path, operation_callback):
        """处理单个文件 - 支持覆盖和添加后缀选项"""
        try:
            # 创建临时文件路径避免覆盖问题
            temp_file = f"{file_path}.tmp"
            
            # 处理文件
            atlas = ReadAtlasFile(file_path)
            operation_callback(atlas)
            
            # 保存到临时文件
            atlas.SaveAtlas(temp_file)
            
            # 确定最终保存路径
            if self.overwrite_radio.isChecked():
                # 安全覆盖原文件
                os.replace(temp_file, file_path)
                self.log(f"成功覆盖: {Path(file_path).name}")
            else:
                # 添加后缀保存
                suffix = self.suffix_input.text().strip()
                save_path = f"{Path(file_path).stem}{suffix}.atlas"
                os.replace(temp_file, save_path)
                self.log(f"保存为: {Path(save_path).name}")
            
            return True
        except Exception as e:
            # 删除临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
            self.log(f"处理失败 {Path(file_path).name}: {str(e)}", error=True)
            return False
    
    def convert_format(self):
        """转换 Atlas 格式 - 支持批处理"""
        if not self.start_batch_operation():
            return
        
        target_format = True if "4.0" in self.format_combo.currentText() else False
        success_count = 0
        
        # 定义格式转换操作
        def convert_op(atlas):
            atlas.version = target_format
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            if self.process_batch_file(file_path, convert_op):
                success_count += 1
        
        self.end_batch_operation()
        self.log(f"格式转换完成! 成功: {success_count}/{len(self.selected_files)}")
    
    def check_textures(self):
        """检查缺失纹理 - 支持批处理"""
        if not self.start_batch_operation():
            return
        
        total_missing = 0
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            try:
                atlas = ReadAtlasFile(file_path)
                miss = atlas.CheckTextures()
                
                if miss:
                    total_missing += len(miss)
                    self.log(f"{Path(file_path).name} 缺失 {len(miss)} 个纹理:")
                    for texture in miss:
                        self.log(f" - {texture}")
                else:
                    self.log(f"{Path(file_path).name} 没有缺失纹理")
            except Exception as e:
                self.log(f"检查 {Path(file_path).name} 失败: {str(e)}", error=True)
        
        self.end_batch_operation()
        self.log(f"纹理检查完成! 共在 {len(self.selected_files)} 个文件中发现 {total_missing} 个缺失纹理")
    
    def apply_scaling(self):
        """应用纹理缩放 - 支持批处理"""
        if not self.start_batch_operation():
            return
        
        success_count = 0
        
        # 定义缩放操作
        def scale_op(atlas):
            atlas.ReScale()
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            if self.process_batch_file(file_path, scale_op):
                success_count += 1
        
        self.end_batch_operation()
        self.log(f"纹理缩放完成! 成功: {success_count}/{len(self.selected_files)}")
    
    def export_frames(self):
        """导出帧 - 支持批处理"""
        if not self.selected_files:
            self.log("没有选择任何文件或目录", error=True)
            return
        
        # 获取导出模式
        mode = self.mode_combo.currentText()
        
        # 选择导出目录
        export_dir = QFileDialog.getExistingDirectory(
            self, "选择导出目录"
        )
        if not export_dir:
            return
        
        self.progress_bar.setRange(0, len(self.selected_files))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        success_count = 0
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            try:
                atlas = ReadAtlasFile(file_path)
                atlas.SaveFrames(path=export_dir, mode=mode)
                success_count += 1
                self.log(f"成功导出 {Path(file_path).name} 的帧")
            except Exception as e:
                self.log(f"导出 {Path(file_path).name} 失败: {str(e)}", error=True)
        
        self.progress_bar.setVisible(False)
        self.log(f"帧导出完成! 成功: {success_count}/{len(self.selected_files)}")
    
    def convert_to_atlas(self):
        """转换 JSON 到 Spine Atlas"""
        json_path = Path(self.json_path_label.text()).absolute()
        if not json_path.is_file():
            self.log("请选择有效的 JSON 文件", error=True)
            return
        
        try:
            # 加载 JSON 数据
            with open(json_path, 'r', encoding='utf-8') as f:
                texture_dict = json.load(f)
            
            # 创建帧列表
            frames = []
            for frame_info in texture_dict['Frame']:
                frame = AtlasFrame(
                    frame_info['Frame_Name'],
                    frame_info['Cut_X'],
                    frame_info['Cut_Y'],
                    frame_info['Cut_Width'],
                    frame_info['Cut_Height'],
                    frame_info['Original_X'],
                    frame_info['Original_Y'],
                    frame_info['Original_Width'],
                    frame_info['Original_Height'],
                    frame_info['Rotate']
                )
                frames.append(frame)
            
            # 创建纹理
            tex = texture_dict['Texture']
            texture = AtlasTex(
                tex['Texture_Name'],
                tex['Texture_Width'],
                tex['Texture_Height'],
                frames=frames
            )
            
            # 创建 Atlas
            atlas = Atlas([texture])
            
            # 保存 Atlas
            output_file = self.output_name.text()
            atlas.SaveAtlas(output_file)
            self.log(f"成功转换 JSON 并保存到: {output_file}")
            
        except Exception as e:
            self.log(f"转换 JSON 失败: {str(e)}", error=True)
    
    def recalculate_cut_anchor(self):
        """重新计算裁剪锚点"""
        if not self.selected_files:
            self.log("请先选择文件或目录", error=True)
            return
        
        # 获取选择的锚点
        anchor_value = self.cut_combo.currentData()
        
        if not self.start_batch_operation():
            return
        
        success_count = 0
        
        # 定义锚点操作
        def anchor_op(atlas):
            atlas.cutp = Anchor(anchor_value)
            atlas.ReOffset()
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            if self.process_batch_file(file_path, anchor_op):
                success_count += 1
        
        self.end_batch_operation()
        self.log(f"裁剪锚点重新计算完成! 成功: {success_count}/{len(self.selected_files)}")
    
    def recalculate_offset_anchor(self):
        """重新计算偏移锚点"""
        if not self.selected_files:
            self.log("请先选择文件或目录", error=True)
            return
        
        # 获取选择的锚点
        anchor_value = self.offset_combo.currentData()
        
        if not self.start_batch_operation():
            return
        
        success_count = 0
        
        # 定义锚点操作
        def anchor_op(atlas):
            atlas.offp = Anchor(anchor_value)
            atlas.ReOffset()
        
        for i, file_path in enumerate(self.selected_files):
            self.update_progress(i)
            if self.process_batch_file(file_path, anchor_op):
                success_count += 1
        
        self.end_batch_operation()
        self.log(f"偏移锚点重新计算完成! 成功: {success_count}/{len(self.selected_files)}")
    
    def process_image(self):
        """处理图像"""
        image_path = Path(self.image_path_label.text()).absolute()
        if not image_path.is_file():
            self.log("请选择有效的图像文件", error=True)
            return
        
        try:
            # 加载图像
            img = imgop(image_path)
            
            # 确定处理类型
            process_type = self.process_combo.currentText()
            if "预乘" in process_type:
                processed_img = ImgPremultiplied(img)
            else:
                processed_img = ImgNonPremultiplied(img)
            
            # 保存处理后的图像
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存处理后的图像", "", "PNG Images (*.png)"
            )
            if save_path:
                processed_img.save(save_path)
                self.log(f"成功处理图像并保存到: {save_path}")
                
        except Exception as e:
            self.log(f"图像处理失败: {str(e)}", error=True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpineAtlasGUI()
    window.show()
    sys.exit(app.exec())