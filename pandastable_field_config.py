import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import json
from pandastable import Table, TableModel
import platform

# 字体配置函数
def configure_system_fonts():
    """配置系统字体"""
    try:
        from tkinter import font
        
        # 根据操作系统选择合适的系统字体
        system = platform.system()
        if system == "Windows":
            # Windows系统字体
            default_font_name = "Microsoft YaHei UI"  # 微软雅黑UI
            text_font_name = "Consolas"  # 等宽字体用于代码显示
        elif system == "Darwin":  # macOS
            default_font_name = "PingFang SC"
            text_font_name = "Menlo"
        else:  # Linux
            default_font_name = "DejaVu Sans"
            text_font_name = "DejaVu Sans Mono"
        
        # 配置默认字体
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family=default_font_name, size=9)
        
        # 配置文本字体
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family=text_font_name, size=9)
        
        # 配置固定宽度字体
        fixed_font = font.nametofont("TkFixedFont")
        fixed_font.configure(family=text_font_name, size=9)
        
        return True
        
    except Exception as e:
        print(f"字体配置失败: {e}")
        return False

class FieldConfigPandasTable:
    def __init__(self, master=None, default_standards=None, critical_files_config=None):
        self.default_data = default_standards if default_standards else {
            "BSM": {"字段别名": "标识码", "字段类型": "Integer", "必填": True, "唯一": False, "字段长度": ""},
            "YSDM": {"字段别名": "要素代码", "字段类型": "Text", "必填": True, "唯一": False, "字段长度": ""},
            "TBBH": {"字段别名": "图斑编号", "字段类型": "Text", "必填": True, "唯一": False, "字段长度": ""}
        }
        
        # 默认重要文件配置
        self.default_critical_files = critical_files_config if critical_files_config else {
            "GHMC": ["YDFW", "GHJX"],  # 规划名称字段在YDFW或GHJX文件中为不可忽略
            "PFDATE": ["YDFW", "GHJX"]  # 批准日期字段在YDFW或GHJX文件中为不可忽略
        }
        
        self.root = tk.Toplevel(master) if master else tk.Tk()
        self.root.title("字段配置表格 v1.1 - 支持重要文件配置")
        self.root.geometry("1200x750")
        
        # 配置系统字体
        configure_system_fonts()
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.init_data()
        self.setup_ui()
        self.load_default_data()

    def init_data(self):
        self.df = pd.DataFrame({
            "字段名称": [],
            "字段别名": [],
            "字段类型": [],
            "必填": [],
            "唯一": [],
            "字段长度": []
        })
        
        # 重要文件配置DataFrame
        self.critical_files_df = pd.DataFrame({
            "字段名称": [],
            "重要文件模式": [],
            "说明": []
        })
        
        # 定义字段类型的下拉列表选项，扩展更多类型
        self.field_types = ["Text", "Integer", "Double", "Date", "Boolean", "Float", "Long", "Short", "Binary", "Time", "Timestamp", "Decimal", "Object", "Geometry"]

    def setup_ui(self):
        # 创建Notebook用于分页显示
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 第一页：字段标准配置
        field_frame = ttk.Frame(notebook)
        notebook.add(field_frame, text="字段标准配置")
        self.setup_field_config_ui(field_frame)
        
        # 第二页：重要文件配置
        critical_frame = ttk.Frame(notebook)
        notebook.add(critical_frame, text="重要文件配置")
        self.setup_critical_files_ui(critical_frame)
        
    def setup_field_config_ui(self, parent):
        """设置字段标准配置UI"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Button(button_frame, text="添加字段", command=self.add_field).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中行", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="新建配置", command=self.new_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="重置默认", command=self.reset_to_default).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=self.root.destroy).pack(side=tk.RIGHT)

        table_frame = tk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 创建表格
        self.table = Table(table_frame, dataframe=self.df, showtoolbar=True, showstatusbar=True)
        self.table.show()
        
        # 设置表格格式
        try:
            self.table.autoResizeColumns()
        except:
            pass
        try:
            self.table.setRowHeight(28)
        except:
            pass
            
        # 设置下拉菜单格式 - 在表格创建后立即设置
        self.setup_dropdowns()
        
    def setup_critical_files_ui(self, parent):
        """设置重要文件配置UI"""
        # 说明标签
        info_label = ttk.Label(parent, text="配置哪些字段在特定文件中为不可忽略错误", 
                              font=("Arial", 10, "bold"))
        info_label.pack(pady=(10, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Button(button_frame, text="添加重要文件规则", command=self.add_critical_file_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中规则", command=self.delete_critical_file_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="重置默认", command=self.reset_critical_files).pack(side=tk.LEFT, padx=(0, 5))

        # 表格框架
        table_frame = tk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        # 创建重要文件配置表格
        self.critical_files_table = Table(table_frame, dataframe=self.critical_files_df, showtoolbar=True, showstatusbar=True)
        self.critical_files_table.show()
        
        # 设置表格格式
        try:
            self.critical_files_table.autoResizeColumns()
        except:
            pass
        try:
            self.critical_files_table.setRowHeight(28)
        except:
            pass
            
        # 加载默认重要文件配置
        self.load_critical_files_data()
        
    def setup_dropdowns(self):
        """设置下拉菜单"""
        try:
            # 绑定单击事件
            self.table.bind('<ButtonRelease-1>', self.on_cell_click)
            print("下拉菜单事件绑定完成")
        except Exception as e:
            print(f"设置下拉菜单时出错: {e}")

    def on_cell_click(self, event):
        """单元格点击事件处理"""
        try:
            # 使用pandastable的方法获取点击的行列
            row = self.table.get_row_clicked(event)
            col = self.table.get_col_clicked(event)
            
            if row is not None and col is not None:
                # 获取列名
                col_name = self.table.model.df.columns[col]
                print(f"点击了列: {col_name}, 行: {row}")
                
                # 根据列名显示相应的下拉选择
                if col_name == "字段类型":
                    self.show_type_dropdown(event.x_root, event.y_root, row)
                elif col_name in ["必填", "唯一"]:
                    self.show_yes_no_dropdown(event.x_root, event.y_root, row, col_name)
                    
        except Exception as e:
            print(f"单元格点击事件处理失败: {e}")
    
    def show_type_dropdown(self, x, y, row):
        """显示字段类型下拉选择"""
        try:
            # 创建下拉选择窗口
            dropdown = tk.Toplevel(self.root)
            dropdown.geometry(f"+{x}+{y}")
            dropdown.overrideredirect(True)
            dropdown.configure(bg='white', relief='solid', bd=1)
            
            # 创建列表框
            listbox = tk.Listbox(dropdown, height=min(len(self.field_types), 8), 
                                bg='white', relief='solid', bd=1)
            for field_type in self.field_types:
                listbox.insert(tk.END, field_type)
            
            listbox.pack()
            
            def on_select(event):
                selection = listbox.curselection()
                if selection:
                    selected_type = listbox.get(selection[0])
                    print(f"选择了字段类型: {selected_type}")
                    # 更新表格中的值
                    self.df.iloc[row, 2] = selected_type  # 字段类型是第3列
                    self.table.updateModel(TableModel(self.df))
                    self.table.redraw()
                dropdown.destroy()
            
            def on_escape(event):
                dropdown.destroy()
            
            listbox.bind('<Double-1>', on_select)
            listbox.bind('<Return>', on_select)
            dropdown.bind('<Escape>', on_escape)
            
            # 设置焦点
            listbox.focus_set()
            listbox.selection_set(0)
            
            print("字段类型下拉菜单已显示")
            
        except Exception as e:
            print(f"显示字段类型下拉失败: {e}")
    
    def show_yes_no_dropdown(self, x, y, row, col_name):
        """显示是/否下拉选择"""
        try:
            # 创建下拉选择窗口
            dropdown = tk.Toplevel(self.root)
            dropdown.geometry(f"+{x}+{y}")
            dropdown.overrideredirect(True)
            dropdown.configure(bg='white', relief='solid', bd=1)
            
            # 创建列表框
            listbox = tk.Listbox(dropdown, height=2, bg='white', relief='solid', bd=1)
            listbox.insert(tk.END, "是")
            listbox.insert(tk.END, "否")
            
            listbox.pack()
            
            def on_select(event):
                selection = listbox.curselection()
                if selection:
                    selected_value = listbox.get(selection[0])
                    print(f"选择了{col_name}: {selected_value}")
                    # 更新表格中的值
                    col_index = 3 if col_name == "必填" else 4  # 必填是第4列，唯一是第5列
                    self.df.iloc[row, col_index] = selected_value
                    self.table.updateModel(TableModel(self.df))
                    self.table.redraw()
                dropdown.destroy()
            
            def on_escape(event):
                dropdown.destroy()
            
            listbox.bind('<Double-1>', on_select)
            listbox.bind('<Return>', on_select)
            dropdown.bind('<Escape>', on_escape)
            
            # 设置焦点
            listbox.focus_set()
            listbox.selection_set(0)
            
            print(f"{col_name}下拉菜单已显示")
            
        except Exception as e:
            print(f"显示是/否下拉失败: {e}")

    def load_default_data(self):
        data = []
        for field_name, config in self.default_data.items():
            data.append([
                field_name,
                config.get("字段别名", ""),
                config.get("字段类型", "Text"),
                "是" if config.get("必填", False) else "否",
                "是" if config.get("唯一", False) else "否",
                str(config.get("字段长度", ""))
            ])
        self.df = pd.DataFrame(data)
        self.df.columns = ["字段名称", "字段别名", "字段类型", "必填", "唯一", "字段长度"]
        self.table.updateModel(TableModel(self.df))
        self.table.redraw()
        
        # 重新设置下拉菜单
        self.setup_dropdowns()

    def add_field(self):
        existing_fields = self.df["字段名称"].tolist()
        base_name = "NEW_FIELD"
        counter = 1
        new_field_name = f"{base_name}_{counter}"
        while new_field_name in existing_fields:
            counter += 1
            new_field_name = f"{base_name}_{counter}"
        new_row = pd.DataFrame([[new_field_name, "", "Text", "否", "否", ""]], columns=self.df.columns)
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.table.updateModel(TableModel(self.df))
        self.table.redraw()
        try:
            self.table.setSelectedRow(len(self.df) - 1)
        except:
            pass

    def delete_selected(self):
        selected = self.table.getSelectedRow()
        if selected is None:
            messagebox.showwarning("警告", "请先选择要删除的行")
            return
        field_name = self.df.iloc[selected]["字段名称"]
        if messagebox.askyesno("确认删除", f"确定要删除字段 '{field_name}' 吗？"):
            self.df = self.df.drop(selected).reset_index(drop=True)
            self.table.updateModel(TableModel(self.df))
            self.table.redraw()

    def save_config(self):
        try:
            # 准备字段配置数据
            field_config_data = {}
            for _, row in self.df.iterrows():
                field_name = row["字段名称"]
                field_config_data[field_name] = {
                    "字段别名": row["字段别名"],
                    "字段类型": row["字段类型"],
                    "必填": row["必填"] == "是",
                    "唯一": row["唯一"] == "是",
                    "字段长度": int(row["字段长度"]) if str(row["字段长度"]).strip() else None
                }
            
            # 准备重要文件配置数据
            critical_files_config = self.get_critical_files_config()
            
            # 组合完整配置
            complete_config = {
                "field_standards": field_config_data,
                "critical_files": critical_files_config,
                "version": "1.1"
            }
            
            filename = filedialog.asksaveasfilename(defaultextension=".json",
                                                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(complete_config, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"配置已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def load_config(self):
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 处理不同版本的配置文件
                if isinstance(config_data, dict) and "field_standards" in config_data:
                    # 新版本配置文件（包含重要文件配置）
                    field_config_data = config_data.get("field_standards", {})
                    critical_files_config = config_data.get("critical_files", {})
                    
                    # 更新重要文件配置
                    if critical_files_config:
                        self.default_critical_files = critical_files_config
                        self.load_critical_files_data()
                    
                else:
                    # 旧版本配置文件（只有字段配置）
                    field_config_data = config_data
                
                # 预览字段
                preview = "\n".join(list(field_config_data.keys()))
                if not messagebox.askyesno("预览字段", f"即将加载以下字段：\n{preview}\n\n是否继续？"):
                    return
                
                # 加载字段配置
                data = []
                for field_name, config in field_config_data.items():
                    data.append([
                        field_name,
                        config.get("字段别名", ""),
                        config.get("字段类型", "Text"),
                        "是" if config.get("必填", False) else "否",
                        "是" if config.get("唯一", False) else "否",
                        str(config.get("字段长度", "")) if config.get("字段长度") else ""
                    ])
                self.df = pd.DataFrame(data)
                self.df.columns = ["字段名称", "字段别名", "字段类型", "必填", "唯一", "字段长度"]
                self.table.updateModel(TableModel(self.df))
                self.table.redraw()
                messagebox.showinfo("成功", f"已加载配置: {filename}\n共{len(self.df)}个字段")
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {str(e)}")

    def reset_to_default(self):
        if messagebox.askyesno("确认重置", "确定要重置为默认配置吗？这将删除所有自定义字段。"):
            self.load_default_data()
            messagebox.showinfo("成功", f"已重置为默认配置，共{len(self.df)}个字段")

    def new_config(self):
        """新建空白配置文件"""
        if messagebox.askyesno("确认新建", "确定要创建新的空白配置文件吗？这将清空当前所有字段。"):
            # 清空DataFrame
            self.df = pd.DataFrame({
                "字段名称": [],
                "字段别名": [],
                "字段类型": [],
                "必填": [],
                "唯一": [],
                "字段长度": []
            })
            self.table.updateModel(TableModel(self.df))
            self.table.redraw()
            print("已创建空白配置文件")
            # 明确保持窗口打开
            self.root.focus_force()

    def get_field_config(self):
        """获取字段配置（兼容旧版本）"""
        config_data = {}
        for _, row in self.df.iterrows():
            field_name = row["字段名称"]
            config_data[field_name] = {
                "字段别名": row["字段别名"],
                "字段类型": row["字段类型"],
                "必填": row["必填"] == "是",
                "唯一": row["唯一"] == "是",
                "字段长度": int(row["字段长度"]) if str(row["字段长度"]).strip() else None
            }
        return config_data
        
    def get_complete_config(self):
        """获取完整配置（包含重要文件配置）"""
        return {
            "field_standards": self.get_field_config(),
            "critical_files": self.get_critical_files_config(),
            "version": "1.1"
        }

    def add_critical_file_rule(self):
        """添加重要文件规则"""
        try:
            # 创建输入对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("添加重要文件规则")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (200 // 2)
            dialog.geometry(f"400x200+{x}+{y}")
            
            # 创建输入框架
            input_frame = ttk.Frame(dialog, padding="10")
            input_frame.pack(fill=tk.BOTH, expand=True)
            
            # 字段名称输入
            ttk.Label(input_frame, text="字段名称:").pack(anchor=tk.W)
            field_entry = ttk.Entry(input_frame, width=40)
            field_entry.pack(fill=tk.X, pady=(0, 10))
            
            # 重要文件模式输入
            ttk.Label(input_frame, text="重要文件模式 (用逗号分隔):").pack(anchor=tk.W)
            pattern_entry = ttk.Entry(input_frame, width=40)
            pattern_entry.pack(fill=tk.X, pady=(0, 10))
            pattern_entry.insert(0, "例如: YDFW,GHJX")
            
            # 说明输入
            ttk.Label(input_frame, text="说明:").pack(anchor=tk.W)
            desc_entry = ttk.Entry(input_frame, width=40)
            desc_entry.pack(fill=tk.X, pady=(0, 10))
            
            def on_ok():
                field_name = field_entry.get().strip()
                patterns = [p.strip() for p in pattern_entry.get().split(',') if p.strip()]
                description = desc_entry.get().strip()
                
                if field_name and patterns:
                    # 添加到DataFrame
                    new_row = pd.DataFrame([[field_name, ','.join(patterns), description]], 
                                          columns=self.critical_files_df.columns)
                    self.critical_files_df = pd.concat([self.critical_files_df, new_row], ignore_index=True)
                    self.critical_files_table.updateModel(TableModel(self.critical_files_df))
                    self.critical_files_table.redraw()
                    dialog.destroy()
                else:
                    messagebox.showwarning("警告", "请填写字段名称和文件模式")
            
            def on_cancel():
                dialog.destroy()
            
            # 按钮框架
            button_frame = ttk.Frame(input_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
            
        except Exception as e:
            print(f"添加重要文件规则失败: {e}")
            messagebox.showerror("错误", f"添加规则失败: {e}")
            
    def delete_critical_file_rule(self):
        """删除重要文件规则"""
        try:
            selected = self.critical_files_table.getSelectedRow()
            if selected is None:
                messagebox.showwarning("警告", "请先选择要删除的规则")
                return
                
            field_name = self.critical_files_df.iloc[selected]["字段名称"]
            if messagebox.askyesno("确认删除", f"确定要删除规则 '{field_name}' 吗？"):
                self.critical_files_df = self.critical_files_df.drop(selected).reset_index(drop=True)
                self.critical_files_table.updateModel(TableModel(self.critical_files_df))
                self.critical_files_table.redraw()
                
        except Exception as e:
            print(f"删除重要文件规则失败: {e}")
            messagebox.showerror("错误", f"删除规则失败: {e}")
            
    def reset_critical_files(self):
        """重置重要文件配置为默认值"""
        if messagebox.askyesno("确认重置", "确定要重置重要文件配置为默认值吗？"):
            self.load_critical_files_data()
            
    def load_critical_files_data(self):
        """加载重要文件配置数据"""
        try:
            data = []
            for field_name, patterns in self.default_critical_files.items():
                data.append([
                    field_name,
                    ','.join(patterns),
                    f"{field_name}字段在{','.join(patterns)}文件中为不可忽略"
                ])
            
            self.critical_files_df = pd.DataFrame(data, columns=["字段名称", "重要文件模式", "说明"])
            self.critical_files_table.updateModel(TableModel(self.critical_files_df))
            self.critical_files_table.redraw()
            
        except Exception as e:
            print(f"加载重要文件配置失败: {e}")
            
    def get_critical_files_config(self):
        """获取重要文件配置"""
        config = {}
        for _, row in self.critical_files_df.iterrows():
            field_name = row["字段名称"]
            patterns = [p.strip() for p in row["重要文件模式"].split(',') if p.strip()]
            if patterns:
                config[field_name] = patterns
        return config

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    FieldConfigPandasTable().run() 