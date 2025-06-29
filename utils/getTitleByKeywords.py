#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号文章关键词筛选模块
==========================

模块功能:
    根据用户指定的关键词对已爬取的文章进行筛选，并整合所有数据
    （时间、标题、链接、内容）生成最终的结果文件。支持多关键词
    匹配和灵活的筛选策略。

主要功能:
    1. 关键词解析 - 解析用户输入的关键词字符串
    2. 正则匹配 - 使用正则表达式在标题中搜索关键词
    3. 数据整合 - 合并时间、标题、链接、内容四类数据
    4. 结果筛选 - 根据匹配结果过滤文章
    5. 文件输出 - 生成最终的CSV结果文件

关键词格式:
    - 分隔符: 中文分号（；）
    - 示例: "人工智能；机器学习；深度学习"
    - 匹配模式: OR逻辑（任一关键词匹配即可）

正则匹配策略:
    - 匹配方式: re.findall()（查找所有匹配项）
    - 匹配模式: 使用 '|'.join() 构建OR模式
    - 大小写: 区分大小写匹配
    - 位置: 在文章标题中搜索关键词

数据整合逻辑:
    1. 读取四个CSV文件：
       - {filename}_real-time.csv: 格式化时间
       - {filename}_title.csv: 文章标题
       - {filename}_url.csv: 文章链接
       - {filename}_content.csv: 文章内容
    2. 按索引位置对应整合数据
    3. 构建包含完整信息的数据字典

筛选流程:
    1. 解析关键词字符串为列表
    2. 对每个标题执行正则匹配
    3. 记录匹配成功的文章索引
    4. 根据索引筛选对应的完整数据
    5. 如果无关键词则输出所有数据

输出格式:
    CSV文件包含以下列：
    - 时间: 文章发布的格式化时间
    - 标题: 文章标题
    - 地址: 文章详情页URL
    - 内容: 文章正文内容

参数说明:
    - keywords_str: 关键词字符串（中文分号分隔）
    - savepath: 文件保存目录
    - filename: 文件名前缀

使用示例:
    # 有关键词筛选
    run_getTitleByKeywords(
        keywords_str="人工智能；机器学习",
        savepath="/path/to/save",
        filename="articles"
    )
    
    # 无关键词（输出所有文章）
    run_getTitleByKeywords(
        keywords_str="",
        savepath="/path/to/save", 
        filename="articles"
    )

输出文件:
    - 文件名: {filename}_爬取结果.csv
    - 编码: UTF-8-BOM（支持中文显示）
    - 格式: 标准CSV格式，可用Excel打开

性能特点:
    - 高效的正则匹配算法
    - 内存友好的数据处理
    - 支持大量文章的快速筛选
    - 灵活的关键词组合策略

注意事项:
    - 确保输入文件完整存在
    - 关键词区分大小写
    - 空关键词将输出所有文章
    - 文件路径需要有写入权限

作者: 王思哲
创建时间: 2022/12/20  
版本: 1.0
"""

import csv
import re
import datetime


def getTitleList(titles_storage_path):
    with open(titles_storage_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        titles_list = [row for row in reader]
    return titles_list

def regexTitleByKeywords(sentences_list, keywords_list):
    '''
    :param sentences_list: 待匹配句子列表
    :param keywords_list:  匹配关键词列表
    :return: 匹配成功的句子下标
    '''
    res = []
    for index, sentence in enumerate(sentences_list):
        pattern = re.compile('|'.join(keywords_list))
        result_findall = pattern.findall(sentence[0])   # .match()-匹配开头  .search()-只匹配第一个  .findall()-匹配所有
        if result_findall:                              # .match() / .search() 返回None    .findall() 返回空列表
            res.append(index)
    return res

def run_getTitleByKeywords(keywords_str:str, savepath:str, filename:str):
    public_path = savepath + '/raw/' + filename + '_'
    # Path
    title_path = public_path + "title.csv"
    update_time_path = public_path + "real-time.csv"
    url_path = public_path + "url.csv"
    content_path = public_path + "content.csv"
    # load files
    title_list = getTitleList(title_path)
    update_time_list = getTitleList(update_time_path)
    url_list = getTitleList(url_path)
    content_list = getTitleList(content_path)

    # get index
    FlAG = True
    if keywords_str != '':
        keyword_list = keywords_str.split('；')
        # 正则获取下标
        res_index = regexTitleByKeywords(title_list, keyword_list)
    else:
        FlAG = False

    data_list = []
    for a, b, c, d in zip(update_time_list, title_list, url_list, content_list):
        x = {}
        x['时间'] = a[0]
        x['标题'] = b[0]
        x['地址'] = c[0]
        x['内容'] = d[0]
        data_list.append(x)
    with open( savepath + '/' + filename + '_爬取结果.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['时间', '标题', '地址', '内容'])
        if FlAG:
            for idx in res_index:
                writer.writerow(
                    data_list[idx].values()
                )
        else:
            for i in range(len(data_list)):
                writer.writerow(
                    data_list[i].values()
                )
    print(f"[save filtered data list] {str(datetime.datetime.now())} done")
