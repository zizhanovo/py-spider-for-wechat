#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信爬虫工具一键打包脚本
======================

这个脚本会自动：
1. 检查依赖环境
2. 创建/更新图标
3. 打包应用程序
4. 清理临时文件

使用方法：
python 打包脚本.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示进度"""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description}完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖环境...")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("📦 安装 PyInstaller...")
        if not run_command("pip install pyinstaller", "安装 PyInstaller"):
            return False
    
    # 检查Pillow
    try:
        import PIL
        print("✅ Pillow 已安装")
    except ImportError:
        print("📦 安装 Pillow...")
        if not run_command("pip install Pillow", "安装 Pillow"):
            return False
    
    return True

def create_icon():
    """创建应用图标"""
    print("🎨 创建应用图标...")
    
    if os.path.exists('img/icon.png'):
        print("✅ 图标已存在，跳过创建")
        return True
    
    # 创建简单的图标生成脚本
    icon_script = '''
from PIL import Image, ImageDraw
import os

# 创建图标
size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 微信绿色背景
wechat_green = (7, 193, 96)
white = (255, 255, 255)

# 绘制圆形背景
margin = 20
circle_size = size - 2 * margin
draw.ellipse([margin, margin, margin + circle_size, margin + circle_size], 
             fill=wechat_green, outline=(6, 176, 87), width=4)

# 绘制简单的网格图案
center_x, center_y = size // 2, size // 2
grid_size = 120
grid_start_x = center_x - grid_size // 2
grid_start_y = center_y - grid_size // 2

# 绘制网格
for i in range(5):
    x = grid_start_x + i * 30
    draw.line([(x, grid_start_y), (x, grid_start_y + grid_size)], 
              fill=white, width=3)
    y = grid_start_y + i * 30
    draw.line([(grid_start_x, y), (grid_start_x + grid_size, y)], 
              fill=white, width=3)

# 保存图标
os.makedirs('img', exist_ok=True)
img.save('img/icon.png', 'PNG')

# 创建ICO文件
sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
ico_imgs = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
ico_imgs[0].save('img/icon.ico', format='ICO', sizes=sizes)

print("图标创建完成")
'''
    
    try:
        exec(icon_script)
        print("✅ 图标创建完成")
        return True
    except Exception as e:
        print(f"❌ 图标创建失败: {e}")
        return False

def create_spec_file():
    """创建或更新spec文件"""
    print("📄 创建打包配置文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('img', 'img'),
        ('note', 'note'),
        ('utils', 'utils'),
        ('requirements.txt', '.'),
        ('readme.md', '.'),
        ('*.md', '.'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'requests',
        'bs4',
        'beautifulsoup4',
        'sqlite3',
        'json',
        'time',
        'datetime',
        'tqdm',
        'utils.wechat_login',
        'utils.batch_scraper',
        'utils.getAllUrls',
        'utils.getContentsByUrls',
        'utils.getContentsByUrls_MultiThread',
        'utils.getFakId',
        'utils.getRealTimeByTimeStamp',
        'utils.getTitleByKeywords',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='微信爬虫工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/icon.ico' if os.path.exists('img/icon.ico') else None,
)

import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='微信爬虫工具.app',
        icon='img/icon.icns' if os.path.exists('img/icon.icns') else None,
        bundle_identifier='com.wechat.scraper',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
        }
    )
'''
    
    with open('build_exe.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 配置文件创建完成")
    return True

def build_app():
    """打包应用"""
    print("🚀 开始打包应用...")
    
    # 清理旧的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # 执行打包
    if not run_command("pyinstaller build_exe.spec", "打包应用"):
        return False
    
    return True

def cleanup():
    """清理临时文件"""
    print("🧹 清理临时文件...")
    
    cleanup_paths = [
        'build',
        '__pycache__',
        '*.pyc',
        '*.pyo',
    ]
    
    for path in cleanup_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    print("✅ 清理完成")

def main():
    """主函数"""
    print("🎯 微信爬虫工具一键打包脚本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，打包终止")
        return False
    
    # 创建图标
    if not create_icon():
        print("⚠️ 图标创建失败，但继续打包")
    
    # 创建配置文件
    if not create_spec_file():
        print("❌ 配置文件创建失败，打包终止")
        return False
    
    # 打包应用
    if not build_app():
        print("❌ 应用打包失败")
        return False
    
    # 清理临时文件
    cleanup()
    
    print("\n🎉 打包完成！")
    print("=" * 50)
    print("📂 打包结果位置：")
    
    if sys.platform == 'darwin':
        print("   - macOS应用：dist/微信爬虫工具.app")
        print("   - 可执行文件：dist/微信爬虫工具")
        print("\n🚀 启动方式：")
        print("   - 双击应用：open dist/微信爬虫工具.app")
        print("   - 命令行：./dist/微信爬虫工具")
    else:
        print("   - 可执行文件：dist/微信爬虫工具.exe")
        print("\n🚀 启动方式：")
        print("   - 双击：dist/微信爬虫工具.exe")
    
    print(f"\n📋 应用大小：约 {get_dir_size('dist'):.1f} MB")
    print("📖 详细说明请查看：exe使用说明.md")
    
    return True

def get_dir_size(path):
    """获取目录大小（MB）"""
    if not os.path.exists(path):
        return 0
    
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    
    return total / (1024 * 1024)  # Convert to MB

if __name__ == '__main__':
    try:
        success = main()
        if success:
            print("\n✅ 打包成功完成！")
        else:
            print("\n❌ 打包失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消打包")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 打包过程中出现错误: {e}")
        sys.exit(1) 