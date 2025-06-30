#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows打包脚本
用于在Windows环境中打包微信爬虫工具
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    required_packages = ['pyinstaller', 'pillow']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("正在安装...")
        for package in missing_packages:
            subprocess.run([sys.executable, '-m', 'pip', 'install', package])
        print("✅ 依赖安装完成")

def create_icon():
    """创建应用图标"""
    try:
        from PIL import Image, ImageDraw
        
        print("🎨 正在创建图标...")
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 微信绿色背景
        bg_color = (19, 185, 68, 255)
        draw.ellipse([10, 10, size-10, size-10], fill=bg_color)
        
        # 绘制爬虫网格
        grid_color = (255, 255, 255, 180)
        for i in range(50, size-50, 30):
            draw.line([i, 50, i, size-50], fill=grid_color, width=2)
            draw.line([50, i, size-50, i], fill=grid_color, width=2)
        
        # 中心文字
        font_size = 40
        text = "微"
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        draw.text((x, y), text, fill=(255, 255, 255, 255))
        
        # 保存为ico格式
        img.save('icon.ico')
        print("✅ 图标创建完成: icon.ico")
        return True
        
    except Exception as e:
        print(f"❌ 图标创建失败: {e}")
        return False

def build_executable():
    """构建可执行文件"""
    if platform.system() != 'Windows':
        print("❌ 此脚本需要在Windows系统上运行")
        return False
    
    print("🔨 开始构建Windows可执行文件...")
    
    # PyInstaller命令
    cmd = [
        'pyinstaller',
        '--onefile',                    # 单文件模式
        '--windowed',                   # 无控制台窗口
        '--icon=icon.ico',             # 图标文件
        '--name=微信爬虫工具',          # 输出文件名
        '--add-data=utils;utils',      # 添加utils目录
        '--noconsole',                 # 不显示控制台
        '--clean',                     # 清理缓存
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            exe_path = Path('dist') / '微信爬虫工具.exe'
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / 1024 / 1024
                print(f"✅ 构建成功!")
                print(f"📦 文件位置: {exe_path}")
                print(f"📏 文件大小: {size_mb:.1f}MB")
                return True
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 微信爬虫工具 - Windows打包脚本")
    print("=" * 50)
    
    # 检查系统
    if platform.system() != 'Windows':
        print("❌ 错误：此脚本需要在Windows系统上运行")
        print("💡 建议：")
        print("   1. 使用GitHub Actions自动构建")
        print("   2. 在Windows虚拟机中运行此脚本")
        print("   3. 使用Windows Subsystem for Linux (WSL)")
        return False
    
    # 检查依赖
    check_dependencies()
    
    # 创建图标
    if not create_icon():
        print("⚠️  图标创建失败，将使用默认图标")
    
    # 构建可执行文件
    success = build_executable()
    
    if success:
        print("\n🎉 打包完成！")
        print("📁 可执行文件位置: dist/微信爬虫工具.exe")
        print("💡 您可以直接运行这个exe文件")
    else:
        print("\n❌ 打包失败")
        print("💡 请检查错误信息并重试")
    
    return success

if __name__ == '__main__':
    main() 