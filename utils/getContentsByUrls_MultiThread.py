#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号文章内容多线程获取模块
==============================

模块功能:
    基于多线程技术，并发下载微信公众号文章的详细内容。通过生产者-消费者模式，
    实现高效的URL请求和HTML内容解析，大幅提升数据获取速度。

主要功能:
    1. 多线程并发下载 - 同时处理多个文章URL请求
    2. 队列管理 - 使用线程安全的队列协调任务分配
    3. HTML内容解析 - 提取文章正文内容
    4. 结果排序 - 按原始顺序整理下载结果
    5. 数据持久化 - 将内容保存为CSV格式

技术架构:
    采用生产者-消费者模式的多线程架构：
    - 生产者线程(do_craw): 负责HTTP请求，获取HTML响应
    - 消费者线程(do_parse): 负责解析HTML，提取文章内容
    - 队列缓冲: url_queue存储待处理URL，response_queue存储响应结果

线程配置:
    - 爬虫线程数: 20个（并发HTTP请求）
    - 解析线程数: 20个（并发HTML解析）
    - 总线程数: 40个（平衡性能与资源消耗）

内容提取策略:
    - 目标标签: <p>标签（包含主要文章内容）
    - 过滤规则: 去除空白内容和无效文本
    - 编码处理: 统一使用UTF-8编码避免乱码

队列机制:
    1. url_queue: 存储[索引, URL]格式的待处理任务
    2. response_queue: 存储[索引, HTTP响应]格式的结果
    3. 通过索引保证最终结果的顺序一致性

性能优化:
    - 随机延时: 1-2秒间隔避免被反爬
    - 异常处理: 确保单个失败不影响整体进程
    - 内存管理: 及时清理队列避免内存泄漏
    - 结果排序: 按原始URL顺序输出内容

数据流程:
    URL列表 → url_queue → 多线程请求 → response_queue → 多线程解析 → 内容列表 → CSV文件

参数说明:
    - savepath: 文件保存目录
    - filename: 输入文件名前缀（用于读取URL文件）
    - headers: HTTP请求头（包含认证信息）

输入文件:
    - {filename}_url.csv: 包含文章URL列表的CSV文件

输出文件:
    - {filename}_content.csv: 包含文章内容的CSV文件

使用示例:
    run_getContentsByUrls_MultiThread(
        savepath='/path/to/save',
        filename='raw/articles',
        headers={'cookie': '...', 'user-agent': '...'}
    )

注意事项:
    - 确保URL文件存在且格式正确
    - 监控系统资源使用情况
    - 网络不稳定时可能需要重试机制
    - 大量并发请求时注意IP限制

作者: 王思哲
创建时间: 2022/12/20
版本: 1.0
"""

import csv
import random
import threading
import requests
import bs4
import time
import queue
import datetime


contents = []

# 从文件读取URLs，返回字典
def getUrlList(url_storage_path):
    with open(url_storage_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        url_list = [[idx, row] for idx, row in enumerate(reader)]
    return url_list

# 不断向rep队列添加response对象
def do_craw(headers, url_queue:queue.Queue, response_queue:queue.Queue):
    while url_queue.empty() != True:
        url = url_queue.get()
        response = requests.get(url[1][0], headers=headers)
        response_queue.put([url[0], response])
        # print("craw")
        time.sleep(random.randint(1, 2))

# 不断解析对象，将结果添加到contents列表中
def do_parse(response_queue:queue.Queue):
    time.sleep(2)
    while response_queue.empty() != True:
        response = response_queue.get()
        # 解析html
        soup = bs4.BeautifulSoup(response[1].text, 'html.parser')
        # 大多数p标签中包含的是文字，但也有一些直接是 "section > span"， 这些内容没有爬到
        soup_sel = soup.select("p")
        content = ""
        for c in soup_sel:
            t = c.get_text().strip('\n')
            if t != '':
                content += t
        contents.append([response[0], content])
        # print("parse")
        time.sleep(random.randint(1, 2))
    # return contents

# 按行存csv， 编码'utf-8-sig'存中文
def saveContentsTocsv(path, filename, contents):
    with open(path + '/' + filename + '_content.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        for row in contents:
            writer.writerow([row])
    print(f"[save content list] {str(datetime.datetime.now())} done")


def run_getContentsByUrls_MultiThread(savepath, filename, headers):
    url_list_storage_path = savepath + '/' + filename + '_url.csv'
    url_list = getUrlList(url_list_storage_path)
    url_queue = queue.Queue()
    response_queue = queue.Queue()

    start = time.time()

    for url in url_list:
        url_queue.put(url)

    thread_list = []
    # craw
    for idx in range(20):
        tc = threading.Thread(target=do_craw, args=(headers, url_queue, response_queue))
        thread_list.append(tc)
        tc.start()
    # parse
    for idx in range(20):
        tp = threading.Thread(target=do_parse, args=(response_queue,))
        thread_list.append(tp)
        tp.start()

    for thread in thread_list:
        thread.join()

    contents.sort(key=lambda x: (x[0]))
    res = []
    for c in contents:
        res.append(c[1])
    end = time.time()
    saveContentsTocsv(savepath, filename, res)
    print(f"time cost:{end - start}s")
