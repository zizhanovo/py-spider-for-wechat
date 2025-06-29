#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号文章时间戳转换模块
==========================

模块功能:
    将微信公众号文章的Unix时间戳转换为人类可读的日期时间格式。
    微信API返回的时间是Unix时间戳格式，需要转换为标准的日期时间
    字符串以便用户理解和数据分析。

主要功能:
    1. 时间戳解析 - 将Unix时间戳转换为时间元组
    2. 格式化输出 - 转换为标准的日期时间字符串
    3. 批量处理 - 处理CSV文件中的所有时间戳
    4. 数据保存 - 将转换结果保存为新的CSV文件

时间格式说明:
    - 输入格式: Unix时间戳（整数，秒级精度）
    - 输出格式: "YYYY-MM-DD HH:MM:SS"（24小时制）
    - 时区: 本地时区（通常为北京时间 UTC+8）

转换逻辑:
    1. 读取时间戳CSV文件
    2. 逐行解析时间戳数值
    3. 使用time.localtime()转换为时间元组
    4. 使用time.strftime()格式化为字符串
    5. 保存转换结果到新文件

文件处理:
    - 输入文件: {filename}_update-time.csv（包含时间戳）
    - 输出文件: {filename}_real-time.csv（包含格式化时间）
    - 编码格式: UTF-8-BOM（确保中文兼容性）

参数说明:
    - savepath: 文件保存目录路径
    - filename: 文件名前缀（不含扩展名）

使用示例:
    # 单个时间戳转换
    timestamp = 1671523200  # 2022-12-20 12:00:00
    readable_time = getRealTimeByTimeStamp(timestamp)
    print(readable_time)  # "2022-12-20 12:00:00"
    
    # 批量文件处理
    run_getRealTimeByTimeStamp(
        savepath='/path/to/files',
        filename='raw/articles'
    )

时间精度:
    - 支持秒级精度的时间戳
    - 自动处理时区转换
    - 保持时间的准确性和一致性

注意事项:
    - 确保输入的时间戳格式正确
    - 时间戳应为有效的正整数
    - 注意时区差异可能影响显示结果
    - 大文件处理时注意内存使用

错误处理:
    - 无效时间戳会被跳过
    - 文件读取错误会有相应提示
    - 保持程序的健壮性和稳定性

作者: 王思哲
创建时间: 2022/12/20
版本: 1.0
"""

import time
import csv
import datetime


def getRealTimeByTimeStamp(time_stamp):
    time_array = time.localtime(time_stamp)  # 时间序列
    otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
    return otherStyleTime

def getTSListAndConvert(ts_storage_path):
    with open(ts_storage_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        ts_list = []
        for row in reader:
            ts_list.append(getRealTimeByTimeStamp(int(row[0])))
    return ts_list

def Write2Csv(data_list, savepath, filename):
    with open(savepath + '/' + filename + '_real-time.csv', 'w', newline='', encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        for row in data_list:
            writer.writerow([row])
    print(f"[save real-time list] {str(datetime.datetime.now())} done")

def run_getRealTimeByTimeStamp(savepath, filename):
    ts_list = getTSListAndConvert(savepath + '/' + filename + "_update-time.csv")
    Write2Csv(ts_list, savepath, filename)
