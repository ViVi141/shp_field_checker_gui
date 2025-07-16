#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段编辑弹窗
支持直接在GUI中编辑字段数据并保存回原文件
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging
import warnings

# 抑制编码转换警告
warnings.filterwarnings('ignore', category=UserWarning, module='fiona')
warnings.filterwarnings('ignore', category=UserWarning, module='geopandas')
warnings.filterwarnings('ignore', category=UserWarning, module='pyogrio')
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
        
        Args:
            parent: 父窗口
            file_path: 文件路径
            field_name: 字段名
            layer_name: 图层名（GDB文件使用）
        """
        self.parent = parent
        self.file_path = Path(file_path)
        self.field_name = field_name
        self.layer_name = layer_name
        self.original_data = None
        self.modified_data = None
        
        # 创建弹窗
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"编辑字段: {field_name}")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 设置弹窗位置为屏幕中心
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"800x600+{x}+{y}")
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """设置界面"""
        # 标题
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(title_frame, text=f"文件: {self.file_path.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        if self.layer_name:
            ttk.Label(title_frame, text=f"图层: {self.layer_name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(title_frame, text=f"字段: {self.field_name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 工具栏
        toolbar_frame = ttk.Frame(self.dialog)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(toolbar_frame, text="保存修改", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="撤销修改", command=self.revert_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 创建表格
        self.create_table()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=2)
    
    def create_table(self):
        """创建表格"""
        # 表格框架
        table_frame = ttk.Frame(self.dialog)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview作为表格
        columns = ('index', 'value', 'is_null')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        # 设置列标题
        self.tree.heading('index', text='序号')
        self.tree.heading('value', text='字段值')
        self.tree.heading('is_null', text='是否为空')
        
        # 设置列宽
        self.tree.column('index', width=80)
        self.tree.column('value', width=400)
        self.tree.column('is_null', width=100)
        
        # 添加滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击编辑事件
        self.tree.bind('<Double-1>', self.on_double_click)
        
        # 右键菜单
        self.context_menu = tk.Menu(self.dialog, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_selected)
        self.context_menu.add_command(label="设为空值", command=self.set_null)
        self.context_menu.add_command(label="复制值", command=self.copy_value)
        
        self.tree.bind('<Button-3>', self.show_context_menu)
    
    def load_data(self):
        """加载数据"""
        try:
            self.status_var.set("正在加载数据...")
            self.dialog.update()
            
            # 读取文件
            if self.file_path.suffix.lower() == '.gdb':
                # GDB文件
                gdf = gpd.read_file(self.file_path, driver='OpenFileGDB')
                if isinstance(gdf, gpd.GeoDataFrame):
                    # 单个图层
                    data = gdf
                else:
                    # 多个图层，需要根据图层名选择
                    if self.layer_name:
                        # 这里需要根据图层名获取数据
                        # 简化处理，假设是第一个图层
                        data = gdf[0] if isinstance(gdf, list) else gdf
                    else:
                        data = gdf[0] if isinstance(gdf, list) else gdf
            else:
                # SHP/DBF文件 - 优先使用GBK编码，避免多次尝试
                data = None
                success_encoding = None
                
                # 首先尝试GBK编码（最常见的中文编码）
                try:
                    data = gpd.read_file(self.file_path, encoding='gbk')
                    success_encoding = 'gbk'
                    logger.info(f"成功使用GBK编码读取文件: {self.file_path}")
                except UnicodeDecodeError:
                    # 如果GBK失败，尝试其他编码
                    encodings = ['gb2312', 'utf-8', 'latin1', 'cp936']
                    for encoding in encodings:
                        try:
                            data = gpd.read_file(self.file_path, encoding=encoding)
                            success_encoding = encoding
                            logger.info(f"成功使用编码 {encoding} 读取文件: {self.file_path}")
                            break
                        except UnicodeDecodeError:
                            continue
                        except Exception as e:
                            logger.warning(f"使用编码 {encoding} 读取失败: {e}")
                            continue
                
                # 如果所有编码都失败，尝试使用错误处理
                if data is None:
                    try:
                        data = gpd.read_file(self.file_path, encoding='gbk', errors='replace')
                        success_encoding = 'gbk (with errors)'
                        logger.warning(f"使用GBK编码（错误替换模式）读取文件: {self.file_path}")
                    except Exception as e:
                        logger.error(f"所有编码尝试都失败: {e}")
                        raise
                
                if data is None:
                    # 如果所有编码都失败，使用默认方式
                    data = gpd.read_file(self.file_path)
                    success_encoding = 'default'
                    logger.warning(f"使用默认编码读取文件: {self.file_path}")
            
            # 获取字段数据并立即刷新显示
            if self.field_name in data.columns:
                field_data = data[self.field_name]
                
                # 在数据层面修复乱码
                if field_data.dtype == 'object':
                    # 对字符串类型的字段应用乱码修复
                    field_data = field_data.apply(lambda x: fix_garbled_text(x) if pd.notna(x) else x)
                    # 更新数据框中的字段
                    data[self.field_name] = field_data
                
                self.original_data = data.copy()
                self.modified_data = data.copy()
                
                # 立即刷新表格显示
                self.populate_table(field_data)
                self.dialog.update()  # 强制刷新界面
                
                # 更新状态信息
                encoding_info = f" (编码: {success_encoding})" if 'success_encoding' in locals() else ""
                self.status_var.set(f"已加载 {len(field_data)} 条记录{encoding_info}")
            else:
                messagebox.showerror("错误", f"字段 '{self.field_name}' 不存在于文件中")
                self.dialog.destroy()
                
        except Exception as e:
            messagebox.showerror("错误", f"加载数据失败: {str(e)}")
            logger.error(f"加载数据失败: {e}")
            self.dialog.destroy()
    
    def populate_table(self, field_data):
        """填充表格数据"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加数据
        for i, value in enumerate(field_data):
            is_null = "是" if pd.isna(value) else "否"
            
            # 先修复乱码，再修复特殊字符，最后处理显示值
            fixed_value = fix_garbled_text(value)
            fixed_value = fix_special_chars_for_display(fixed_value)
            display_value = clean_text_for_display(fixed_value)
            
            self.tree.insert('', 'end', values=(i+1, display_value, is_null), tags=(str(i),))
    
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
            if new_value == "":
                self.modified_data.loc[index, self.field_name] = None
            else:
                self.modified_data.loc[index, self.field_name] = new_value
            
            edit_dialog.destroy()
            self.status_var.set("已修改，请点击保存")
        
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
            self.modified_data.loc[index, self.field_name] = None
            
            self.status_var.set("已设为空值，请点击保存")
    
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
            if self.original_data.equals(self.modified_data):
                messagebox.showinfo("提示", "没有修改需要保存")
                return
            
            # 保存文件
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
            self.original_data = self.modified_data.copy()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            logger.error(f"保存失败: {e}")
            self.status_var.set("保存失败")
    
    def revert_changes(self):
        """撤销修改"""
        if messagebox.askyesno("确认", "确定要撤销所有修改吗？"):
            self.modified_data = self.original_data.copy()
            self.populate_table(self.modified_data[self.field_name])
            self.status_var.set("已撤销修改")
    
    def run(self):
        """运行弹窗"""
        self.dialog.wait_window()
        return self.modified_data is not None and not self.original_data.equals(self.modified_data) 