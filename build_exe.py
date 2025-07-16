#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理数据质检工具 - 打包脚本
使用PyInstaller打包为exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
        return True
    except ImportError:
        print("❌ PyInstaller未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.0.0"])
            print("✅ PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError:
            print("❌ PyInstaller安装失败")
            return False

def create_spec_file():
    """创建PyInstaller配置文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['shp_field_checker_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('encoding_fix_utils.py', '.'),
        ('field_editor_dialog.py', '.'),
        ('pandastable_field_config.py', '.'),
    ],
    hiddenimports=[
        'geopandas',
        'fiona',
        'shapely',
        'pyproj',
        'pandas',
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib.format',
        'numpy.random',
        'numpy.random.common',
        'numpy.random.bounded_integers',
        'numpy.random.entropy',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'openpyxl',
        'xlrd',
        'docx',
        'python-docx',
        'pandastable',
        'encoding_fix_utils',
        'field_editor_dialog',
        'pandastable_field_config',
        'PIL',
        'PIL.Image',
        'scipy',
        'scipy.spatial',
        'scipy.spatial.distance',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
        'test',
        'tests',
        'distutils',
        'setuptools',
        'numpy.tests',
        'pandas.tests',
        'geopandas.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤掉numpy源代码目录
a.binaries = [x for x in a.binaries if not x[0].startswith('numpy\\')]
a.datas = [x for x in a.datas if not (x[0].startswith('numpy\\') and x[0].endswith('.py'))]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='地理数据质检工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='favicon.ico' if os.path.exists('favicon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='地理数据质检工具',
)
'''
    
    with open('地理数据质检工具.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 创建配置文件: 地理数据质检工具.spec")

def create_version_info():
    """创建版本信息文件"""
    version_info = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'ViVi141'),
        StringStruct(u'FileDescription', u'地理数据质检工具 - 专业的地理数据质量检查工具'),
        StringStruct(u'FileVersion', u'2.0.0.0'),
        StringStruct(u'InternalName', u'地理数据质检工具'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2025 ViVi141'),
        StringStruct(u'OriginalFilename', u'地理数据质检工具.exe'),
        StringStruct(u'ProductName', u'地理数据质检工具'),
        StringStruct(u'ProductVersion', u'2.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    
    print("✅ 创建版本信息文件: version_info.txt")

def build_exe():
    """执行打包"""
    print("🚀 开始打包exe文件...")
    
    # 检查PyInstaller
    if not check_pyinstaller():
        return False
    
    # 创建配置文件
    create_spec_file()
    create_version_info()
    
    # 清理之前的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # 执行打包
    try:
        cmd = [
            'pyinstaller',
            '--clean',
            '--noconfirm',
            '地理数据质检工具.spec'
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ 打包成功!")
        print(f"输出目录: {os.path.abspath('dist')}")
        
        # 检查生成的文件
        dist_dir = Path('dist')
        if dist_dir.exists():
            exe_files = list(dist_dir.glob('*.exe'))
            if exe_files:
                print(f"✅ 生成的exe文件: {exe_files[0].name}")
                print(f"文件大小: {exe_files[0].stat().st_size / (1024*1024):.1f} MB")
            else:
                print("❌ 未找到生成的exe文件")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 打包过程中出现错误: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("地理数据质检工具 - 打包脚本")
    print("=" * 50)
    
    # 检查必要文件
    required_files = [
        'shp_field_checker_gui.py',
        'encoding_fix_utils.py',
        'field_editor_dialog.py',
        'pandastable_field_config.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {missing_files}")
        return False
    
    print("✅ 所有必要文件检查通过")
    
    # 执行打包
    if build_exe():
        print("\n🎉 打包完成!")
        print("\n使用说明:")
        print("1. 生成的exe文件在 dist/ 目录中")
        print("2. 可以直接运行exe文件，无需安装Python")
        print("3. 建议在目标机器上测试exe文件")
        print("4. 如有问题，请检查依赖库是否正确包含")
    else:
        print("\n❌ 打包失败，请检查错误信息")

if __name__ == "__main__":
    main() 