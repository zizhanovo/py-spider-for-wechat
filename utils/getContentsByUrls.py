#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号文章内容单线程获取模块（已弃用）
========================================

模块功能:
    这是文章内容获取的单线程版本，主要用于早期开发和测试。
    现已被多线程版本(getContentsByUrls_MultiThread.py)替代，
    但保留作为参考实现和小规模测试使用。

主要功能:
    1. 顺序下载 - 逐个处理文章URL请求
    2. HTML解析 - 提取文章正文内容
    3. 进度显示 - 使用tqdm显示下载进度
    4. 内容保存 - 将结果保存为CSV文件

技术特点:
    - 单线程顺序执行，稳定性好
    - 资源占用少，适合小规模爬取
    - 代码简单，易于理解和调试
    - 速度较慢，不适合大批量处理

与多线程版本对比:
    优势:
    - 代码逻辑简单清晰
    - 资源消耗低
    - 调试容易
    - 不会因并发导致问题
    
    劣势:
    - 处理速度慢
    - 效率低下
    - 不适合大量数据

内容提取策略:
    - 目标标签: <p>标签（包含主要文章内容）
    - 过滤规则: 去除空白内容
    - 内容处理: 截取有效内容部分[116:-11]
    - 编码处理: UTF-8编码避免乱码

HTTP请求配置:
    - 请求头: 包含cookie和user-agent
    - 延时机制: 可选的随机延时（已注释）
    - 错误处理: 基本的状态码检查

数据处理流程:
    1. 从CSV文件读取URL列表
    2. 逐个发送HTTP请求
    3. 使用BeautifulSoup解析HTML
    4. 提取<p>标签中的文本内容
    5. 清理和格式化文本
    6. 保存结果到CSV文件

参数说明:
    - url_storage_path: URL列表文件路径
    - 输出文件名: 用户交互式输入

使用场景:
    - 小规模测试（少于100篇文章）
    - 调试和开发阶段
    - 网络环境不稳定时的备用方案
    - 学习和理解爬虫基本原理

注意事项:
    - 已被多线程版本替代，不推荐生产使用
    - 仅适用于小规模数据爬取
    - 硬编码的请求头需要更新
    - 缺乏完善的错误处理机制

迁移建议:
    建议使用 getContentsByUrls_MultiThread.py 替代此模块，
    以获得更好的性能和更完善的功能。

作者: 王思哲
创建时间: 2022/12/20
状态: 已弃用（保留作为参考）
版本: 1.0
"""

import csv
import random
import requests
import bs4
import time
from tqdm import tqdm

# 从文件读取URLs，返回字典
def getUrlList(url_storage_path):
    with open(url_storage_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        url_list = [row for row in reader]
    return url_list


def getContentByUrl(url_list):
    # 返回结果
    contents = []
    # 请求头
    headers = {
        "cookie":
            "ua_id=HvjnK6CPHdz8Zt8LAAAAAOhen6ItkIZVMBtW_LgGBJI=; wxuin=59663835389206; cert=8usVhBJvV_bhiOGzvEr5KNZrBLVPpLvI; sig=h01f5bf100266357f9042120ae1f1e6812f0dd97700fa5cc0af9d3206ec20ce8d58f65c6dfd9ddf258b; master_key=oqWPTPRNLKNRxZ933GO+CKIV6t0+ii+8093Le9A8ayE=; rewardsn=; wxtokenkey=777; wwapp.vid=; wwapp.cst=; wwapp.deviceid=; uuid=9a488fb0b902debc7c27e896a8cad45a; rand_info=CAESIJrdL2xSqHo7JtTHuM8d4zAMoSNjxacqc6VQsR4g87rR; slave_bizuin=3940396966; data_bizuin=3940396966; bizuin=3940396966; data_ticket=GYSHLkTsYGcdfdQ/Oj2wGnYGGBkKpTBgA59H5y7Zb2Su8NHcYn40uu+pALruIHzO; slave_sid=VnNCREhCQ1diTkoyQ091ejQ0ckoxdDBiTUxLMWxURHFPVDNsWmFhZVY0UjFzemc0UjhZc19hOERZY2tGa2dEcFRmeEJjV2tWRXRoZlFfMjFlUmhkbXRUdF9pdzUxTEVSVzQxbmhaYnVMMnNuSm55b0NsYkJwOHhLSEdOMk9mYk1hSW5DcDFsZTFjVEw5YUkw; slave_user=gh_495d307185e5; xid=1f54bfb9bf5268fecf62675424ba6a66; mm_lang=zh_CN",
        "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    }
    # 遍历url
    with tqdm(total=len(url_list)) as pbar:
        for url in url_list:
            # 随机休眠，防止被封
            # time.sleep(random.randint(1, 5))
            # 发送请求
            response = requests.get(url[0], headers=headers)
            # print("state_code:", response.status_code)    # 200即正常
            # 解析html
            soup = bs4.BeautifulSoup(response.text, 'html.parser')
            # 大多数p标签中包含的是文字，但也有一些直接是 "section > span"， 这些内容没有爬到
            soup_sel = soup.select("p")
            # soup_sel = soup.select(".rich_media_inner")
            content = ""
            for c in soup_sel:
                t = c.get_text().strip('\n')
                if t != '':
                    content += t
            # print(content)
            # print(content[116:-11])
            content = content[116:-11]
            contents.append(content)
            pbar.update(1)
        return contents

# 按行存csv， 编码'utf-8-sig'存中文
def saveContentsTocsv(contents):
    file_name = input("please name the new csv-file\n")
    with open('./data/' + file_name + '.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        for row in contents:
            writer.writerow([row])
    print("done")


if __name__ == "__main__":
    start = time.time()
    url_list_storage_path = "./data/20pages_link.csv"

    url_list = getUrlList(url_list_storage_path)
    contents = getContentByUrl(url_list)
    # print(contents)
    saveContentsTocsv(contents)
    end = time.time()
    print("time cost:", end-start, "s")
