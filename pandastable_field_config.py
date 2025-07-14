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
    def __init__(self, master=None, default_standards=None):
        self.default_data = default_standards if default_standards else {
            "BSM": {"字段别名": "标识码", "字段类型": "Integer", "必填": True, "唯一": False, "字段长度": ""},
            "YSDM": {"字段别名": "要素代码", "字段类型": "Text", "必填": True, "唯一": False, "字段长度": ""},
            "TBBH": {"字段别名": "图斑编号", "字段类型": "Text", "必填": True, "唯一": False, "字段长度": ""}
        }
        self.root = tk.Toplevel(master) if master else tk.Tk()
        self.root.title("字段配置表格 v1.0 - PandasTable美化版")
        self.root.geometry("1100x650")
        
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

    def setup_ui(self):
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Button(button_frame, text="添加字段", command=self.add_field).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中行", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="新建配置", command=self.new_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="重置默认", command=self.reset_to_default).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=self.root.destroy).pack(side=tk.RIGHT)

        table_frame = tk.Frame(self.main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.table = Table(table_frame, dataframe=self.df, showtoolbar=True, showstatusbar=True)
        self.table.show()
        try:
            self.table.autoResizeColumns()
        except:
            pass
        try:
            self.table.setRowHeight(28)
        except:
            pass

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
            filename = filedialog.asksaveasfilename(defaultextension=".json",
                                                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"配置已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def load_config(self):
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                preview = "\n".join(list(config_data.keys()))
                if not messagebox.askyesno("预览字段", f"即将加载以下字段：\n{preview}\n\n是否继续？"):
                    return
                data = []
                for field_name, config in config_data.items():
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
            messagebox.showinfo("成功", "已创建空白配置文件，请添加字段")

    def get_field_config(self):
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

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    FieldConfigPandasTable().run() 