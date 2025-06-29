#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# 添加依赖库路径
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(current_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# 导入原始的login模块并传递命令行参数
if __name__ == '__main__':
    # 保持原始的sys.argv，这样login.py可以正确处理命令行参数
    from login import main
    main()
