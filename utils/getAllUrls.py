#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号文章URL批量获取模块
===========================

模块功能:
    通过微信公众平台的文章列表接口，分页获取指定公众号的历史文章URL链接、
    标题和发布时间等基础信息。这是爬虫流程的第一步，为后续的内容抓取
    提供目标URL列表。

主要功能:
    1. 分页数据获取 - 按页码批量获取文章列表
    2. 信息提取 - 从API响应中提取文章标题、链接、时间戳
    3. 进度显示 - 使用tqdm显示爬取进度
    4. 数据保存 - 将获取的数据分类保存为CSV文件
    5. 目录管理 - 自动创建保存目录结构

API接口说明:
    - 接口地址: https://mp.weixin.qq.com/cgi-bin/appmsg
    - 请求方式: GET
    - 认证方式: 通过token和cookie进行身份验证
    - 分页机制: 每页5篇文章，通过begin参数控制起始位置

分页逻辑:
    - 第0页: begin=0, 最新文章
    - 第1页: begin=5, 次新文章
    - 第n页: begin=n*5
    - 页数越小，文章越新

数据提取字段:
    - title: 文章标题
    - link: 文章详情页URL
    - update_time: 文章发布时间戳

文件保存格式:
    生成三个CSV文件：
    - {filename}_url.csv: 文章链接列表
    - {filename}_title.csv: 文章标题列表  
    - {filename}_update-time.csv: 发布时间戳列表

参数说明:
    - page_start: 起始页码（推荐从0开始）
    - page_num: 爬取页数（不能为0）
    - save_path: 文件保存根目录
    - fad: 公众号的fakeid
    - tok: 访问token
    - headers: HTTP请求头
    - filename: 保存文件名前缀

性能优化:
    - 请求间随机延时1-2秒，避免被反爬
    - 使用tqdm显示实时进度
    - 异常处理确保程序稳定性

使用示例:
    run_getAllUrls(
        page_start=0,
        page_num=10, 
        save_path='/path/to/save',
        fad='公众号fakeid',
        tok='access_token',
        headers={'cookie': '...'},
        filename='raw/articles'
    )

注意事项:
    - 确保有足够的存储空间
    - 避免过于频繁的请求
    - 检查网络连接稳定性
    - 监控API返回状态

作者: 王思哲  
创建时间: 2022/12/20
版本: 1.0
"""

# -*- coding: utf-8 -*-
import random
import requests
import time
import csv
from tqdm import tqdm
import datetime
import os


def getAllUrl(page_num, start_page, fad, tok, headers):                             # pages
    url = 'https://mp.weixin.qq.com/cgi-bin/appmsg'
    title = []
    link = []
    update_time = []
    with tqdm(total=page_num) as pbar:
        for i in range(page_num):
            data = {
                'action': 'list_ex',
                'begin': start_page + i*5,       #页数
                'count': '5',
                'fakeid': fad,
                'type': '9',
                'query':'' ,
                'token': tok,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
            }
            time.sleep(random.randint(1, 2))
            r = requests.get(url, headers=headers, params=data)
            # 解析json
            dic = r.json()
            for i in dic['app_msg_list']:     # 遍历dic['app_msg_list']中所有内容
                # 按照键值对的方式选择
                title.append(i['title'])      # get title value
                link.append(i['link'])        # get link value
                update_time.append(i['update_time'])    # get update-time value
            pbar.update(1)

    return title, link, update_time

def write2csv(path, filename, data_list, eType:str):
    mkdir(path=path)
    with open(path + '/' + filename + '_' + eType + '.csv', 'w', newline='', encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        for row in data_list:
            writer.writerow([row])
    print(f"[save {eType} list] {str(datetime.datetime.now())} done")

def mkdir(path):
    '''
    创建指定的文件夹
    :param path: 文件夹路径，字符串格式
    :return: True(新建成功) or False(文件夹已存在，新建失败)
    '''

    # 去除首位空格
    path = path.strip()
    # 去除尾部 \ 符号
    path = path.rstrip("\\")

    # 判断路径是否存在
    # 存在     True
    # 不存在   False
    isExists = os.path.exists(path)

    # 判断结果
    if not isExists:
        # 如果不存在则创建目录
         # 创建目录操作函数
        os.makedirs(path)
        print(path + ' 创建成功')
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print(path + ' 目录已存在')
        return False

def run_getAllUrls(page_start, page_num, save_path, fad, tok, headers, filename):
    mkdir(save_path + '/raw')
    start = time.time()
    title, link, update_time = getAllUrl(page_num=page_num, start_page=page_start, fad=fad, tok=tok, headers=headers)
    # save urls, titles, update_times
    write2csv(save_path, filename, link, eType="url")
    write2csv(save_path, filename, title, eType="title")
    write2csv(save_path, filename, update_time, eType="update-time")
    end = time.time()
    print("time cost:", end - start, "s")

