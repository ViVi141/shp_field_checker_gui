@echo off
echo 正在升级版本到2.0...
echo.

REM 检查git是否可用
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到git命令，请确保已安装git
    pause
    exit /b 1
)

REM 检查是否有未提交的更改
git status --porcelain
if %errorlevel% equ 0 (
    echo 检测到未提交的更改，正在添加文件...
    git add .
    
    echo 提交版本升级到2.0...
    git commit -m "版本升级到2.0 - 修复书名号显示问题，优化编码处理，修复语法错误"
    
    echo.
    echo 版本升级完成！
    echo.
    echo ========================================
    echo v2.0 相比v1.0的主要更新内容：
    echo ========================================
    echo.
    echo 🎯 核心功能增强:
    echo - GDB格式支持（从v1.1继承）
    echo - 多图层处理（从v1.1继承）
    echo - Unicode字符支持（书名号、引号等）
    echo.
    echo 🔧 技术优化:
    echo - 编码处理优化
    echo - 语法错误修复
    echo - 显示效果优化
    echo.
    echo 🐛 问题修复:
    echo - 修复书名号（《》）显示问题
    echo - 修复重复导入问题
    echo - 解决字符显示异常
    echo.
    echo 当前版本: v2.0 正式版
    echo 更新时间: 2025年1月15日
    echo.
    echo 相比v1.0，v2.0新增了GDB支持、Unicode字符支持、
    echo 并修复了所有语法错误和显示问题。
) else (
    echo 没有检测到需要提交的更改
)

echo.
pause 