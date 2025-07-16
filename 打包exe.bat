@echo off
chcp 65001 >nul
echo ========================================
echo 地理数据质检工具 - 打包脚本
echo ========================================
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请确保已安装Python并添加到PATH
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

REM 检查必要文件
if not exist "shp_field_checker_gui.py" (
    echo ❌ 错误: 缺少主程序文件 shp_field_checker_gui.py
    pause
    exit /b 1
)

if not exist "encoding_fix_utils.py" (
    echo ❌ 错误: 缺少编码工具文件 encoding_fix_utils.py
    pause
    exit /b 1
)

if not exist "field_editor_dialog.py" (
    echo ❌ 错误: 缺少字段编辑文件 field_editor_dialog.py
    pause
    exit /b 1
)

if not exist "pandastable_field_config.py" (
    echo ❌ 错误: 缺少字段配置文件 pandastable_field_config.py
    pause
    exit /b 1
)

echo ✅ 所有必要文件检查通过
echo.

REM 安装PyInstaller（如果需要）
echo 检查PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装PyInstaller...
    pip install pyinstaller>=5.0.0
    if %errorlevel% neq 0 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
    echo ✅ PyInstaller安装成功
) else (
    echo ✅ PyInstaller已安装
)

echo.
echo 🚀 开始打包exe文件...
echo 这可能需要几分钟时间，请耐心等待...
echo.

REM 执行打包
python build_exe.py

if %errorlevel% equ 0 (
    echo.
    echo 🎉 打包完成！
    echo.
    echo 📁 生成的文件位置:
    echo    dist/地理数据质检工具.exe
    echo.
    echo 📋 使用说明:
    echo    1. 生成的exe文件可以直接运行，无需安装Python
    echo    2. 建议在目标机器上测试exe文件
    echo    3. 如有问题，请检查依赖库是否正确包含
    echo.
    echo 按任意键打开输出目录...
    pause >nul
    explorer dist
) else (
    echo.
    echo ❌ 打包失败，请检查错误信息
    echo.
    echo 💡 常见问题解决方案:
    echo    1. 确保所有依赖库已正确安装
    echo    2. 检查Python版本兼容性
    echo    3. 尝试以管理员身份运行
    echo.
)

pause 