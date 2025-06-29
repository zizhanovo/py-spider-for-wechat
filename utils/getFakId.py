#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号ID获取模块
==================

模块功能:
    通过微信公众平台的搜索接口，根据公众号名称关键词搜索匹配的公众号，
    并返回公众号的基本信息（名称和fakeid）。fakeid是微信公众平台内部
    用于标识公众号的唯一ID，是后续获取文章列表的必要参数。

主要功能:
    1. 公众号搜索 - 根据关键词搜索公众号
    2. 结果解析 - 解析搜索结果并提取公众号信息
    3. 数据格式化 - 将结果格式化为标准的字典列表

API接口说明:
    - 接口地址: https://mp.weixin.qq.com/cgi-bin/searchbiz
    - 请求方式: GET
    - 认证方式: 通过token和cookie进行身份验证
    - 返回格式: JSON

参数说明:
    - headers: HTTP请求头，包含cookie等认证信息
    - tok: 微信公众平台的访问token
    - query: 搜索关键词（公众号名称）

返回值格式:
    返回包含公众号信息的字典列表，每个字典包含：
    - wpub_name: 公众号显示名称
    - wpub_fakid: 公众号的内部ID（用于后续API调用）

使用示例:
    headers = {'cookie': 'your_cookie_here', ...}
    token = 'your_token_here'
    query = '公众号名称'
    result = get_fakid(headers, token, query)
    # result: [{'wpub_name': '公众号1', 'wpub_fakid': 'fakeid1'}, ...]

注意事项:
    - 需要有效的微信公众平台登录状态
    - token和cookie必须匹配且在有效期内
    - 搜索结果最多返回10个匹配的公众号
    - 请求频率不宜过高，避免被限制访问

作者: 王思哲
创建时间: 2022/12/20
版本: 1.0
"""

# coding=utf-8
# @Time : 2022/12/20 11:55 AM
# @Author : 王思哲
# @File : getFakId.py
# @Software: PyCharm

import requests


def get_fakid(headers, tok, query):
    '''

    :param headers:请求头
    :param tok: token
    :param query: 查询名称
    :return:
    '''
    url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
    data = {
        'action': 'search_biz',
        'scene': 1,  # 页数
        'begin': 0,
        'count': 10,
        'query': query,
        'token': tok,
        'lang': 'zh_CN',
        'f': 'json',
        'ajax': '1',
    }
    # 发送请求
    r = requests.get(url, headers=headers, params=data)
    # 解析json
    dic = r.json()
    # 获取公众号名称、fakeid
    wpub_list = [
        {
            'wpub_name': item['nickname'],
            'wpub_fakid': item['fakeid']
        }
        for item in dic['list']
    ]

    return wpub_list
