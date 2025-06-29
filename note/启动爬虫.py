#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号批量爬虫启动器
======================

简单的启动脚本，会检查依赖并启动批量爬虫程序。

功能:
    1. 检查必要的Python包是否已安装
    2. 提供友好的错误提示和安装建议
    3. 启动批量爬虫主程序

使用方法:
    python 启动爬虫.py
    或者直接双击运行
"""

import sys
import subprocess
import os

def check_requirements():
    """检查必要的依赖包"""
    required_packages = [
        ('PyQt5', '图形界面库'),
        ('requests', 'HTTP请求库'),
        ('selenium', '自动登录功能')
    ]
    
    missing_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} ({description}) - 已安装")
        except ImportError:
            print(f"✗ {package} ({description}) - 未安装")
            missing_packages.append(package)
    
    return missing_packages

def install_packages(packages):
    """安装缺失的包"""
    print(f"\n正在安装缺失的包: {', '.join(packages)}")
    
    for package in packages:
        try:
            print(f"安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} 安装成功")
        except subprocess.CalledProcessError:
            print(f"✗ {package} 安装失败，请手动安装")
            return False
    
    return True

def main():
    print("=" * 50)
    print("微信公众号批量爬虫启动器")
    print("=" * 50)
    print()
    
    print("正在检查依赖...")
    missing = check_requirements()
    
    if missing:
        print(f"\n发现 {len(missing)} 个缺失的依赖包")
        
        # 询问是否自动安装
        try:
            choice = input("\n是否自动安装缺失的包？(y/n): ").lower().strip()
            if choice in ['y', 'yes', '是']:
                if install_packages(missing):
                    print("\n✓ 所有依赖包安装完成")
                else:
                    print("\n请手动安装缺失的包后重试")
                    input("\n按回车键退出...")
                    return
            else:
                print("\n请手动安装以下包后重试:")
                for pkg in missing:
                    print(f"  pip install {pkg}")
                input("\n按回车键退出...")
                return
        except KeyboardInterrupt:
            print("\n\n用户取消操作")
            return
    
    print("\n依赖检查完成，启动批量爬虫...")
    
    try:
        # 启动主程序
        import main
        main.main()
        
    except ImportError as e:
        print(f"启动失败：{e}")
        print("请确保 main.py 文件在当前目录")
    except Exception as e:
        print(f"运行出错：{e}")
        input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n启动器出错：{e}")
        input("\n按回车键退出...") 