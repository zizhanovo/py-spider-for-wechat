#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速打包脚本 - 无需GitHub Actions
================================

在任何系统上本地快速打包为可执行文件

使用方法：
python 快速打包.py
"""

import os
import sys
import subprocess
import platform

def check_and_install_pyinstaller():
    """检查并安装PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("📦 正在安装 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller 安装成功")
            return True
        except subprocess.CalledProcessError:
            print("❌ PyInstaller 安装失败")
            return False

def get_system_info():
    """获取系统信息"""
    system = platform.system()
    arch = platform.machine()
    
    if system == "Windows":
        exe_ext = ".exe"
        icon_file = "img/icon.ico" if os.path.exists("img/icon.ico") else None
    elif system == "Darwin":  # macOS
        exe_ext = ""
        icon_file = "img/icon.icns" if os.path.exists("img/icon.icns") else None
    else:  # Linux
        exe_ext = ""
        icon_file = None
    
    return system, arch, exe_ext, icon_file

def build_executable():
    """构建可执行文件"""
    system, arch, exe_ext, icon_file = get_system_info()
    
    print(f"🖥️ 检测到系统: {system} ({arch})")
    
    # 基础PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=微信爬虫工具",
        "--distpath=./dist_local"
    ]
    
    # 添加无控制台窗口（GUI应用）
    if system == "Windows" or system == "Darwin":
        cmd.append("--windowed")
    
    # 添加图标
    if icon_file and os.path.exists(icon_file):
        cmd.extend(["--icon", icon_file])
        print(f"🎨 使用图标: {icon_file}")
    
    # 添加主文件
    cmd.append("main.py")
    
    print(f"🚀 开始打包...")
    print(f"📋 命令: {' '.join(cmd)}")
    
    try:
        # 清理旧的构建文件
        if os.path.exists("dist_local"):
            import shutil
            shutil.rmtree("dist_local")
        if os.path.exists("build"):
            import shutil
            shutil.rmtree("build")
        if os.path.exists("微信爬虫工具.spec"):
            os.remove("微信爬虫工具.spec")
        
        # 执行打包
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 检查生成的文件
            output_file = f"dist_local/微信爬虫工具{exe_ext}"
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
                print(f"\n🎉 打包成功！")
                print(f"📁 输出文件: {output_file}")
                print(f"📏 文件大小: {file_size:.1f} MB")
                print(f"🖥️ 目标系统: {system}")
                
                # 显示运行方式
                if system == "Windows":
                    print(f"\n🚀 运行方式:")
                    print(f"   双击: {output_file}")
                    print(f"   或命令行: .\\{output_file.replace('/', '\\\\')}")
                else:
                    print(f"\n🚀 运行方式:")
                    print(f"   双击或命令行: ./{output_file}")
                    # 设置执行权限
                    os.chmod(output_file, 0o755)
                
                return True
            else:
                print("❌ 打包失败：找不到输出文件")
                return False
        else:
            print("❌ 打包失败：")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程出错: {e}")
        return False

def create_simple_icon():
    """创建简单图标（如果不存在）"""
    if not os.path.exists("img"):
        os.makedirs("img")
    
    # 检查是否已有图标
    if os.path.exists("img/icon.png"):
        return True
    
    try:
        from PIL import Image, ImageDraw
        
        # 创建简单图标
        size = 256
        img = Image.new('RGBA', (size, size), (7, 193, 96))  # 微信绿
        draw = ImageDraw.Draw(img)
        
        # 绘制简单的网格图案
        white = (255, 255, 255)
        draw.rectangle([50, 50, 206, 206], fill=white, width=3)
        
        # 添加网格线
        for i in range(4):
            x = 70 + i * 30
            draw.line([(x, 70), (x, 186)], fill=(7, 193, 96), width=2)
            y = 70 + i * 30
            draw.line([(70, y), (186, y)], fill=(7, 193, 96), width=2)
        
        # 保存PNG
        img.save('img/icon.png', 'PNG')
        
        # 转换为ICO和ICNS
        system = platform.system()
        if system == "Windows":
            sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
            ico_imgs = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
            ico_imgs[0].save('img/icon.ico', format='ICO', sizes=sizes)
            print("✅ 创建了Windows图标")
        elif system == "Darwin":  # macOS
            # 在macOS上可以使用系统工具创建icns
            img.save('img/icon.icns', 'PNG')  # 简化版
            print("✅ 创建了macOS图标")
        
        return True
        
    except ImportError:
        print("⚠️ 未安装Pillow，跳过图标创建")
        return False
    except Exception as e:
        print(f"⚠️ 图标创建失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 微信爬虫工具 - 快速本地打包")
    print("=" * 50)
    
    # 检查主文件
    if not os.path.exists("main.py"):
        print("❌ 未找到 main.py 文件")
        return
    
    # 检查并安装PyInstaller
    if not check_and_install_pyinstaller():
        return
    
    # 创建图标
    create_simple_icon()
    
    # 执行打包
    if build_executable():
        print("\n🎊 恭喜！本地打包完成")
        print("📝 说明:")
        print("   - 生成的文件可以在没有Python环境的电脑上运行")
        print("   - 首次启动可能需要几秒钟")
        print("   - 如果被杀毒软件误报，请添加信任")
    else:
        print("\n💔 打包失败，请检查错误信息")

if __name__ == "__main__":
    main() 