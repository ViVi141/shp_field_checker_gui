#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
几何编辑弹窗
增强版 - 包含几何修复、拓扑检查、可视化编辑等功能
支持直接在GUI中编辑几何数据并保存回原文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging
import warnings
import numpy as np
from datetime import datetime
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import matplotlib.patches as patches
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, shape
from shapely.validation import make_valid
from shapely.ops import unary_union
import shapely.affinity
import shapely.ops
from shapely import wkt
import math
import fiona


logger = logging.getLogger(__name__)

class GeometryEditorDialog:
    """几何编辑弹窗"""
    
    def __init__(self, parent, file_path, layer_name=None):
        """
        初始化几何编辑弹窗
        
        Args:
            parent: 父窗口
            file_path: 文件路径
            layer_name: 图层名称（GDB文件）
        """
        self.parent = parent
        self.file_path = Path(file_path)
        self.layer_name = layer_name
        self.original_gdf = None
        self.modified_gdf = None
        self.selected_features = set()
        self.geometry_issues = []
        
        # 几何修复选项
        self.auto_fix_options = {
            'fix_invalid_geometries': True,
            'fix_self_intersections': True,
            'fix_gaps': True,
            'fix_overlaps': True,
            'snap_vertices': True,
            'tolerance': 0.001
        }
        
        # 创建弹窗
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"几何编辑: {self.file_path.name}")
        self.dialog.geometry("1600x1000")  # 增大窗口尺寸
        self.dialog.minsize(1400, 900)     # 增大最小窗口尺寸
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 设置弹窗位置为屏幕中心
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (1000 // 2)
        self.dialog.geometry(f"1600x1000+{x}+{y}")
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """设置界面"""
        # 主布局
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧面板 - 工具和统计
        left_panel = ttk.Frame(main_frame, width=400)  # 增加左侧面板宽度
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # 几何信息面板
        geometry_info_frame = ttk.LabelFrame(left_panel, text="几何信息")
        geometry_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.geometry_info_text = tk.Text(geometry_info_frame, height=10, width=45)  # 增加高度和宽度
        self.geometry_info_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 几何问题面板
        issues_frame = ttk.LabelFrame(left_panel, text="几何问题")
        issues_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.issues_text = tk.Text(issues_frame, height=8, width=45)  # 增加高度和宽度
        self.issues_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 修复选项面板
        fix_options_frame = ttk.LabelFrame(left_panel, text="修复选项")
        fix_options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 修复选项复选框
        self.fix_invalid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fix_options_frame, text="修复无效几何", 
                       variable=self.fix_invalid_var).pack(anchor=tk.W, padx=5)
        
        self.fix_intersections_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fix_options_frame, text="修复自相交", 
                       variable=self.fix_intersections_var).pack(anchor=tk.W, padx=5)
        
        self.fix_gaps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fix_options_frame, text="修复缝隙", 
                       variable=self.fix_gaps_var).pack(anchor=tk.W, padx=5)
        
        self.fix_overlaps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fix_options_frame, text="修复重叠", 
                       variable=self.fix_overlaps_var).pack(anchor=tk.W, padx=5)
        
        self.snap_vertices_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fix_options_frame, text="顶点捕捉", 
                       variable=self.snap_vertices_var).pack(anchor=tk.W, padx=5)
        
        # 容差设置
        tolerance_frame = ttk.Frame(fix_options_frame)
        tolerance_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(tolerance_frame, text="容差:").pack(side=tk.LEFT)
        self.tolerance_var = tk.StringVar(value="0.001")
        ttk.Entry(tolerance_frame, textvariable=self.tolerance_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # 操作按钮面板
        buttons_frame = ttk.LabelFrame(left_panel, text="操作")
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用Grid布局来更好地排列按钮
        button_grid = ttk.Frame(buttons_frame)
        button_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # 第一行按钮
        ttk.Button(button_grid, text="一键修复", command=self.auto_fix_all).grid(row=0, column=0, sticky='ew', padx=2, pady=2)
        ttk.Button(button_grid, text="检测问题", command=self.detect_issues).grid(row=0, column=1, sticky='ew', padx=2, pady=2)
        
        # 第二行按钮
        ttk.Button(button_grid, text="保存修改", command=self.save_changes).grid(row=1, column=0, sticky='ew', padx=2, pady=2)
        ttk.Button(button_grid, text="撤销修改", command=self.revert_changes).grid(row=1, column=1, sticky='ew', padx=2, pady=2)
        
        # 配置列权重
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        
        # 右侧主面板
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 工具栏
        toolbar_frame = ttk.Frame(right_panel)
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar_frame, text="放大", command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="缩小", command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="平移", command=self.pan).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="选择", command=self.select_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="编辑", command=self.edit_mode).pack(side=tk.LEFT, padx=2)
        
        # 几何可视化区域
        viz_frame = ttk.LabelFrame(right_panel, text="几何可视化")
        viz_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 创建matplotlib画布
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 几何列表
        list_frame = ttk.LabelFrame(right_panel, text="几何要素列表")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建几何列表
        self.create_geometry_list(list_frame)
        
        # 绑定事件
        self.geometry_tree.bind('<Double-1>', self.on_geometry_double_click)
        self.geometry_tree.bind('<<TreeviewSelect>>', self.on_geometry_select)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=2)

    def create_geometry_list(self, parent):
        """创建几何要素列表"""
        # 创建表格
        columns = ('序号', '几何类型', '面积/长度', '顶点数', '状态', '问题')
        self.geometry_tree = ttk.Treeview(parent, columns=columns, show='headings', height=12)  # 减少表格高度，为按钮留出空间
        
        # 设置列标题
        for col in columns:
            self.geometry_tree.heading(col, text=col)
        
        # 设置列宽
        self.geometry_tree.column('序号', width=60)
        self.geometry_tree.column('几何类型', width=100)
        self.geometry_tree.column('面积/长度', width=120)
        self.geometry_tree.column('顶点数', width=80)
        self.geometry_tree.column('状态', width=80)
        self.geometry_tree.column('问题', width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.geometry_tree.yview)
        self.geometry_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.geometry_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.geometry_tree.bind('<Double-1>', self.on_geometry_double_click)
        self.geometry_tree.bind('<<TreeviewSelect>>', self.on_geometry_select)

    def load_data(self):
        """加载几何数据"""
        try:
            self.status_var.set("正在加载数据...")
            self.dialog.update()
            
            # 读取文件
            if self.file_path.suffix.lower() == '.gdb':
                if self.layer_name:
                    self.original_gdf = gpd.read_file(self.file_path, layer=self.layer_name)
                else:
                    # 读取第一个图层
                    import fiona  # 修复未定义fiona的问题
                    layers = fiona.listlayers(str(self.file_path))
                    if layers:
                        self.original_gdf = gpd.read_file(self.file_path, layer=layers[0])
                    else:
                        raise ValueError("GDB文件中没有找到图层")
            else:
                # 尝试不同编码
                for encoding in ['gbk', 'utf-8', 'gb2312']:
                    try:
                        self.original_gdf = gpd.read_file(self.file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
            
            if self.original_gdf is None or self.original_gdf.empty:
                raise ValueError("无法读取几何数据")
            
            # 尝试修复几何错误
            self.status_var.set("正在修复几何错误...")
            self.dialog.update()
            
            # 修复无效几何
            fixed_geometries = []
            for idx, row in self.original_gdf.iterrows():
                geom = row.geometry
                if geom is not None:
                    try:
                        # 尝试修复几何
                        if not geom.is_valid:
                            fixed_geom = make_valid(geom)
                            if fixed_geom is not None:
                                geom = fixed_geom
                    except Exception as fix_error:
                        logger.warning(f"修复几何 {idx} 失败: {fix_error}")
                        # 如果修复失败，保持原几何
                
                fixed_geometries.append(geom)
            
            # 创建修复后的GeoDataFrame
            self.original_gdf = self.original_gdf.copy()
            self.original_gdf.geometry = fixed_geometries
            
            # 复制数据用于编辑
            self.modified_gdf = self.original_gdf.copy()
            
            # 更新界面
            self.update_geometry_info()
            self.populate_geometry_list()
            self.detect_issues()
            
            self.status_var.set(f"已加载 {len(self.original_gdf)} 个几何要素")
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            # 尝试更宽松的加载方式
            try:
                self.status_var.set("尝试宽松模式加载...")
                self.dialog.update()
                
                # 使用更宽松的参数读取文件
                if self.file_path.suffix.lower() == '.gdb':
                    if self.layer_name:
                        self.original_gdf = gpd.read_file(self.file_path, layer=self.layer_name, ignore_geometry=True)
                    else:
                        import fiona
                        layers = fiona.listlayers(str(self.file_path))
                        if layers:
                            self.original_gdf = gpd.read_file(self.file_path, layer=layers[0], ignore_geometry=True)
                        else:
                            raise ValueError("GDB文件中没有找到图层")
                else:
                    for encoding in ['gbk', 'utf-8', 'gb2312']:
                        try:
                            self.original_gdf = gpd.read_file(self.file_path, encoding=encoding, ignore_geometry=True)
                            break
                        except UnicodeDecodeError:
                            continue
                
                if self.original_gdf is not None and not self.original_gdf.empty:
                    # 创建空的几何列
                    self.original_gdf['geometry'] = None
                    self.modified_gdf = self.original_gdf.copy()
                    
                    self.update_geometry_info()
                    self.populate_geometry_list()
                    self.detect_issues()
                    
                    self.status_var.set(f"已加载 {len(self.original_gdf)} 个要素（几何已忽略）")
                    messagebox.showwarning("警告", "文件包含几何错误，已忽略几何数据。请使用几何修复功能。")
                else:
                    raise ValueError("无法读取数据")
                    
            except Exception as fallback_error:
                logger.error(f"宽松模式加载也失败: {fallback_error}")
                messagebox.showerror("错误", f"加载数据失败: {str(e)}\n\n尝试宽松模式也失败: {str(fallback_error)}")
                self.status_var.set("加载失败")
            
            # 如果仍然失败，尝试从原始文件重新构建几何
            if self.original_gdf is None or self.original_gdf.empty:
                self.try_reconstruct_geometry()
    
    def try_reconstruct_geometry(self):
        """尝试从原始文件重新构建几何"""
        try:
            self.status_var.set("尝试重新构建几何...")
            self.dialog.update()
            
            # 使用fiona直接读取几何数据
            import fiona
            geometries = []
            
            if self.file_path.suffix.lower() == '.gdb':
                if self.layer_name:
                    with fiona.open(str(self.file_path), layer=self.layer_name) as src:
                        for feature in src:
                            try:
                                geom = shape(feature['geometry'])
                                if geom.is_valid:
                                    geometries.append(geom)
                                else:
                                    # 尝试修复无效几何
                                    fixed_geom = make_valid(geom)
                                    if fixed_geom is not None:
                                        geometries.append(fixed_geom)
                                    else:
                                        geometries.append(None)
                            except Exception:
                                geometries.append(None)
                else:
                    layers = fiona.listlayers(str(self.file_path))
                    if layers:
                        with fiona.open(str(self.file_path), layer=layers[0]) as src:
                            for feature in src:
                                try:
                                    geom = shape(feature['geometry'])
                                    if geom.is_valid:
                                        geometries.append(geom)
                                    else:
                                        fixed_geom = make_valid(geom)
                                        if fixed_geom is not None:
                                            geometries.append(fixed_geom)
                                        else:
                                            geometries.append(None)
                                except Exception:
                                    geometries.append(None)
            else:
                with fiona.open(str(self.file_path)) as src:
                    for feature in src:
                        try:
                            geom = shape(feature['geometry'])
                            if geom.is_valid:
                                geometries.append(geom)
                            else:
                                fixed_geom = make_valid(geom)
                                if fixed_geom is not None:
                                    geometries.append(fixed_geom)
                                else:
                                    geometries.append(None)
                        except Exception:
                            geometries.append(None)
            
            # 创建新的GeoDataFrame
            if geometries:
                # 读取属性数据
                if self.file_path.suffix.lower() == '.gdb':
                    if self.layer_name:
                        df = gpd.read_file(self.file_path, layer=self.layer_name, ignore_geometry=True)
                    else:
                        layers = fiona.listlayers(str(self.file_path))
                        if layers:
                            df = gpd.read_file(self.file_path, layer=layers[0], ignore_geometry=True)
                        else:
                            raise ValueError("无法读取属性数据")
                else:
                    df = gpd.read_file(self.file_path, ignore_geometry=True)
                
                # 确保几何列表长度与数据框一致
                while len(geometries) < len(df):
                    geometries.append(None)
                geometries = geometries[:len(df)]
                
                # 创建GeoDataFrame
                self.original_gdf = gpd.GeoDataFrame(df, geometry=geometries)
                self.modified_gdf = self.original_gdf.copy()
                
                self.update_geometry_info()
                self.populate_geometry_list()
                self.detect_issues()
                
                self.status_var.set(f"已重新构建 {len(self.original_gdf)} 个几何要素")
                messagebox.showinfo("成功", "已重新构建几何数据，部分几何可能已修复")
            else:
                raise ValueError("无法重新构建几何数据")
                
        except Exception as e:
            logger.error(f"重新构建几何失败: {e}")
            messagebox.showerror("错误", f"重新构建几何失败: {str(e)}")
            self.status_var.set("几何重建失败")

    def update_geometry_info(self):
        """更新几何信息显示"""
        if self.original_gdf is None:
            return
        
        info_text = f"文件: {self.file_path.name}\n"
        info_text += f"要素数量: {len(self.original_gdf)}\n"
        
        # 检查是否有几何数据
        if 'geometry' in self.original_gdf.columns and self.original_gdf.geometry.notna().any():
            geom_types = self.original_gdf.geometry.geom_type.unique()
            info_text += f"几何类型: {', '.join(geom_types)}\n"
            
            # 计算总面积/长度
            if 'Polygon' in geom_types:
                total_area = self.original_gdf.geometry.area.sum()
                info_text += f"总面积: {total_area:.2f}\n"
            
            if 'LineString' in geom_types:
                total_length = self.original_gdf.geometry.length.sum()
                info_text += f"总长度: {total_length:.2f}\n"
            
            # 统计顶点数
            total_vertices = sum(len(geom.coords) if hasattr(geom, 'coords') and geom is not None else 0 
                               for geom in self.original_gdf.geometry)
            info_text += f"总顶点数: {total_vertices}\n"
        else:
            info_text += "几何类型: 无几何数据\n"
            info_text += "注意: 文件包含几何错误，几何数据已被忽略\n"
            info_text += "建议: 使用一键修复功能尝试恢复几何数据\n"
        
        self.geometry_info_text.config(state=tk.NORMAL)
        self.geometry_info_text.delete('1.0', tk.END)
        self.geometry_info_text.insert('1.0', info_text)
        self.geometry_info_text.config(state=tk.DISABLED)

    def populate_geometry_list(self):
        """填充几何要素列表"""
        if self.modified_gdf is None:
            return
        
        # 清空列表
        for item in self.geometry_tree.get_children():
            self.geometry_tree.delete(item)
        
        # 添加几何要素
        for idx, row in self.modified_gdf.iterrows():
            geom = row.geometry
            geom_type = geom.geom_type if geom is not None else 'None'
            
            # 计算面积或长度
            if geom is not None and geom_type == 'Polygon':
                area_length = f"{geom.area:.2f}"
            elif geom is not None and geom_type == 'LineString':
                area_length = f"{geom.length:.2f}"
            else:
                area_length = "N/A"
            
            # 计算顶点数
            if geom is not None and hasattr(geom, 'coords'):
                vertex_count = len(geom.coords)
            else:
                vertex_count = 0
            
            # 检查几何有效性
            is_valid = geom.is_valid if geom is not None else False
            status = "有效" if is_valid else "无效"
            
            # 检查问题
            issues = self.check_geometry_issues(geom)
            # 修正：确保所有元素为str
            issue_text = "; ".join(str(i) for i in issues) if issues else "无"
            
            # 确保idx是整数类型
            display_idx = int(idx) if isinstance(idx, (int, float)) else 0
            self.geometry_tree.insert('', 'end', values=(
                display_idx + 1, geom_type, area_length, vertex_count, status, issue_text
            ))
        
        # 更新几何可视化
        self.update_geometry_visualization()

    def update_geometry_visualization(self):
        """更新几何可视化"""
        if self.modified_gdf is None or self.modified_gdf.empty:
            return
        
        try:
            # 清除画布
            self.ax.clear()
            
            # 检查是否有几何数据
            if 'geometry' in self.modified_gdf.columns and self.modified_gdf.geometry.notna().any():
                # 绘制几何要素
                for idx, row in self.modified_gdf.iterrows():
                    geom = row.geometry
                    if geom is not None:
                        try:
                            # 根据几何类型绘制
                            if geom.geom_type == 'Polygon':
                                # 绘制多边形
                                coords = list(geom.exterior.coords)
                                if len(coords) > 2:
                                    x_coords = [coord[0] for coord in coords]
                                    y_coords = [coord[1] for coord in coords]
                                    self.ax.fill(x_coords, y_coords, alpha=0.5, edgecolor='black', linewidth=1)
                                    self.ax.plot(x_coords, y_coords, 'k-', linewidth=1)
                            
                            elif geom.geom_type == 'LineString':
                                # 绘制线
                                coords = list(geom.coords)
                                if len(coords) > 1:
                                    x_coords = [coord[0] for coord in coords]
                                    y_coords = [coord[1] for coord in coords]
                                    self.ax.plot(x_coords, y_coords, 'b-', linewidth=2)
                            
                            elif geom.geom_type == 'Point':
                                # 绘制点
                                coords = list(geom.coords)
                                if coords:
                                    x_coords = [coord[0] for coord in coords]
                                    y_coords = [coord[1] for coord in coords]
                                    self.ax.scatter(x_coords, y_coords, c='red', s=50, zorder=5)
                        except Exception as geom_error:
                            logger.warning(f"绘制几何 {idx} 失败: {geom_error}")
                            continue
            
            # 设置坐标轴
            self.ax.set_aspect('equal')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_title('几何要素可视化')
            self.ax.set_xlabel('X坐标')
            self.ax.set_ylabel('Y坐标')
            
            # 刷新画布
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"更新几何可视化失败: {e}")
            # 显示错误信息
            self.ax.clear()
            self.ax.text(0.5, 0.5, '几何可视化失败\n请使用修复功能', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=12, color='red')
            self.ax.set_title('几何可视化错误')
            self.canvas.draw()

    def check_geometry_issues(self, geom):
        """检查单个几何的问题"""
        issues = []
        
        if geom is None:
            return ["空几何"]
        
        # 检查有效性
        if not geom.is_valid:
            issues.append("几何无效")
        
        # 检查自相交
        if geom.geom_type == 'Polygon' and not geom.is_simple:
            issues.append("自相交")
        
        # 检查面积
        if geom.geom_type == 'Polygon':
            if geom.area == 0:
                issues.append("零面积")
            elif geom.area < 0.0001:  # 极小面积
                issues.append("面积过小")
        
        # 检查长度
        if geom.geom_type == 'LineString':
            if geom.length == 0:
                issues.append("零长度")
            elif geom.length < 0.001:  # 极小长度
                issues.append("长度过小")
        
        return issues

    def detect_issues(self):
        """检测所有几何问题"""
        if self.modified_gdf is None:
            return
        
        self.geometry_issues = []
        
        for idx, row in self.modified_gdf.iterrows():
            geom = row.geometry
            issues = self.check_geometry_issues(geom)
            
            if issues:
                self.geometry_issues.append({
                    'index': idx,
                    'geometry': geom,
                    'issues': issues
                })
        
        # 更新问题显示
        self.update_issues_display()
        
        self.status_var.set(f"检测到 {len(self.geometry_issues)} 个几何问题")

    def update_issues_display(self):
        """更新问题显示"""
        if not self.geometry_issues:
            issues_text = "未发现几何问题"
        else:
            issues_text = f"发现 {len(self.geometry_issues)} 个几何问题:\n\n"
            
            # 按问题类型分组
            issue_types = {}
            for issue in self.geometry_issues:
                for problem in issue['issues']:
                    if problem not in issue_types:
                        issue_types[problem] = 0
                    issue_types[problem] += 1
            
            for problem, count in issue_types.items():
                issues_text += f"• {problem}: {count} 个\n"
        
        self.issues_text.config(state=tk.NORMAL)
        self.issues_text.delete('1.0', tk.END)
        self.issues_text.insert('1.0', issues_text)
        self.issues_text.config(state=tk.DISABLED)

    def auto_fix_all(self):
        """一键修复所有几何问题"""
        if self.modified_gdf is None:
            return
        
        try:
            self.status_var.set("正在修复几何问题...")
            self.dialog.update()
            
            tolerance = float(self.tolerance_var.get())
            fixed_count = 0
            error_count = 0
            
            for idx, row in self.modified_gdf.iterrows():
                try:
                    original_geom = row.geometry
                    fixed_geom = self.fix_geometry(original_geom, tolerance)
                    
                    if fixed_geom != original_geom:
                        self.modified_gdf.at[idx, 'geometry'] = fixed_geom
                        fixed_count += 1
                except Exception as fix_error:
                    logger.warning(f"修复几何 {idx} 失败: {fix_error}")
                    error_count += 1
                    continue
            
            # 更新界面
            self.populate_geometry_list()
            self.detect_issues()
            self.update_geometry_visualization()
            
            # 显示修复结果
            result_message = f"已修复 {fixed_count} 个几何要素"
            if error_count > 0:
                result_message += f"\n{error_count} 个几何修复失败"
            
            self.status_var.set(f"修复完成: {fixed_count} 成功, {error_count} 失败")
            messagebox.showinfo("修复完成", result_message)
            
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            messagebox.showerror("错误", f"自动修复失败: {str(e)}")

    def fix_geometry(self, geom, tolerance):
        """修复单个几何"""
        if geom is None:
            return geom
        
        try:
            # 修复无效几何
            if not geom.is_valid:
                geom = make_valid(geom)
            
            # 修复自相交
            if geom.geom_type == 'Polygon' and not geom.is_simple:
                geom = geom.buffer(0)
            
            # 顶点捕捉
            if self.snap_vertices_var.get():
                geom = self.snap_vertices(geom, tolerance)
            
            # 确保几何类型一致
            if geom.geom_type == 'GeometryCollection':
                # 提取最大的几何要素
                try:
                    # 使用getattr安全地获取geoms属性
                    geoms_list = getattr(geom, 'geoms', None)
                    if geoms_list is not None:
                        geoms = list(geoms_list)
                        if geoms:
                            # 找到最大的几何要素
                            largest_geom = None
                            max_size = -1
                            for g in geoms:
                                try:
                                    size = getattr(g, 'area', 0) if hasattr(g, 'area') else getattr(g, 'length', 0)
                                    if size > max_size:
                                        max_size = size
                                        largest_geom = g
                                except Exception:
                                    continue
                            if largest_geom is not None:
                                geom = largest_geom
                except Exception:
                    # 如果任何操作失败，保持原几何不变
                    pass
            
            # 处理MultiPolygon
            if geom.geom_type == 'MultiPolygon':
                try:
                    # 获取最大的多边形
                    geoms_list = getattr(geom, 'geoms', None)
                    if geoms_list is not None:
                        polygons = list(geoms_list)
                        if polygons:
                            largest_polygon = max(polygons, key=lambda p: p.area)
                            geom = largest_polygon
                except Exception:
                    pass
            
            # 处理MultiLineString
            if geom.geom_type == 'MultiLineString':
                try:
                    # 获取最长的线
                    geoms_list = getattr(geom, 'geoms', None)
                    if geoms_list is not None:
                        lines = list(geoms_list)
                        if lines:
                            longest_line = max(lines, key=lambda l: l.length)
                            geom = longest_line
                except Exception:
                    pass
            
            # 处理MultiPoint
            if geom.geom_type == 'MultiPoint':
                try:
                    # 获取第一个点
                    geoms_list = getattr(geom, 'geoms', None)
                    if geoms_list is not None:
                        points = list(geoms_list)
                        if points:
                            geom = points[0]
                except Exception:
                    pass
            
            return geom
            
        except Exception as e:
            logger.error(f"修复几何失败: {e}")
            return geom

    def snap_vertices(self, geom, tolerance):
        """顶点捕捉"""
        if geom.geom_type == 'Polygon':
            coords = list(geom.exterior.coords)
            snapped_coords = self.snap_coordinates(coords, tolerance)
            return Polygon(snapped_coords)
        elif geom.geom_type == 'LineString':
            coords = list(geom.coords)
            snapped_coords = self.snap_coordinates(coords, tolerance)
            return LineString(snapped_coords)
        return geom

    def snap_coordinates(self, coords, tolerance):
        """坐标捕捉"""
        if len(coords) < 2:
            return coords
        
        snapped = [coords[0]]
        
        for i in range(1, len(coords)):
            current = coords[i]
            prev = snapped[-1]
            
            # 如果距离小于容差，则捕捉到前一个点
            if math.sqrt((current[0] - prev[0])**2 + (current[1] - prev[1])**2) < tolerance:
                continue
            else:
                snapped.append(current)
        
        return snapped

    def on_geometry_double_click(self, event):
        """双击几何要素事件"""
        selection = self.geometry_tree.selection()
        if selection:
            item = selection[0]
            values = self.geometry_tree.item(item)['values']
            index = int(values[0]) - 1
            
            # 高亮显示选中的几何
            self.highlight_geometry(index)

    def on_geometry_select(self, event):
        """几何要素选择事件"""
        selection = self.geometry_tree.selection()
        self.selected_features = set()
        
        for item in selection:
            values = self.geometry_tree.item(item)['values']
            index = int(values[0]) - 1
            self.selected_features.add(index)
        
        self.status_var.set(f"已选择 {len(self.selected_features)} 个几何要素")

    def highlight_geometry(self, index):
        """高亮显示几何要素"""
        if self.modified_gdf is None or index >= len(self.modified_gdf):
            return
        
        try:
            # 清除画布
            self.ax.clear()
            
            # 重新绘制所有几何要素
            for idx, row in self.modified_gdf.iterrows():
                geom = row.geometry
                if geom is not None:
                    # 根据几何类型绘制
                    if geom.geom_type == 'Polygon':
                        coords = list(geom.exterior.coords)
                        if len(coords) > 2:
                            x_coords = [coord[0] for coord in coords]
                            y_coords = [coord[1] for coord in coords]
                            # 如果是选中的几何，用不同颜色高亮
                            if idx == index:
                                self.ax.fill(x_coords, y_coords, alpha=0.7, color='red', edgecolor='red', linewidth=2)
                            else:
                                self.ax.fill(x_coords, y_coords, alpha=0.3, edgecolor='black', linewidth=1)
                            self.ax.plot(x_coords, y_coords, 'k-', linewidth=1)
                    
                    elif geom.geom_type == 'LineString':
                        coords = list(geom.coords)
                        if len(coords) > 1:
                            x_coords = [coord[0] for coord in coords]
                            y_coords = [coord[1] for coord in coords]
                            # 如果是选中的几何，用不同颜色高亮
                            if idx == index:
                                self.ax.plot(x_coords, y_coords, 'r-', linewidth=4)
                            else:
                                self.ax.plot(x_coords, y_coords, 'b-', linewidth=2)
                    
                    elif geom.geom_type == 'Point':
                        coords = list(geom.coords)
                        if coords:
                            x_coords = [coord[0] for coord in coords]
                            y_coords = [coord[1] for coord in coords]
                            # 如果是选中的几何，用不同颜色高亮
                            if idx == index:
                                self.ax.scatter(x_coords, y_coords, c='red', s=100, zorder=5)
                            else:
                                self.ax.scatter(x_coords, y_coords, c='blue', s=50, zorder=5)
            
            # 设置坐标轴
            self.ax.set_aspect('equal')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_title(f'几何要素可视化 - 选中要素 {index + 1}')
            self.ax.set_xlabel('X坐标')
            self.ax.set_ylabel('Y坐标')
            
            # 刷新画布
            self.canvas.draw()
            
            self.status_var.set(f"高亮显示几何要素 {index + 1}")
            
        except Exception as e:
            logger.error(f"高亮显示几何失败: {e}")
            self.status_var.set(f"高亮显示几何要素 {index + 1}")

    def zoom_in(self):
        """放大"""
        self.status_var.set("放大模式")

    def zoom_out(self):
        """缩小"""
        self.status_var.set("缩小模式")

    def pan(self):
        """平移"""
        self.status_var.set("平移模式")

    def select_mode(self):
        """选择模式"""
        self.status_var.set("选择模式")

    def edit_mode(self):
        """编辑模式"""
        self.status_var.set("编辑模式")

    def save_changes(self):
        """保存修改"""
        if self.modified_gdf is None:
            return
        
        try:
            # 检查是否有修改
            if self.modified_gdf.equals(self.original_gdf):
                messagebox.showinfo("提示", "没有修改需要保存")
                return
            
            # 保存到原文件
            if self.file_path.suffix.lower() == '.gdb':
                if self.layer_name:
                    self.modified_gdf.to_file(self.file_path, layer=self.layer_name, driver='OpenFileGDB')
                else:
                    # 保存到第一个图层
                    layers = fiona.listlayers(str(self.file_path))
                    if layers:
                        self.modified_gdf.to_file(self.file_path, layer=layers[0], driver='OpenFileGDB')
            else:
                self.modified_gdf.to_file(self.file_path)
            
            # 更新原始数据
            self.original_gdf = self.modified_gdf.copy()
            
            self.status_var.set("修改已保存")
            messagebox.showinfo("成功", "几何修改已保存")
            
        except Exception as e:
            logger.error(f"保存失败: {e}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def revert_changes(self):
        """撤销修改"""
        if messagebox.askyesno("确认", "确定要撤销所有修改吗？"):
            if self.original_gdf is not None:
                self.modified_gdf = self.original_gdf.copy()
                self.populate_geometry_list()
                self.detect_issues()
                self.update_geometry_visualization()
                self.status_var.set("已撤销修改")

    def run(self):
        """运行弹窗"""
        self.dialog.wait_window()
        return (self.modified_gdf is not None and 
                self.original_gdf is not None and 
                not self.original_gdf.equals(self.modified_gdf))

if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.withdraw()
    
    dialog = GeometryEditorDialog(root, "test.shp")
    dialog.run()
    
    root.destroy() 