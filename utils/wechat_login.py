#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号自动登录模块
====================

模块功能:
    通过Selenium自动化浏览器，实现微信公众号平台的自动登录，
    自动获取token和cookie等认证信息，并提供缓存管理功能。

主要功能:
    1. 自动登录 - 使用Selenium打开浏览器进行扫码登录
    2. 信息提取 - 自动提取token和cookie认证信息
    3. 缓存管理 - 保存和验证登录信息缓存
    4. 状态检查 - 检查当前登录状态和有效性
    5. 自动清理 - 清理浏览器进程和临时文件

技术架构:
    - 浏览器自动化: Selenium WebDriver
    - 浏览器引擎: Chrome/Chromium
    - 信息提取: 正则表达式和Cookie解析
    - 缓存存储: JSON文件格式
    - 状态验证: HTTP请求验证

工作流程:
    1. 检查现有缓存是否有效
    2. 如缓存无效，启动Chrome浏览器
    3. 导航到微信公众号平台登录页
    4. 等待用户扫码登录完成
    5. 自动提取URL中的token参数
    6. 获取浏览器中的所有cookies
    7. 保存认证信息到缓存文件
    8. 清理浏览器进程和临时文件

缓存机制:
    - 缓存文件: wechat_cache.json
    - 有效期: 4天（96小时）
    - 验证机制: 通过API请求验证token有效性
    - 自动清理: 过期缓存自动删除

安全特性:
    - 隐藏自动化特征，避免被检测
    - 使用临时用户数据目录
    - 自动清理敏感信息
    - 异常处理和错误恢复

使用示例:
    # 基本使用
    login_manager = WeChatLogin()
    if login_manager.login():
        token = login_manager.get_token()
        cookies = login_manager.get_cookies()
        headers = login_manager.get_headers()
    
    # 检查登录状态
    status = login_manager.check_login_status()
    if status['isLoggedIn']:
        print(f"已登录，时间: {status['loginTime']}")

依赖要求:
    - selenium >= 4.0.0
    - requests >= 2.28.0
    - Chrome浏览器
    - ChromeDriver (自动管理)

注意事项:
    - 需要安装Chrome浏览器
    - 首次使用需要扫码登录
    - 登录信息会自动缓存4天
    - 网络环境需要能访问微信公众平台

作者: 基于原始login.py改进
创建时间: 2024/12/20
版本: 1.0
"""

import json
import os
import random
import time
import platform
import tempfile
import shutil
import subprocess
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import re

# 配置常量
CACHE_FILE = 'wechat_cache.json'
CACHE_EXPIRE_HOURS = 24 * 4  # 缓存有效期（小时），4天


class WeChatLogin:
    """微信公众号登录管理器"""

    def __init__(self, cache_file=CACHE_FILE):
        """
        初始化登录管理器
        
        Args:
            cache_file (str): 缓存文件路径
        """
        self.token = None
        self.cookies = None
        self.cache_file = cache_file
        self.cache_expire_hours = CACHE_EXPIRE_HOURS
        self.driver = None
        self.temp_user_data_dir = None

    def save_cache(self):
        """保存token和cookies到缓存文件"""
        if self.token and self.cookies:
            cache_data = {
                'token': self.token,
                'cookies': self.cookies,
                'timestamp': datetime.now().timestamp()
            }
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print(f"[OK] 登录信息已保存到缓存文件 {self.cache_file}")
                return True
            except Exception as e:
                print(f"[ERROR] 保存缓存失败: {e}")
                return False
        return False

    def load_cache(self):
        """从缓存文件加载token和cookies"""
        if not os.path.exists(self.cache_file):
            print("[INFO] 缓存文件不存在，需要重新登录")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            current_time = datetime.now()
            hours_diff = (current_time - cache_time).total_seconds() / 3600
            
            if hours_diff > self.cache_expire_hours:
                print(f"[INFO] 缓存已过期（{hours_diff:.1f}小时前），需要重新登录")
                return False
            
            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            print(f"[OK] 从缓存加载登录信息（{hours_diff:.1f}小时前保存）")
            return True
            
        except Exception as e:
            print(f"[ERROR] 读取缓存失败: {e}，需要重新登录")
            return False

    def validate_cache(self):
        """验证缓存的token和cookies是否仍然有效"""
        if not self.token or not self.cookies:
            return False
        
        try:
            headers = {
                "HOST": "mp.weixin.qq.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            }
            
            test_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
            test_params = {
                'action': 'search_biz', 
                'token': self.token, 
                'lang': 'zh_CN', 
                'f': 'json', 
                'ajax': '1',
                'random': random.random(), 
                'query': 'test', 
                'begin': '0', 
                'count': '1',
            }
            
            response = requests.get(
                test_url, 
                cookies=self.cookies, 
                headers=headers, 
                params=test_params, 
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            
            if 'base_resp' in result:
                if result['base_resp']['ret'] == 0:
                    print("[OK] 缓存的登录信息验证有效")
                    return True
                elif result['base_resp']['ret'] in (-6, 200013):
                    print("[WARN] 缓存的token已失效")
                    return False
                else:
                    print(f"[WARN] 验证失败: {result['base_resp'].get('err_msg', '未知错误')}")
                    return False
            else:
                print("[WARN] 验证响应格式异常")
                return False
                
        except Exception as e:
            print(f"[ERROR] 验证缓存时发生错误: {e}")
            return False

    def clear_cache(self):
        """清除缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("[OK] 缓存文件已清除")
                return True
        except Exception as e:
            print(f"[ERROR] 清除缓存失败: {e}")
        return False

    def _cleanup_chrome_processes(self):
        """清理Chrome进程（Windows专用）"""
        if platform.system() == "Windows":
            try:
                print("[INFO] 正在清理Chrome进程...")
                subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                time.sleep(1)  # 等待进程完全关闭
            except Exception as e:
                print(f"[WARN] 清理进程时出现警告: {e}")

    def _setup_chrome_options(self):
        """配置Chrome选项"""
        chrome_options = webdriver.ChromeOptions()
        
        # 用户代理
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        
        # 临时用户数据目录
        self.temp_user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
        if platform.system() == "Windows":
            self.temp_user_data_dir = self.temp_user_data_dir.replace("\\", "/")
        chrome_options.add_argument(f"--user-data-dir={self.temp_user_data_dir}")
        
        # 隐藏自动化特征
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 安全和性能选项
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument("--start-maximized")
        
        # Windows特定配置
        if platform.system() == "Windows":
            chrome_options.add_argument('--remote-debugging-port=0')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-renderer-backgrounding')
        
        return chrome_options

    def _cleanup_temp_files(self):
        """清理临时文件"""
        if self.temp_user_data_dir and os.path.exists(self.temp_user_data_dir):
            try:
                shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
                print("[OK] 临时用户数据目录已清理")
            except Exception as e:
                print(f"[WARN] 清理临时目录时出现警告: {e}")

    def login(self):
        """
        登录微信公众号平台
        
        Returns:
            bool: 登录是否成功
        """
        print("\n" + "="*60)
        print("开始登录微信公众号平台...")
        print("="*60)
        
        # 检查缓存
        if self.load_cache() and self.validate_cache():
            print("[OK] 使用有效的缓存登录信息")
            return True
        else:
            print("[INFO] 缓存无效或不存在，需要重新扫码登录")
            self.clear_cache()
        
        # 清理残留进程
        self._cleanup_chrome_processes()
        
        try:
            print("[INFO] 正在启动Chrome浏览器...")
            
            # 配置Chrome选项
            chrome_options = self._setup_chrome_options()
            
            # 创建WebDriver
            try:
                service = ChromeService()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("[OK] Chrome浏览器启动成功")
            except Exception as e:
                print(f"[ERROR] Chrome浏览器启动失败: {e}")
                return False

            # 隐藏自动化特征
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # 访问微信公众号平台
            print("[INFO] 正在访问微信公众号平台...")
            self.driver.get('https://mp.weixin.qq.com/')
            print("[OK] 页面加载完成")
            
            print("[INFO] 请在浏览器窗口中扫码登录...")
            print("[INFO] 等待登录完成（最长等待5分钟）...")

            # 等待登录成功（URL中包含token）
            wait = WebDriverWait(self.driver, 300)  # 5分钟超时
            wait.until(EC.url_contains('token'))
            
            # 提取token
            current_url = self.driver.current_url
            print("[OK] 检测到登录成功！正在获取登录信息...")
            
            token_match = re.search(r'token=(\d+)', current_url)
            if token_match:
                self.token = token_match.group(1)
                print(f"[OK] Token获取成功: {self.token}")
            else:
                print("[ERROR] 无法从URL中提取token")
                return False

            # 获取cookies
            raw_cookies = self.driver.get_cookies()
            self.cookies = {item['name']: item['value'] for item in raw_cookies}
            print(f"[OK] Cookies获取成功，共{len(self.cookies)}个")
            
            # 保存到缓存
            if self.save_cache():
                print("[OK] 登录信息已保存到缓存")
            
            print("[OK] 登录完成！")
            return True
            
        except Exception as e:
            print(f"[ERROR] 登录过程中出现错误: {e}")
            return False
            
        finally:
            # 清理资源
            if self.driver:
                try:
                    self.driver.quit()
                    print("[OK] 浏览器已关闭")
                except:
                    pass
            
            self._cleanup_chrome_processes()
            self._cleanup_temp_files()

    def check_login_status(self):
        """
        检查当前登录状态
        
        Returns:
            dict: 登录状态信息
        """
        if self.load_cache() and self.validate_cache():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_time = datetime.fromtimestamp(cache_data['timestamp'])
                expire_time = cache_time + timedelta(hours=self.cache_expire_hours)
                hours_since_login = (datetime.now() - cache_time).total_seconds() / 3600
                hours_until_expire = (expire_time - datetime.now()).total_seconds() / 3600
                
                return {
                    'isLoggedIn': True,
                    'loginTime': cache_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'expireTime': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'hoursSinceLogin': round(hours_since_login, 1),
                    'hoursUntilExpire': round(hours_until_expire, 1),
                    'token': self.token,
                    'message': f'已登录 {round(hours_since_login, 1)} 小时'
                }
            except:
                pass
        
        return {
            'isLoggedIn': False,
            'message': '未登录或登录已过期'
        }

    def logout(self):
        """
        退出登录
        
        Returns:
            bool: 退出是否成功
        """
        print("[INFO] 正在退出登录...")
        
        # 清除缓存和状态
        self.clear_cache()
        self.token = None
        self.cookies = None
        
        # 清理进程和临时文件
        self._cleanup_chrome_processes()
        self._cleanup_temp_files()
        
        print("[OK] 退出登录完成")
        return True

    def get_token(self):
        """
        获取token
        
        Returns:
            str: token字符串，如果未登录返回None
        """
        if not self.token and not (self.load_cache() and self.validate_cache()):
            return None
        return self.token

    def get_cookies(self):
        """
        获取cookies字典
        
        Returns:
            dict: cookies字典，如果未登录返回None
        """
        if not self.cookies and not (self.load_cache() and self.validate_cache()):
            return None
        return self.cookies

    def get_cookie_string(self):
        """
        获取cookie字符串格式
        
        Returns:
            str: cookie字符串，如果未登录返回None
        """
        cookies = self.get_cookies()
        if not cookies:
            return None
        
        cookie_string = '; '.join([f"{key}={value}" for key, value in cookies.items()])
        return cookie_string

    def get_headers(self):
        """
        获取标准的HTTP请求头
        
        Returns:
            dict: 包含cookie和user-agent的请求头，如果未登录返回None
        """
        cookie_string = self.get_cookie_string()
        if not cookie_string:
            return None
        
        return {
            "cookie": cookie_string,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

    def is_logged_in(self):
        """
        检查是否已登录
        
        Returns:
            bool: 是否已登录
        """
        return self.check_login_status()['isLoggedIn']


# 便捷函数
def quick_login():
    """
    快速登录函数
    
    Returns:
        tuple: (token, cookies, headers) 如果登录成功，否则返回 (None, None, None)
    """
    login_manager = WeChatLogin()
    if login_manager.login():
        return (
            login_manager.get_token(),
            login_manager.get_cookies(),
            login_manager.get_headers()
        )
    return (None, None, None)


def check_login():
    """
    检查登录状态的便捷函数
    
    Returns:
        dict: 登录状态信息
    """
    login_manager = WeChatLogin()
    return login_manager.check_login_status()


if __name__ == "__main__":
    # 测试代码 - 只在直接运行此文件时执行
    login_manager = WeChatLogin()
    
    # 检查登录状态
    status = login_manager.check_login_status()
    print("登录状态:", status)
    
    if not status['isLoggedIn']:
        # 尝试登录
        if login_manager.login():
            print("登录成功！")
            print("Token:", login_manager.get_token())
            print("Cookie字符串长度:", len(login_manager.get_cookie_string() or ""))
        else:
            print("登录失败！")
    else:
        print("已经登录，无需重新登录") 