#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段编辑弹窗
增强版 - 包含批量操作、数据验证、快速填充等功能
支持直接在GUI中编辑字段数据并保存回原文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging
import warnings
import re
import numpy as np
from datetime import datetime
import json
import csv
import difflib

# 抑制编码转换警告
warnings.filterwarnings('ignore', category=UserWarning, module='pyogrio')
warnings.filterwarnings('ignore', category=UserWarning, module='geopandas')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='pyogrio')
warnings.filterwarnings('ignore', message='.*One or several characters couldn\'t be converted correctly.*')
warnings.filterwarnings('ignore', message='.*couldn\'t be converted correctly.*')

# 导入编码修复工具
try:
    from encoding_fix_utils import clean_text_for_display, fix_garbled_text, fix_special_chars_for_display
except ImportError:
    # 如果导入失败，使用简单的替代函数
    def clean_text_for_display(text, max_length=100):
        if text is None:
            return "(空值)"
        text_str = str(text)
        if len(text_str) > max_length:
            text_str = text_str[:max_length-3] + "..."
        return text_str
    
    def fix_garbled_text(text):
        return str(text)
    
    def fix_special_chars_for_display(text):
        return str(text)

logger = logging.getLogger(__name__)

class FieldEditorDialog:
    """字段编辑弹窗"""
    
    def __init__(self, parent, file_path, field_name, layer_name=None):
        """
        初始化字段编辑弹窗
        """
        # 添加参数验证和调试信息
        logger.info(f"初始化字段编辑器: parent={parent}, file_path={file_path}, field_name={field_name}, layer_name={layer_name}")
        
        if not parent:
            raise ValueError("父窗口不能为空")
        if not file_path:
            raise ValueError("文件路径不能为空")
        if not field_name:
            raise ValueError("字段名不能为空")
        
        self.parent = parent
        self.file_path = Path(file_path)
        self.field_name = field_name
        self.layer_name = layer_name
        self.original_data = None
        self.modified_data = None
        self.selected_items = set()
        self.search_results = []
        self.current_search_index = -1
        
        # 初始化缺失的属性
        self.search_var = None
        self.replace_var = None
        self.operation_count = 0
        self.repair_text = None
        
        # 验证文件是否存在
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        logger.info(f"文件路径验证通过: {self.file_path}")
        
        # 创建弹窗
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"编辑字段: {field_name}")
        self.dialog.geometry("1200x800")  # 增加默认窗口大小
        self.dialog.minsize(1000, 700)    # 设置最小窗口大小
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 设置弹窗位置为屏幕中心
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (800 // 2)
        self.dialog.geometry(f"1200x800+{x}+{y}")
        
        try:
            self.setup_ui()
            self.load_data()
            logger.info("字段编辑器初始化完成")
        except Exception as e:
            logger.error(f"字段编辑器初始化失败: {e}")
            self.dialog.destroy()
            raise

    def setup_ui(self):
        """设置界面"""
        # 主布局
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧面板 - 工具和统计
        left_panel = ttk.Frame(main_frame, width=320)  # 增加左侧面板宽度
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)  # 防止面板被压缩
        
        # 字段信息面板
        field_info_frame = ttk.LabelFrame(left_panel, text="字段信息")
        field_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用Grid布局来对齐标签和值
        field_grid = ttk.Frame(field_info_frame)
        field_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # 配置Grid列的权重
        field_grid.grid_columnconfigure(1, weight=1)
        
        # 获取字段标准信息
        field_info = self.get_field_standards()
        
        # 字段信息标签样式
        label_style = {'sticky': 'w', 'pady': 2, 'padx': 3}
        value_style = {'sticky': 'w', 'pady': 2, 'padx': 3}
        
        # 字段名
        ttk.Label(field_grid, text="字段名：").grid(row=0, column=0, **label_style)
        ttk.Label(field_grid, text=self.field_name).grid(row=0, column=1, **value_style)
        
        # 字段别名
        ttk.Label(field_grid, text="别名：").grid(row=1, column=0, **label_style)
        ttk.Label(field_grid, text=field_info.get('字段别名', '-')).grid(row=1, column=1, **value_style)
        
        # 字段类型
        ttk.Label(field_grid, text="类型：").grid(row=2, column=0, **label_style)
        ttk.Label(field_grid, text=field_info.get('字段类型', '-')).grid(row=2, column=1, **value_style)
        
        # 是否必填
        ttk.Label(field_grid, text="必填：").grid(row=3, column=0, **label_style)
        ttk.Label(field_grid, text="是" if field_info.get('必填', False) else "否").grid(row=3, column=1, **value_style)
        
        # 修复建议面板
        suggestion_frame = ttk.LabelFrame(left_panel, text="修复建议")
        suggestion_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.suggestion_text = tk.Text(suggestion_frame, height=6, width=40, wrap=tk.WORD)
        self.suggestion_text.pack(fill=tk.BOTH, padx=5, pady=(5,0))
        self.suggestion_text.config(state=tk.DISABLED)
        
        # 添加一键修复按钮
        button_frame = ttk.Frame(suggestion_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(button_frame, text="一键修复", command=self.quick_fix).pack(side=tk.LEFT)
        
        # 统计信息面板
        stats_frame = ttk.LabelFrame(left_panel, text="统计信息")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=10, width=40)
        self.stats_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 右侧主面板
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 标题信息
        title_frame = ttk.Frame(right_panel)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(title_frame, text=f"文件: {self.file_path.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        if self.layer_name:
            ttk.Label(title_frame, text=f"图层: {self.layer_name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 工具栏
        toolbar_frame = ttk.Frame(right_panel)
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        # 绑定快捷键
        self.dialog.bind('<Control-s>', lambda e: self.save_changes())
        self.dialog.bind('<Control-z>', lambda e: self.revert_changes())
        self.dialog.bind('<Control-q>', lambda e: self.dialog.destroy())
        self.dialog.bind('<Control-r>', lambda e: self.quick_fix())
        self.dialog.bind('<F5>', lambda e: self.refresh_data())
        
        # 添加快捷键提示到按钮
        ttk.Button(toolbar_frame, text="保存修改 (Ctrl+S)", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="撤销修改 (Ctrl+Z)", command=self.revert_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="关闭 (Ctrl+Q)", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 添加导出按钮到工具栏
        ttk.Button(toolbar_frame, text="导出数据", command=self.show_export_dialog).pack(side=tk.LEFT, padx=5)
        
        # 创建表格
        self.create_table(right_panel)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=2)
        
        # 绑定窗口大小变化事件
        self.dialog.bind('<Configure>', self.on_window_resize)

    def on_window_resize(self, event):
        """窗口大小变化时的处理"""
        if event.widget == self.dialog:
            # 重新计算表格列宽
            self.update_table_column_widths()
    
    def update_table_column_widths(self):
        """更新表格列宽以适应窗口大小"""
        try:
            if hasattr(self, 'tree'):
                # 获取窗口宽度
                window_width = self.dialog.winfo_width()
                left_panel_width = 320  # 左侧面板宽度
                available_width = window_width - left_panel_width - 40  # 减去边距
                
                if available_width > 400:  # 确保有足够的最小宽度
                    # 动态调整列宽
                    index_width = max(80, available_width * 0.1)
                    value_width = max(400, available_width * 0.6)
                    null_width = max(100, available_width * 0.15)
                    validation_width = max(100, available_width * 0.15)
                    
                    self.tree.column('index', width=int(index_width))
                    self.tree.column('value', width=int(value_width))
                    self.tree.column('is_null', width=int(null_width))
                    self.tree.column('validation', width=int(validation_width))
        except Exception as e:
            logger.warning(f"更新表格列宽时出错: {e}")

    def create_table(self, parent):
        """创建表格"""
        # 表格框架
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview作为表格
        columns = ('index', 'value', 'is_null', 'validation')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        # 设置列标题
        self.tree.heading('index', text='序号')
        self.tree.heading('value', text='字段值')
        self.tree.heading('is_null', text='是否为空')
        self.tree.heading('validation', text='验证状态')
        
        # 设置初始列宽
        self.tree.column('index', width=80, minwidth=60)
        self.tree.column('value', width=600, minwidth=400)  # 增加字段值列的宽度
        self.tree.column('is_null', width=100, minwidth=80)
        self.tree.column('validation', width=100, minwidth=80)
        
        # 配置标签样式
        self.tree.tag_configure('need_fix', background='#FFE0E0')
        self.tree.tag_configure('fixed', background='#E0FFE0')
        self.tree.tag_configure('selected', background='#0078D7')
        
        # 添加滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局 - 使用pack布局以支持自适应
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定事件
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<Control-a>', self.select_all)
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_change)
        
        # 创建右键菜单
        self.create_context_menu()

    def load_data(self):
        """加载数据时分析模式"""
        try:
            self.status_var.set("正在加载数据...")
            self.dialog.update()
            
            logger.info(f"开始加载文件: {self.file_path}")
            logger.info(f"字段名: {self.field_name}")
            
            # 读取文件
            if self.file_path.suffix.lower() == '.gdb':
                logger.info("正在读取GDB文件...")
                data = gpd.read_file(self.file_path, driver='OpenFileGDB')
            else:
                # SHP/DBF文件 - 优先使用GBK编码
                logger.info("正在读取SHP/DBF文件...")
                encodings = ['gbk', 'utf-8', 'gb2312', 'cp936']
                data = None
                success_encoding = None
                
                for encoding in encodings:
                    try:
                        data = gpd.read_file(self.file_path, encoding=encoding)
                        success_encoding = encoding
                        logger.info(f"成功使用编码 {encoding} 读取文件")
                        break
                    except Exception as e:
                        logger.warning(f"使用编码 {encoding} 读取失败: {e}")
                        continue
            
            if data is None:
                raise ValueError("无法读取文件")
            
            logger.info(f"文件读取成功，总行数: {len(data)}")
            logger.info(f"所有列: {list(data.columns)}")
            
            # 检查字段是否存在
            if self.field_name not in data.columns:
                raise ValueError(f"字段 '{self.field_name}' 不存在")
            
            # 获取字段数据
            field_data = data[self.field_name]
            logger.info(f"字段值示例: {field_data.head()}")
            logger.info(f"字段类型: {field_data.dtype}")
            
            # 保存原始数据
            self.original_data = data
            self.modified_data = data.copy()
            
            # 更新表格显示
            self.populate_table(field_data)
            
            # 立即分析数据模式
            self.analyze_data_patterns()
            
            self.status_var.set(f"已加载 {len(field_data)} 条记录")
            
        except Exception as e:
            logger.error(f"加载数据时出错: {e}", exc_info=True)
            messagebox.showerror("错误", f"加载数据失败: {str(e)}")
            self.dialog.destroy()

    def populate_table(self, field_data):
        """填充表格数据"""
        try:
            # 清空现有数据
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 记录填充的数据
            filled_count = 0
            null_count = 0
            
            # 填充数据
            for idx, value in enumerate(field_data, 1):
                is_null = pd.isna(value) or (isinstance(value, str) and not value.strip())
                display_value = "" if is_null else str(value).strip()
                
                item = self.tree.insert('', 'end', values=(
                    idx,
                    display_value,
                    '是' if is_null else '否'
                ))
                
                # 设置标签
                if is_null:
                    self.tree.item(item, tags=('need_fix',))
                    null_count += 1
                else:
                    filled_count += 1
            
            logger.info(f"表格填充完成 - 总行数: {len(field_data)}, 空值: {null_count}, 非空值: {filled_count}")
            
        except Exception as e:
            logger.error(f"填充表格时出错: {e}", exc_info=True)
            raise
    
    def on_double_click(self, event):
        """双击编辑"""
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        
        if column == '#2':  # 值列
            self.edit_cell(item)
    
    def edit_cell(self, item):
        """编辑单元格"""
        # 获取当前值
        current_values = self.tree.item(item, 'values')
        current_value = current_values[1]
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.dialog)
        edit_dialog.title("编辑值")
        edit_dialog.geometry("400x150")
        edit_dialog.transient(self.dialog)
        edit_dialog.grab_set()
        
        # 居中显示
        edit_dialog.update_idletasks()
        x = (edit_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (edit_dialog.winfo_screenheight() // 2) - (150 // 2)
        edit_dialog.geometry(f"400x150+{x}+{y}")
        
        ttk.Label(edit_dialog, text="请输入新值:").pack(pady=10)
        
        # 修复显示值中的乱码和特殊字符
        display_value = current_value if current_value != "(空值)" else ""
        if display_value:
            display_value = fix_garbled_text(display_value)
            display_value = fix_special_chars_for_display(display_value)
        
        entry_var = tk.StringVar(value=display_value)
        entry = ttk.Entry(edit_dialog, textvariable=entry_var, width=50)
        entry.pack(pady=10)
        entry.focus()
        
        def save_edit():
            new_value = entry_var.get().strip()
            
            # 更新表格显示
            if new_value == "":
                display_value = "(空值)"
                is_null = "是"
            else:
                display_value = new_value
                is_null = "否"
            
            self.tree.item(item, values=(current_values[0], display_value, is_null))
            
            # 更新数据
            index = int(current_values[0]) - 1
            if self.modified_data is not None:
                if new_value == "":
                    self.modified_data.loc[index, self.field_name] = None
                else:
                    self.modified_data.loc[index, self.field_name] = new_value
            
            # 更新标签
            if is_null:
                self.tree.item(item, tags=('need_fix',))
            else:
                self.tree.item(item, tags=('fixed',))
            
            edit_dialog.destroy()
            self.status_var.set("已修改，请点击保存")
            self.record_operation('edit')
        
        def cancel_edit():
            edit_dialog.destroy()
        
        button_frame = ttk.Frame(edit_dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="保存", command=save_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=cancel_edit).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
    
    def edit_selected(self):
        """编辑选中的行"""
        selection = self.tree.selection()
        if selection:
            self.edit_cell(selection[0])
    
    def set_null(self):
        """设为空值"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            current_values = self.tree.item(item, 'values')
            index = int(current_values[0]) - 1
            
            # 更新表格显示
            self.tree.item(item, values=(current_values[0], "(空值)", "是"))
            
            # 更新数据
            if self.modified_data is not None:
                self.modified_data.loc[index, self.field_name] = None
            
            self.status_var.set("已设为空值，请点击保存")
            self.record_operation('set_null')
    
    def copy_value(self):
        """复制值"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            current_values = self.tree.item(item, 'values')
            value = current_values[1]
            
            if value != "(空值)":
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(value)
                self.status_var.set("已复制到剪贴板")
                self.record_operation('copy_value')
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def save_changes(self):
        """保存修改"""
        try:
            self.status_var.set("正在保存...")
            self.dialog.update()
            
            # 检查是否有修改
            if self.original_data is not None and self.modified_data is not None:
                if self.original_data.equals(self.modified_data):
                    messagebox.showinfo("提示", "没有修改需要保存")
                    return
            
            # 保存文件
            if self.modified_data is not None:
                if self.file_path.suffix.lower() == '.gdb':
                    # GDB文件保存
                    self.modified_data.to_file(self.file_path, driver='OpenFileGDB')
                else:
                    # SHP/DBF文件保存 - 尝试多种编码
                    save_success = False
                    save_errors = []
                    
                    # 尝试UTF-8编码
                    try:
                        self.modified_data.to_file(self.file_path, encoding='utf-8')
                        save_success = True
                        logger.info("使用UTF-8编码保存成功")
                    except Exception as e:
                        save_errors.append(f"UTF-8保存失败: {e}")
                    
                    # 如果UTF-8失败，尝试GBK编码
                    if not save_success:
                        try:
                            self.modified_data.to_file(self.file_path, encoding='gbk')
                            save_success = True
                            logger.info("使用GBK编码保存成功")
                        except Exception as e:
                            save_errors.append(f"GBK保存失败: {e}")
                    
                    # 如果GBK也失败，尝试使用错误处理
                    if not save_success:
                        try:
                            self.modified_data.to_file(self.file_path, encoding='gbk', errors='replace')
                            save_success = True
                            logger.warning("使用GBK编码（错误替换模式）保存成功")
                        except Exception as e:
                            save_errors.append(f"GBK错误替换保存失败: {e}")
                    
                    if not save_success:
                        raise Exception(f"所有保存方式都失败: {'; '.join(save_errors)}")
                
                self.status_var.set("保存成功")
                messagebox.showinfo("成功", "修改已保存到原文件")
                
                # 更新原始数据
                if self.modified_data is not None:
                    self.original_data = self.modified_data.copy()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            logger.error(f"保存失败: {e}")
            self.status_var.set("保存失败")
    
    def revert_changes(self):
        """撤销修改"""
        if messagebox.askyesno("确认", "确定要撤销所有修改吗？"):
            if self.original_data is not None:
                self.modified_data = self.original_data.copy()
                self.populate_table(self.modified_data[self.field_name])
                self.status_var.set("已撤销修改")
    
    def run(self):
        """运行弹窗"""
        self.dialog.wait_window()
        return self.modified_data is not None and self.original_data is not None and not self.original_data.equals(self.modified_data) 

    def batch_edit(self):
        """批量编辑对话框"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("批量编辑")
        dialog.geometry("400x300")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # 编辑模式选择
        ttk.Label(dialog, text="编辑模式:").pack(pady=5)
        mode_var = tk.StringVar(value="replace")
        ttk.Radiobutton(dialog, text="替换", variable=mode_var, value="replace").pack()
        ttk.Radiobutton(dialog, text="前缀", variable=mode_var, value="prefix").pack()
        ttk.Radiobutton(dialog, text="后缀", variable=mode_var, value="suffix").pack()
        
        # 输入值
        ttk.Label(dialog, text="输入值:").pack(pady=5)
        value_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=value_var).pack(fill=tk.X, padx=10)
        
        def apply_batch_edit():
            mode = mode_var.get()
            value = value_var.get()
            selected = self.tree.selection()
            
            if not selected:
                messagebox.showwarning("警告", "请先选择要编辑的项")
                return
            
            for item in selected:
                old_value = self.tree.item(item)['values'][1]
                if old_value is None or pd.isna(old_value):
                    old_value = ""
                
                if mode == "replace":
                    new_value = value
                elif mode == "prefix":
                    new_value = value + str(old_value)
                elif mode == "suffix":
                    new_value = str(old_value) + value
                
                self.tree.set(item, 'value', new_value)
                self.tree.set(item, 'is_null', '否' if new_value else '是')
            
            dialog.destroy()
            self.update_statistics()
            self.record_operation('batch_edit')
        
        ttk.Button(dialog, text="应用", command=apply_batch_edit).pack(pady=10)
        ttk.Button(dialog, text="取消", command=dialog.destroy).pack()
    
    def validate_data(self):
        """数据验证"""
        # 获取字段类型
        if self.original_data is None or self.field_name is None:
            field_type = None
        else:
            field_type = self.original_data[self.field_name].dtype if self.field_name in self.original_data else None

        # 验证规则
        rules = {
            'object': lambda x: isinstance(x, str) and bool(x.strip()),  # 非空字符串
            'int64': lambda x: pd.notna(x) and float(x).is_integer(),   # 整数
            'float64': lambda x: pd.notna(x) and isinstance(float(x), float),  # 浮点数
            'datetime64[ns]': lambda x: pd.notna(x) and pd.to_datetime(x, errors='coerce') is not pd.NaT  # 日期
        }
        
        # 应用验证
        for item in self.tree.get_children():
            item_data = self.tree.item(item)
            values = item_data.get('values') if item_data else None
            value = values[1] if values and len(values) > 1 else None
            try:
                is_null = False
                try:
                    is_null = bool(pd.isna(value))
                except Exception:
                    is_null = value is None
                if is_null or value == '':
                    self.tree.set(item, 'validation', '空值')
                elif str(field_type) in rules and rules[str(field_type)](value):
                    self.tree.set(item, 'validation', '有效')
                else:
                    self.tree.set(item, 'validation', '无效')
            except:
                self.tree.set(item, 'validation', '无效')
        
        self.update_statistics()
        self.record_operation('validate')
    
    def quick_fill(self):
        """快速填充对话框"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("快速填充")
        dialog.geometry("400x400")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # 填充模式
        ttk.Label(dialog, text="填充模式:").pack(pady=5)
        mode_var = tk.StringVar(value="sequence")
        ttk.Radiobutton(dialog, text="序列", variable=mode_var, value="sequence").pack()
        ttk.Radiobutton(dialog, text="重复值", variable=mode_var, value="repeat").pack()
        ttk.Radiobutton(dialog, text="随机值", variable=mode_var, value="random").pack()
        
        # 参数框架
        param_frame = ttk.LabelFrame(dialog, text="参数")
        param_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 序列参数
        seq_frame = ttk.Frame(param_frame)
        ttk.Label(seq_frame, text="起始值:").grid(row=0, column=0, padx=5)
        start_var = tk.StringVar(value="1")
        ttk.Entry(seq_frame, textvariable=start_var).grid(row=0, column=1, padx=5)
        
        ttk.Label(seq_frame, text="步长:").grid(row=1, column=0, padx=5)
        step_var = tk.StringVar(value="1")
        ttk.Entry(seq_frame, textvariable=step_var).grid(row=1, column=1, padx=5)
        
        # 重复值参数
        repeat_frame = ttk.Frame(param_frame)
        ttk.Label(repeat_frame, text="重复值:").pack(side=tk.LEFT, padx=5)
        repeat_var = tk.StringVar()
        ttk.Entry(repeat_frame, textvariable=repeat_var).pack(side=tk.LEFT, padx=5)
        
        # 随机值参数
        random_frame = ttk.Frame(param_frame)
        ttk.Label(random_frame, text="最小值:").grid(row=0, column=0, padx=5)
        min_var = tk.StringVar(value="0")
        ttk.Entry(random_frame, textvariable=min_var).grid(row=0, column=1, padx=5)
        
        ttk.Label(random_frame, text="最大值:").grid(row=1, column=0, padx=5)
        max_var = tk.StringVar(value="100")
        ttk.Entry(random_frame, textvariable=max_var).grid(row=1, column=1, padx=5)
        
        def update_param_frame(*args):
            for frame in [seq_frame, repeat_frame, random_frame]:
                frame.pack_forget()
            
            if mode_var.get() == "sequence":
                seq_frame.pack(fill=tk.X, padx=5, pady=5)
            elif mode_var.get() == "repeat":
                repeat_frame.pack(fill=tk.X, padx=5, pady=5)
            else:
                random_frame.pack(fill=tk.X, padx=5, pady=5)
        
        mode_var.trace('w', update_param_frame)
        update_param_frame()
        
        def apply_quick_fill():
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请先选择要填充的项")
                return
            
            mode = mode_var.get()
            try:
                if mode == "sequence":
                    start = float(start_var.get())
                    step = float(step_var.get())
                    for i, item in enumerate(selected):
                        value = start + i * step
                        self.tree.set(item, 'value', str(value))
                        self.tree.set(item, 'is_null', '否')
                
                elif mode == "repeat":
                    value = repeat_var.get()
                    for item in selected:
                        self.tree.set(item, 'value', value)
                        self.tree.set(item, 'is_null', '否' if value else '是')
                
                else:  # random
                    min_val = float(min_var.get())
                    max_val = float(max_var.get())
                    for item in selected:
                        value = np.random.uniform(min_val, max_val)
                        self.tree.set(item, 'value', str(value))
                        self.tree.set(item, 'is_null', '否')
                
                dialog.destroy()
                self.update_statistics()
                
            except ValueError as e:
                messagebox.showerror("错误", f"参数错误: {str(e)}")
            self.record_operation('quick_fill')
        
        ttk.Button(dialog, text="应用", command=apply_quick_fill).pack(pady=10)
        ttk.Button(dialog, text="取消", command=dialog.destroy).pack()
    
    def search(self):
        """搜索功能"""
        if self.search_var is None:
            messagebox.showerror("错误", "搜索变量未初始化")
            return
        search_text = self.search_var.get() if hasattr(self.search_var, "get") else None
        if not search_text:
            return

        # 清除之前的搜索结果
        self.search_results = []
        self.current_search_index = -1
        
        # 搜索
        for item in self.tree.get_children():
            item_data = self.tree.item(item)
            values = item_data.get('values') if item_data else None
            value = values[1] if values and len(values) > 1 else None
            if search_text.lower() in str(value).lower():
                self.search_results.append(item)
        
        if self.search_results:
            self.current_search_index = 0
            self.highlight_search_result()
        else:
            messagebox.showinfo("搜索", "未找到匹配项")
        self.record_operation('search')
    
    def highlight_search_result(self):
        """高亮显示搜索结果"""
        if not self.search_results:
            return
        
        # 清除之前的选择
        self.tree.selection_remove(*self.tree.selection())
        
        # 高亮当前项
        item = self.search_results[self.current_search_index]
        self.tree.selection_add(item)
        self.tree.see(item)
        
        # 更新状态栏
        self.status_var.set(f"找到 {len(self.search_results)} 个匹配项 ({self.current_search_index + 1}/{len(self.search_results)})")
    
    def replace(self):
        """替换当前选中项"""
        if not self.search_results or self.current_search_index < 0:
            return
        
        item = self.search_results[self.current_search_index]
        item_data = self.tree.item(item)
        values = item_data.get('values') if item_data else None
        old_value = str(values[1]) if values and len(values) > 1 else ""
        search_text = self.search_var.get() if self.search_var and hasattr(self.search_var, "get") else ""
        replace_text = self.replace_var.get() if self.replace_var and hasattr(self.replace_var, "get") else ""
        new_value = old_value.replace(search_text, replace_text)
        
        self.tree.set(item, 'value', new_value)
        self.tree.set(item, 'is_null', '否' if new_value else '是')
        # 移动到下一个
        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self.highlight_search_result()
        self.record_operation('replace')
    
    def replace_all(self):
        """替换所有匹配项"""
        if not self.search_results:
            return
        
        count = 0
        for item in self.search_results:
            item_data = self.tree.item(item)
            values = item_data.get('values') if item_data else None
            old_value = str(values[1]) if values and len(values) > 1 else ""
            search_text = self.search_var.get() if self.search_var and hasattr(self.search_var, "get") else ""
            replace_text = self.replace_var.get() if self.replace_var and hasattr(self.replace_var, "get") else ""
            new_value = old_value.replace(search_text, replace_text)
            
            self.tree.set(item, 'value', new_value)
            self.tree.set(item, 'is_null', '否' if new_value else '是')
            count += 1
        
        self.status_var.set(f"已替换 {count} 处")
        self.update_statistics()
        self.record_operation('replace_all')
    
    def export_data(self):
        """导出数据"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV文件", "*.csv"),
                ("Excel文件", "*.xlsx"),
                ("JSON文件", "*.json")
            ]
        )
        
        if not file_path:
            return
        
        try:
            data = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                data.append({
                    '序号': values[0],
                    '字段值': values[1],
                    '是否为空': values[2],
                    '验证状态': values[3] if len(values) > 3 else ''
                })
            
            if file_path.endswith('.csv'):
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['序号', '字段值', '是否为空', '验证状态'])
                    writer.writeheader()
                    writer.writerows(data)
            
            elif file_path.endswith('.xlsx'):
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)
            
            else:  # .json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.status_var.set(f"数据已导出到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def import_data(self):
        """导入数据"""
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("CSV文件", "*.csv"),
                ("Excel文件", "*.xlsx"),
                ("JSON文件", "*.json")
            ]
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:  # .json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
            
            # 清空现有数据
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 导入新数据
            for _, row in df.iterrows():
                row_value = row.get('字段值', '') if row is not None and hasattr(row, 'get') else ''
                is_null = False
                try:
                    is_null = bool(pd.isna(row_value))
                except Exception:
                    is_null = row_value is None
                values = [
                    row.get('序号', '') if row is not None and hasattr(row, 'get') else '',
                    row_value,
                    '是' if is_null else '否',
                    row.get('验证状态', '') if row is not None and hasattr(row, 'get') else ''
                ]
                self.tree.insert('', 'end', values=values)
            
            self.status_var.set(f"已从 {file_path} 导入数据")
            self.update_statistics()
            
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")
    
    def update_statistics(self):
        """更新统计信息"""
        try:
            total = len(self.tree.get_children())
            null_count = sum(1 for item in self.tree.get_children() 
                           if self.tree.item(item)['values'][2] == '是')
            
            # 获取所有非空值
            values = [self.tree.item(item)['values'][1] 
                     for item in self.tree.get_children() 
                     if self.tree.item(item)['values'][2] == '否']
            
            # 获取字段标准信息
            field_info = self.get_field_standards()
            field_type = field_info.get('字段类型', '未知') if field_info is not None else '未知'
            
            # 计算统计信息
            stats = {
                '总记录数': total,
                '空值数量': null_count,
                '非空数量': total - null_count,
                '空值比例': f"{(null_count/total*100):.1f}%" if total > 0 else "0%"
            }
            
            # 根据字段类型添加相应的统计
            if field_type in ['Double', 'Integer']:
                try:
                    numeric_values = [float(v) for v in values if str(v).replace('.', '').isdigit()]
                    if numeric_values:
                        stats.update({
                            '最小值': f"{min(numeric_values):.2f}",
                            '最大值': f"{max(numeric_values):.2f}",
                            '平均值': f"{sum(numeric_values)/len(numeric_values):.2f}"
                        })
                except:
                    pass
            elif field_type == 'Text':
                if values:
                    lengths = [len(str(v)) for v in values]
                    stats.update({
                        '最短长度': min(lengths),
                        '最长长度': max(lengths),
                        '平均长度': f"{sum(lengths)/len(lengths):.1f}",
                        '唯一值数': len(set(values))
                    })
            
            # 更新统计文本
            self.stats_text.config(state=tk.NORMAL) if self.stats_text is not None else None
            self.stats_text.delete('1.0', tk.END) if self.stats_text is not None else None
            for key, value in stats.items():
                self.stats_text.insert(tk.END, f"{key}: {value}\n")
            self.stats_text.config(state=tk.DISABLED) if self.stats_text is not None else None
            
        except Exception as e:
            logger.error(f"更新统计信息时出错: {e}", exc_info=True)
            self.stats_text.config(state=tk.NORMAL) if self.stats_text is not None else None
            self.stats_text.delete('1.0', tk.END) if self.stats_text is not None else None
            self.stats_text.insert(tk.END, "统计信息生成失败") if self.stats_text is not None else None
            self.stats_text.config(state=tk.DISABLED) if self.stats_text is not None else None

    def select_all(self, event=None):
        """选择所有项"""
        self.tree.selection_set(*self.tree.get_children())
        return 'break'  # 阻止默认行为
    
    def on_selection_change(self, event=None):
        """选择变化时更新状态栏和建议"""
        selected = len(self.tree.selection())
        total = len(self.tree.get_children())
        self.status_var.set(f"已选择 {selected}/{total} 项")
        self.update_suggestions()
        
        # 更新选中项的高亮
        for item in self.tree.get_children():
            current_tags = list(self.tree.item(item)['tags'] or ())
            if 'selected' in current_tags:
                current_tags.remove('selected')
            if item in self.tree.selection():
                if 'need_fix' not in current_tags and 'fixed' not in current_tags:
                    current_tags.append('selected')
            self.tree.item(item, tags=current_tags)

    def batch_edit_selected(self):
        """批量编辑选中项"""
        if not self.tree.selection():
            messagebox.showwarning("警告", "请先选择要编辑的项")
            return
        self.batch_edit()
    
    def validate_selected(self):
        """验证选中项"""
        if not self.tree.selection():
            messagebox.showwarning("警告", "请先选择要验证的项")
            return
        self.validate_data() 
        return self.modified_data is not None and self.original_data is not None and not self.original_data.equals(self.modified_data) 

    def analyze_data_patterns(self):
        """分析数据模式和特征"""
        try:
            logger.info("开始分析数据模式...")
            
            # 直接从树形视图获取数据
            all_values = []
            null_count = 0
            value_counts = {}
            
            # 收集所有值
            for item in self.tree.get_children():
                item_data = self.tree.item(item)
                values = item_data.get('values') if item_data else None
                value = values[1] if values and len(values) > 1 else None
                is_null = values[2] == '是' if values and len(values) > 2 else False
                
                logger.debug(f"处理行: 值={value}, 是否为空={is_null}")
                
                if is_null:
                    null_count += 1
                elif value:  # 确保值不是空字符串
                    str_value = str(value).strip()
                    if str_value:  # 再次确保去除空格后不是空字符串
                        all_values.append(str_value)
                        value_counts[str_value] = value_counts.get(str_value, 0) + 1
            
            logger.info(f"值统计: {value_counts}")
            logger.info(f"空值数量: {null_count}")
            
            total_count = len(all_values) + null_count
            
            # 如果没有任何有效值，返回空结果
            if not value_counts:
                logger.warning("未找到任何有效值")
                self.data_patterns = {
                    'total_count': total_count,
                    'null_count': null_count,
                    'has_pattern': False
                }
                return
            
            # 找出最常见的值
            sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            most_common = sorted_values[0]
            most_common_value = most_common[0]
            most_common_count = most_common[1]
            
            # 计算比例
            non_null_count = len(all_values)
            non_null_percentage = (most_common_count / non_null_count * 100) if non_null_count > 0 else 0
            
            logger.info(f"最常见值: {most_common_value} (出现 {most_common_count} 次)")
            logger.info(f"非空值比例: {non_null_percentage:.1f}%")
            
            # 存储分析结果
            self.data_patterns = {
                'total_count': total_count,
                'null_count': null_count,
                'non_null_count': non_null_count,
                'most_common_value': most_common_value,
                'most_common_count': most_common_count,
                'non_null_percentage': non_null_percentage,
                'has_pattern': most_common_count > 1,  # 只要有重复值就认为有模式
                'value_counts': sorted_values[:5]  # 保存前5个最常见的值
            }
            
            logger.info(f"数据分析结果: {self.data_patterns}")
            
            self.update_suggestions()
            
        except Exception as e:
            logger.error(f"分析数据模式时出错: {e}", exc_info=True)
            self.data_patterns = {}

    def update_suggestions(self):
        """更新智能提示"""
        try:
            logger.info("开始更新建议...")
            
            if not self.data_patterns:
                logger.warning("没有数据模式信息，无法生成建议")
                self.suggestion_text.config(state=tk.NORMAL)
                self.suggestion_text.delete('1.0', tk.END)
                self.suggestion_text.insert('1.0', '暂无建议')
                self.suggestion_text.config(state=tk.DISABLED)
                return
            
            # 获取统计信息
            null_count = self.data_patterns.get('null_count', 0)
            has_pattern = self.data_patterns.get('has_pattern', False)
            
            # 获取字段标准信息
            field_info = self.get_field_standards()
            field_alias = field_info.get('字段别名', self.field_name) if field_info is not None else self.field_name
            field_type = field_info.get('字段类型', '未知') if field_info is not None else '未知'
            is_required = field_info.get('必填', False) if field_info is not None else False
            
            # 如果有空值且有数据模式
            if null_count > 0 and has_pattern:
                most_common_value = self.data_patterns.get('most_common_value')
                
                # 构建建议信息
                suggestion = f"字段\"{field_alias}\"存在 {null_count} 个空值\n"
                if is_required:
                    suggestion += "【必填字段】必须填写\n"
                suggestion += f"建议值: {most_common_value}\n"
                suggestion += f"(应为{field_type}类型)"
            else:
                if null_count > 0:
                    suggestion = f"字段\"{field_alias}\"存在 {null_count} 个空值\n"
                    if is_required:
                        suggestion += "【必填字段】请手动填写"
                    else:
                        suggestion += "可以保持为空"
                else:
                    suggestion = "暂无需要修复的内容"
            
            # 更新提示文本
            self.suggestion_text.config(state=tk.NORMAL)
            self.suggestion_text.delete('1.0', tk.END)
            self.suggestion_text.insert('1.0', suggestion)
            self.suggestion_text.config(state=tk.DISABLED)
            
            logger.info(f"生成的建议: {suggestion}")
            
        except Exception as e:
            logger.error(f"更新建议时出错: {e}", exc_info=True)
            self.suggestion_text.config(state=tk.NORMAL)
            self.suggestion_text.delete('1.0', tk.END)
            self.suggestion_text.insert('1.0', '生成建议时出错')
            self.suggestion_text.config(state=tk.DISABLED)

    def record_operation(self, operation):
        """记录操作"""
        self.last_operation = operation
        if not hasattr(self, 'operation_count') or not isinstance(self.operation_count, dict):
            self.operation_count = {}
        self.operation_count[operation] = self.operation_count.get(operation, 0) + 1
        self.update_suggestions() 

    def scan_similar_fields(self):
        """扫描文件夹中的其他文件，查找相同字段的值"""
        try:
            self.status_var.set("正在扫描其他文件...")
            self.dialog.update()
            
            # 获取当前文件所在文件夹
            folder_path = self.file_path.parent
            current_file = self.file_path.name
            
            # 收集所有的地理数据文件
            geo_files = []
            for ext in ['.shp', '.gdb']:
                geo_files.extend(folder_path.glob(f'*{ext}'))
            
            # 存储找到的值
            field_values = {}
            value_frequencies = {}
            
            # 遍历其他文件
            for file_path in geo_files:
                if file_path.name == current_file:
                    continue
                
                try:
                    # 读取文件
                    if file_path.suffix.lower() == '.gdb':
                        gdf = gpd.read_file(file_path, driver='OpenFileGDB')
                    else:
                        # 尝试不同编码
                        for encoding in ['gbk', 'utf-8', 'gb2312']:
                            try:
                                gdf = gpd.read_file(file_path, encoding=encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                    
                    # 检查是否有相同字段
                    if self.field_name in gdf.columns:
                        # 获取非空值
                        valid_values = gdf[self.field_name].dropna().unique()
                        for value in valid_values:
                            if pd.notna(value) and str(value).strip():
                                str_value = str(value)
                                field_values[str_value] = field_values.get(str_value, 0) + 1
                                
                                # 记录来源文件
                                if str_value not in value_frequencies:
                                    value_frequencies[str_value] = set()
                                value_frequencies[str_value].add(file_path.name)
                
                except Exception as e:
                    logger.warning(f"读取文件 {file_path} 时出错: {e}")
                    continue
            
            # 分析值的模式
            self.analyze_field_patterns(field_values.keys())
            
            # 更新建议
            self.similar_field_values = field_values
            self.update_repair_suggestions(value_frequencies)
            
            self.status_var.set(f"扫描完成，找到 {len(field_values)} 个可能的值")
            
        except Exception as e:
            logger.error(f"扫描文件时出错: {e}")
            messagebox.showerror("错误", f"扫描文件时出错: {str(e)}")
            self.status_var.set("扫描失败")

    def analyze_field_patterns(self, values):
        """分析字段值的模式"""
        if not values:
            return
        
        patterns = {}
        for value in values:
            # 分析数字模式
            if str(value).replace('.', '').isdigit():
                patterns['numeric'] = patterns.get('numeric', 0) + 1
            
            # 分析日期模式
            if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', str(value)):
                patterns['date'] = patterns.get('date', 0) + 1
            
            # 分析编码模式（例如：XX-123）
            if re.search(r'^[A-Za-z]+-\d+$', str(value)):
                patterns['code'] = patterns.get('code', 0) + 1
            
            # 分析长度
            length = len(str(value))
            if length not in patterns.get('lengths', {}):
                patterns.setdefault('lengths', {})[length] = 0
            patterns['lengths'][length] += 1
        
        self.field_value_patterns = patterns

    def update_repair_suggestions(self, value_frequencies):
        """更新修复建议"""
        suggestions = []
        
        # 获取当前空值的行
        null_items = [item for item in self.tree.get_children()
                     if isinstance(self.tree.item(item), dict) and 'values' in self.tree.item(item) and len(self.tree.item(item)['values']) > 2 and self.tree.item(item)['values'][2] == '是']
        
        if not null_items:
            suggestions.append("当前没有需要修复的空值。")
        else:
            # 添加统计信息
            suggestions.append(f"发现 {len(null_items)} 个空值需要修复")
            suggestions.append("从其他文件中发现的可能值：")
            
            # 按出现频率排序
            sorted_values = sorted(self.similar_field_values.items(),
                                 key=lambda x: x[1],
                                 reverse=True)[:5]  # 只显示前5个最常见的值
            
            for value, count in sorted_values:
                files = value_frequencies[value]
                suggestions.append(f"• {value} (出现{count}次，在{len(files)}个文件中)")
            
            # 添加模式建议
            if self.field_value_patterns:
                suggestions.append("\n值的模式分析：")
                if self.field_value_patterns.get('numeric', 0) > 0:
                    suggestions.append("• 多为数值类型")
                if self.field_value_patterns.get('date', 0) > 0:
                    suggestions.append("• 包含日期格式")
                if self.field_value_patterns.get('code', 0) > 0:
                    suggestions.append("• 包含编码格式（如XX-123）")
                if 'lengths' in self.field_value_patterns:
                    common_length = max(self.field_value_patterns['lengths'].items(),
                                     key=lambda x: x[1])[0]
                    suggestions.append(f"• 常见长度为 {common_length} 个字符")
        
        # 更新建议文本
        if self.repair_text is not None:
            self.repair_text.config(state=tk.NORMAL)
            self.repair_text.delete('1.0', tk.END)
            self.repair_text.insert('1.0', '\n'.join(suggestions))
            self.repair_text.config(state=tk.DISABLED)

    def apply_repair_suggestions(self):
        """应用修复建议"""
        if not self.similar_field_values:
            messagebox.showwarning("警告", "请先扫描相似值")
            return
        
        # 获取空值项
        null_items = [item for item in self.tree.get_children()
                     if isinstance(self.tree.item(item), dict) and 'values' in self.tree.item(item) and len(self.tree.item(item)['values']) > 2 and self.tree.item(item)['values'][2] == '是']
        
        if not null_items:
            messagebox.showinfo("提示", "没有需要修复的空值")
            return
        
        # 创建修复对话框
        repair_dialog = tk.Toplevel(self.dialog)
        repair_dialog.title("应用修复建议")
        repair_dialog.geometry("500x400")
        repair_dialog.transient(self.dialog)
        repair_dialog.grab_set()
        
        # 创建表格
        columns = ('item_id', 'original', 'suggested')
        tree = ttk.Treeview(repair_dialog, columns=columns, show='headings')
        
        tree.heading('item_id', text='序号')
        tree.heading('original', text='原值')
        tree.heading('suggested', text='建议值')
        
        tree.column('item_id', width=80)
        tree.column('original', width=200)
        tree.column('suggested', width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(repair_dialog, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 获取最可能的值
        most_common = sorted(self.similar_field_values.items(),
                           key=lambda x: x[1],
                           reverse=True)[0][0]
        
        # 填充表格
        for item in null_items:
            values = self.tree.item(item)['values']
            tree.insert('', 'end', values=(values[0], '空值', most_common))
        
        # 添加按钮
        button_frame = ttk.Frame(repair_dialog)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def apply_repairs():
            for item in tree.get_children():
                values = tree.item(item)['values']
                item_id = values[0]
                suggested = values[2]
                # 更新主表格中的值
                for main_item in null_items:
                    main_item_data = self.tree.item(main_item)
                    if (isinstance(main_item_data, dict) and 'values' in main_item_data and
                        isinstance(main_item_data['values'], (list, tuple)) and len(main_item_data['values']) > 0 and main_item_data['values'][0] == item_id):
                        self.tree.set(main_item, 'value', suggested)
                        self.tree.set(main_item, 'is_null', '否')
                        break
            
            repair_dialog.destroy()
            self.update_statistics()
            self.status_var.set("已应用修复建议")
        
        ttk.Button(button_frame, text="应用全部", command=apply_repairs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=repair_dialog.destroy).pack(side=tk.RIGHT, padx=5) 

    def fill_common_value(self):
        """使用最常见值填充选中项"""
        try:
            if not self.data_patterns:
                messagebox.showwarning("警告", "未找到数据模式")
                return
            
            most_common_value = self.data_patterns.get('most_common_value')
            if not most_common_value:
                messagebox.showwarning("警告", "未找到常见值")
                return
            
            # 获取所有空值项
            null_items = [item for item in self.tree.get_children()
                         if isinstance(self.tree.item(item), dict) and 'values' in self.tree.item(item) and len(self.tree.item(item)['values']) > 2 and self.tree.item(item)['values'][2] == '是']
            
            if not null_items:
                messagebox.showinfo("提示", "没有需要填充的空值")
                return
            
            # 填充所有空值
            for item in null_items:
                self.tree.set(item, 'value', most_common_value)
                self.tree.set(item, 'is_null', '否')
            
            self.update_statistics()
            self.status_var.set(f"已填充 {len(null_items)} 个空值")
            
            # 调试日志
            logger.info(f"已用值 '{most_common_value}' 填充 {len(null_items)} 个空值")
            
        except Exception as e:
            logger.error(f"填充常见值时出错: {e}")
            messagebox.showerror("错误", f"填充值时出错: {str(e)}")

    def quick_fix(self):
        """一键修复"""
        try:
            if not self.data_patterns:
                messagebox.showwarning("提示", "没有可用的修复方案")
                return
            
            null_count = self.data_patterns.get('null_count', 0)
            has_pattern = self.data_patterns.get('has_pattern', False)
            
            if null_count == 0:
                messagebox.showinfo("提示", "没有需要修复的空值")
                return
            
            if not has_pattern:
                messagebox.showwarning("提示", "没有找到合适的填充值")
                return
            
            most_common_value = self.data_patterns.get('most_common_value')
            if not most_common_value:
                messagebox.showwarning("提示", "未找到有效的填充值")
                return
            
            # 获取所有空值项
            null_items = [item for item in self.tree.get_children()
                         if isinstance(self.tree.item(item), dict) and 'values' in self.tree.item(item) and len(self.tree.item(item)['values']) > 2 and self.tree.item(item)['values'][2] == '是']
            
            # 填充所有空值
            for item in null_items:
                self.tree.set(item, 'value', most_common_value)
                self.tree.set(item, 'is_null', '否')
                # 更新标签为已修复
                self.tree.item(item, tags=('fixed',))
            
            self.update_statistics()
            messagebox.showinfo("完成", f"已修复 {len(null_items)} 个空值")
            self.status_var.set(f"已修复 {len(null_items)} 个空值")
            
            # 更新建议
            self.analyze_data_patterns()
            
            # --- 同步表格内容到self.modified_data ---
            if self.modified_data is not None:
                for item in self.tree.get_children():
                    values = self.tree.item(item, 'values')
                    index = int(values[0]) - 1
                    value = values[1]
                    if value == "(空值)":
                        self.modified_data.loc[index, self.field_name] = None
                    else:
                        self.modified_data.loc[index, self.field_name] = value
            
        except Exception as e:
            logger.error(f"快速修复时出错: {e}", exc_info=True)
            messagebox.showerror("错误", "修复过程中出错")

    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.dialog, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_selected)
        self.context_menu.add_command(label="设为空值", command=self.set_null)
        self.context_menu.add_command(label="复制值", command=self.copy_value)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="一键修复", command=self.quick_fix)
        
        # 添加批量操作子菜单
        batch_menu = tk.Menu(self.context_menu, tearoff=0)
        self.context_menu.add_cascade(label="批量操作", menu=batch_menu)
        
        batch_menu.add_command(label="批量编辑", command=self.batch_edit_selected)
        batch_menu.add_command(label="批量验证", command=self.validate_selected)
        batch_menu.add_command(label="批量大写", command=lambda: self.batch_transform('upper'))
        batch_menu.add_command(label="批量小写", command=lambda: self.batch_transform('lower'))
        batch_menu.add_command(label="批量去空格", command=lambda: self.batch_transform('strip'))
        batch_menu.add_command(label="批量替换", command=self.batch_replace)

    def batch_transform(self, transform_type):
        """批量转换"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要处理的项")
            return
        
        count = 0
        for item in selected:
            item_data = self.tree.item(item)
            value = item_data.get('values')[1] if item_data else None
            if value is None or pd.isna(value) or value == "":
                continue
                
            if transform_type == 'upper':
                new_value = str(value).upper()
            elif transform_type == 'lower':
                new_value = str(value).lower()
            elif transform_type == 'strip':
                new_value = str(value).strip()
            
            if new_value != value:
                self.tree.set(item, 'value', new_value)
                count += 1
        
        if count > 0:
            self.update_statistics()
            self.status_var.set(f"已处理 {count} 个值")

    def batch_replace(self):
        """批量替换对话框"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("批量替换")
        dialog.geometry("400x200")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        # 查找和替换输入框
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="查找:").grid(row=0, column=0, sticky='w', pady=5)
        find_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=find_var).grid(row=0, column=1, sticky='ew', padx=5)
        
        ttk.Label(input_frame, text="替换为:").grid(row=1, column=0, sticky='w', pady=5)
        replace_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=replace_var).grid(row=1, column=1, sticky='ew', padx=5)
        
        input_frame.grid_columnconfigure(1, weight=1)
        
        # 选项
        options_frame = ttk.Frame(dialog)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="区分大小写", variable=case_sensitive_var).pack(side=tk.LEFT)
        
        whole_word_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="全字匹配", variable=whole_word_var).pack(side=tk.LEFT, padx=10)
        
        def do_replace():
            find_text = find_var.get()
            replace_text = replace_var.get()
            
            if not find_text:
                messagebox.showwarning("警告", "请输入要查找的文本")
                return
            
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("警告", "请先选择要处理的项")
                return
            
            count = 0
            for item in selected:
                item_data = self.tree.item(item)
                value = item_data.get('values')[1] if item_data else None
                if value is None or pd.isna(value) or value == "":
                    continue
                
                if not case_sensitive_var.get():
                    pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                else:
                    pattern = re.compile(re.escape(find_text))
                
                if whole_word_var.get():
                    pattern = re.compile(r'\b' + re.escape(find_text) + r'\b', 
                                      re.IGNORECASE if not case_sensitive_var.get() else 0)
                
                new_value = pattern.sub(replace_text, value)
                if new_value != value:
                    self.tree.set(item, 'value', new_value)
                    count += 1
            
            if count > 0:
                self.update_statistics()
                self.status_var.set(f"已替换 {count} 处")
                dialog.destroy()
            else:
                messagebox.showinfo("提示", "未找到匹配项")
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(button_frame, text="替换", command=do_replace).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5) 

    def get_field_standards(self):
        """获取字段标准信息"""
        try:
            from shp_field_checker_gui import DEFAULT_FIELD_STANDARDS
            return DEFAULT_FIELD_STANDARDS.get(self.field_name, {})
        except ImportError:
            return {} 

    def refresh_data(self, event=None):
        """刷新数据"""
        try:
            self.load_data()
            self.status_var.set("数据已刷新")
        except Exception as e:
            logger.error(f"刷新数据时出错: {e}")
            messagebox.showerror("错误", "刷新数据失败") 

    def show_export_dialog(self):
        """显示导出选项对话框"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("导出数据")
        dialog.geometry("400x300")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"400x300+{x}+{y}")
        
        # 导出选项
        options_frame = ttk.LabelFrame(dialog, text="导出选项")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 导出格式
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(format_frame, text="导出格式:").pack(side=tk.LEFT)
        format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(format_frame, text="CSV", variable=format_var, value="csv").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="Excel", variable=format_var, value="excel").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="JSON", variable=format_var, value="json").pack(side=tk.LEFT, padx=10)
        
        # 导出范围
        range_frame = ttk.Frame(options_frame)
        range_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(range_frame, text="导出范围:").pack(side=tk.LEFT)
        range_var = tk.StringVar(value="all")
        ttk.Radiobutton(range_frame, text="全部", variable=range_var, value="all").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(range_frame, text="选中项", variable=range_var, value="selected").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(range_frame, text="非空值", variable=range_var, value="non_null").pack(side=tk.LEFT, padx=10)
        
        # 包含列
        columns_frame = ttk.Frame(options_frame)
        columns_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(columns_frame, text="包含列:").pack(side=tk.LEFT)
        include_index_var = tk.BooleanVar(value=True)
        include_validation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(columns_frame, text="序号", variable=include_index_var).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(columns_frame, text="验证状态", variable=include_validation_var).pack(side=tk.LEFT, padx=10)
        
        # 其他选项
        other_frame = ttk.Frame(options_frame)
        other_frame.pack(fill=tk.X, padx=5, pady=5)
        include_header_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(other_frame, text="包含表头", variable=include_header_var).pack(side=tk.LEFT, padx=10)
        
        def do_export():
            try:
                # 获取要导出的数据
                data = []
                if range_var.get() == "all":
                    items = self.tree.get_children()
                elif range_var.get() == "selected":
                    items = self.tree.selection()
                else:  # non_null
                    items = [item for item in self.tree.get_children()
                            if self.tree.item(item)['values'][2] == '否']
                
                # 构建列
                columns = []
                if include_index_var.get():
                    columns.append("序号")
                columns.append("字段值")
                columns.append("是否为空")
                if include_validation_var.get():
                    columns.append("验证状态")
                
                # 收集数据
                for item in items:
                    values = self.tree.item(item)['values']
                    row = {}
                    if include_index_var.get():
                        row["序号"] = values[0]
                    row["字段值"] = values[1]
                    row["是否为空"] = values[2]
                    if include_validation_var.get() and len(values) > 3:
                        row["验证状态"] = values[3]
                    data.append(row)
                
                # 选择保存路径
                file_types = {
                    "csv": ("CSV文件", "*.csv"),
                    "excel": ("Excel文件", "*.xlsx"),
                    "json": ("JSON文件", "*.json")
                }
                file_type = file_types[format_var.get()]
                file_path = filedialog.asksaveasfilename(
                    defaultextension=f".{format_var.get()}",
                    filetypes=[file_type, ("所有文件", "*.*")]
                )
                
                if not file_path:
                    return
                
                # 导出数据
                if format_var.get() == "csv":
                    with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=columns)
                        if include_header_var.get():
                            writer.writeheader()
                        writer.writerows(data)
                
                elif format_var.get() == "excel":
                    df = pd.DataFrame(data)
                    if not include_header_var.get():
                        df.to_excel(file_path, index=False, header=False)
                    else:
                        df.to_excel(file_path, index=False)
                
                else:  # json
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", "数据导出完成")
                dialog.destroy()
                
            except Exception as e:
                logger.error(f"导出数据时出错: {e}")
                messagebox.showerror("错误", f"导出失败: {str(e)}")
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(button_frame, text="导出", command=do_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5) 