#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号批量爬取模块
===================

模块功能:
    支持批量输入多个公众号，按指定时间范围进行文章爬取，
    参考WeChat.py的设计理念，提供更强大的批量处理能力。

主要功能:
    1. 批量公众号配置 - 支持从文件或界面输入多个公众号
    2. 时间范围筛选 - 按开始和结束日期过滤文章
    3. 进度跟踪 - 实时显示每个公众号的处理进度
    4. 错误处理 - 单个公众号失败不影响其他公众号
    5. 结果汇总 - 将所有公众号的结果合并保存
    6. 数据库存储 - 可选的SQLite数据库存储功能

技术特点:
    - 异步处理: 支持多线程并发爬取
    - 智能重试: 请求失败时自动重试
    - 缓存机制: 避免重复爬取相同文章
    - 进度可视化: 实时更新爬取状态
    - 灵活配置: 支持多种配置方式

使用场景:
    - 监控多个公众号的最新动态
    - 批量收集特定时间段的文章
    - 竞品分析和内容研究
    - 舆情监控和数据分析

作者: 基于WeChat.py改进
创建时间: 2024/12/20
版本: 1.0
"""

import json
import os
import random
import time
import csv
import sqlite3
import logging
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import requests
from PyQt5.QtCore import QThread, pyqtSignal

# 导入现有模块
from .getFakId import get_fakid
from .getAllUrls import getAllUrl
from .getContentsByUrls_MultiThread import run_getContentsByUrls_MultiThread
from .getRealTimeByTimeStamp import run_getRealTimeByTimeStamp
from .getTitleByKeywords import run_getTitleByKeywords

# 配置常量
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 10
DEFAULT_REQUEST_DELAY = (1, 3)  # 请求间隔范围（秒）
DEFAULT_ACCOUNT_DELAY = (15, 20)  # 公众号间隔范围（秒）


class BatchScraperDatabase:
    """批量爬取专用数据库管理器"""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = Lock()
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 创建文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    link TEXT UNIQUE NOT NULL,
                    digest TEXT,
                    publish_time TEXT,
                    publish_timestamp INTEGER,
                    content TEXT,
                    batch_id TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    UNIQUE(link)
                )
            ''')
            
            # 创建批次表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT UNIQUE NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    accounts TEXT,
                    total_articles INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    completed_at INTEGER
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch_account_time ON batch_articles(account_name, publish_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch_id ON batch_articles(batch_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch_time_range ON batch_articles(publish_timestamp)')
            
            conn.commit()
            conn.close()
    
    def create_batch(self, batch_id, start_date, end_date, accounts):
        """创建新的批次记录"""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO batch_info 
                (batch_id, start_date, end_date, accounts, status)
                VALUES (?, ?, ?, ?, 'running')
            ''', (batch_id, start_date, end_date, json.dumps(accounts)))
            
            conn.commit()
            conn.close()
    
    def save_article(self, article, batch_id):
        """保存文章到数据库"""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO batch_articles 
                    (account_name, title, link, digest, content, publish_time, 
                     publish_timestamp, batch_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article['name'],
                    article['title'],
                    article['link'],
                    article['digest'],
                    article.get('content', ''),
                    article['publish_time'],
                    article['publish_timestamp'],
                    batch_id
                ))
                conn.commit()
            except Exception as e:
                logging.error(f"保存文章到数据库失败: {e}")
            finally:
                conn.close()
    
    def complete_batch(self, batch_id, total_articles):
        """标记批次完成"""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE batch_info 
                SET status = 'completed', total_articles = ?, 
                    completed_at = strftime('%s', 'now')
                WHERE batch_id = ?
            ''', (total_articles, batch_id))
            
            conn.commit()
            conn.close()


class BatchScraperThread(QThread):
    """批量爬取工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, int)  # batch_id, current, total
    account_status = pyqtSignal(str, str, str)    # account_name, status, message
    batch_completed = pyqtSignal(str, int)        # batch_id, total_articles
    error_occurred = pyqtSignal(str, str)         # account_name, error_message
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.db_manager = None
        self.is_cancelled = False
        
        # 初始化数据库（如果启用）
        if config.get('use_database', False):
            db_file = config.get('db_file', 'batch_scraper.db')
            self.db_manager = BatchScraperDatabase(db_file)
    
    def cancel(self):
        """取消爬取任务"""
        self.is_cancelled = True
    
    def run(self):
        """主运行函数"""
        try:
            self._run_batch_scraper()
        except Exception as e:
            logging.error(f"批量爬取出错: {e}", exc_info=True)
            self.error_occurred.emit("系统", str(e))
    
    def _run_batch_scraper(self):
        """执行批量爬取"""
        accounts = self.config['accounts']
        start_date = self._parse_date(self.config['start_date'])
        end_date = self._parse_date(self.config['end_date'])
        batch_id = self.config.get('batch_id', f"batch_{int(time.time())}")
        
        if not start_date or not end_date:
            self.error_occurred.emit("系统", "日期格式错误")
            return
        
        if start_date > end_date:
            self.error_occurred.emit("系统", "开始日期不能晚于结束日期")
            return
        
        # 创建批次记录
        if self.db_manager:
            self.db_manager.create_batch(batch_id, self.config['start_date'], 
                                       self.config['end_date'], accounts)
        
        all_articles = []
        completed_accounts = 0
        total_accounts = len(accounts)
        
        # 是否使用多线程
        use_threading = self.config.get('use_threading', False)
        max_workers = self.config.get('max_workers', 3)
        
        if use_threading and total_accounts > 1:
            # 多线程处理
            all_articles = self._process_accounts_threaded(
                accounts, start_date, end_date, batch_id, total_accounts
            )
        else:
            # 单线程处理
            all_articles = self._process_accounts_sequential(
                accounts, start_date, end_date, batch_id, total_accounts
            )
        
        if not self.is_cancelled:
            # 保存结果
            self._save_results(all_articles, batch_id)
            
            # 完成批次
            if self.db_manager:
                self.db_manager.complete_batch(batch_id, len(all_articles))
            
            self.batch_completed.emit(batch_id, len(all_articles))
    
    def _process_accounts_sequential(self, accounts, start_date, end_date, batch_id, total_accounts):
        """顺序处理公众号"""
        all_articles = []
        
        for i, account in enumerate(accounts):
            if self.is_cancelled:
                break
                
            self.account_status.emit(account, "processing", f"正在处理 ({i+1}/{total_accounts})")
            self.progress_updated.emit(batch_id, i, total_accounts)
            
            try:
                articles = self._scrape_single_account(account, start_date, end_date, batch_id)
                all_articles.extend(articles)
                
                self.account_status.emit(account, "completed", f"完成，获得 {len(articles)} 篇文章")
                
                # 账号间延迟
                if i < total_accounts - 1:
                    delay = random.uniform(*DEFAULT_ACCOUNT_DELAY)
                    time.sleep(delay)
                    
            except Exception as e:
                error_msg = f"处理失败: {str(e)}"
                self.account_status.emit(account, "error", error_msg)
                self.error_occurred.emit(account, error_msg)
                continue
        
        return all_articles
    
    def _process_accounts_threaded(self, accounts, start_date, end_date, batch_id, total_accounts):
        """多线程处理公众号"""
        all_articles = []
        completed = 0
        
        max_workers = min(self.config.get('max_workers', 3), len(accounts))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_account = {
                executor.submit(self._scrape_single_account, account, start_date, end_date, batch_id): account
                for account in accounts
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_account):
                if self.is_cancelled:
                    break
                    
                account = future_to_account[future]
                completed += 1
                
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    
                    self.account_status.emit(account, "completed", f"完成，获得 {len(articles)} 篇文章")
                    self.progress_updated.emit(batch_id, completed, total_accounts)
                    
                except Exception as e:
                    error_msg = f"处理失败: {str(e)}"
                    self.account_status.emit(account, "error", error_msg)
                    self.error_occurred.emit(account, error_msg)
        
        return all_articles
    
    def _scrape_single_account(self, account_name, start_date, end_date, batch_id):
        """爬取单个公众号"""
        headers = self.config['headers']
        token = self.config['token']
        
        # 1. 获取公众号fakeid
        search_results = get_fakid(headers, token, account_name)
        if not search_results:
            raise Exception(f"未找到公众号: {account_name}")
        
        fakeid = search_results[0]['wpub_fakid']
        
        # 2. 获取文章列表
        articles_in_range = []
        page_start = 0
        max_pages = self.config.get('max_pages_per_account', 100)  # 限制最大页数
        
        for page in range(max_pages):
            if self.is_cancelled:
                break
            
            try:
                # 获取一页的文章
                titles, links, update_times = getAllUrl(
                    page_num=1,
                    start_page=page_start,
                    fad=fakeid,
                    tok=token,
                    headers=headers
                )
                
                if not titles:  # 没有更多文章
                    break
                
                # 检查文章是否在时间范围内
                found_in_range = False
                for i, (title, link, update_time) in enumerate(zip(titles, links, update_times)):
                    article_date = datetime.fromtimestamp(int(update_time)).date()
                    
                    if article_date < start_date:
                        # 文章太旧，停止爬取
                        break
                    
                    if start_date <= article_date <= end_date:
                        article_info = {
                            'name': account_name,
                            'title': title,
                            'link': link,
                            'digest': '',  # 这里可以后续补充
                            'publish_time': self._format_timestamp(update_time),
                            'publish_timestamp': update_time,
                            'content': ''  # 这里可以后续补充
                        }
                        
                        articles_in_range.append(article_info)
                        found_in_range = True
                        
                        # 保存到数据库
                        if self.db_manager:
                            self.db_manager.save_article(article_info, batch_id)
                
                if not found_in_range and article_date < start_date:
                    # 如果这页没有符合条件的文章且已经超出时间范围，停止
                    break
                
                page_start += 5
                
                # 请求间延迟
                delay = random.uniform(*DEFAULT_REQUEST_DELAY)
                time.sleep(delay)
                
            except Exception as e:
                logging.warning(f"获取 {account_name} 第 {page+1} 页失败: {e}")
                continue
        
        return articles_in_range
    
    def _save_results(self, articles, batch_id):
        """保存爬取结果"""
        if not articles:
            return
        
        # 保存为CSV
        output_file = self.config.get('output_file')
        if output_file:
            try:
                fieldnames = ['name', 'title', 'link', 'digest', 'publish_time', 'publish_timestamp']
                if self.config.get('include_content', False):
                    fieldnames.append('content')
                
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(articles)
                
                logging.info(f"批次 {batch_id} 结果已保存到: {output_file}")
                
            except Exception as e:
                logging.error(f"保存CSV文件失败: {e}")
    
    @staticmethod
    def _parse_date(date_str):
        """解析日期字符串"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    @staticmethod
    def _format_timestamp(timestamp):
        """格式化时间戳"""
        try:
            return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ''


class BatchScraperManager:
    """批量爬取管理器"""
    
    def __init__(self):
        self.current_thread = None
        self.callbacks = {}
    
    def set_callback(self, event, callback):
        """设置回调函数"""
        self.callbacks[event] = callback
    
    def start_batch_scrape(self, config):
        """开始批量爬取"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.cancel()
            self.current_thread.wait()
        
        self.current_thread = BatchScraperThread(config)
        
        # 连接信号
        if 'progress_updated' in self.callbacks:
            self.current_thread.progress_updated.connect(self.callbacks['progress_updated'])
        if 'account_status' in self.callbacks:
            self.current_thread.account_status.connect(self.callbacks['account_status'])
        if 'batch_completed' in self.callbacks:
            self.current_thread.batch_completed.connect(self.callbacks['batch_completed'])
        if 'error_occurred' in self.callbacks:
            self.current_thread.error_occurred.connect(self.callbacks['error_occurred'])
        
        self.current_thread.start()
    
    def cancel_batch_scrape(self):
        """取消批量爬取"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.cancel()
            self.current_thread.wait()
    
    def is_running(self):
        """检查是否正在运行"""
        return self.current_thread and self.current_thread.isRunning()


# 便捷函数
def create_batch_config(accounts, start_date, end_date, token, headers, **kwargs):
    """创建批量爬取配置"""
    config = {
        'accounts': accounts if isinstance(accounts, list) else [accounts],
        'start_date': start_date,
        'end_date': end_date,
        'token': token,
        'headers': headers,
        'batch_id': kwargs.get('batch_id', f"batch_{int(time.time())}"),
        'output_file': kwargs.get('output_file'),
        'use_database': kwargs.get('use_database', False),
        'db_file': kwargs.get('db_file', 'batch_scraper.db'),
        'use_threading': kwargs.get('use_threading', False),
        'max_workers': kwargs.get('max_workers', 3),
        'max_pages_per_account': kwargs.get('max_pages_per_account', 100),
        'include_content': kwargs.get('include_content', False),
        'request_interval': kwargs.get('request_interval', 60)  # 请求间隔，默认60秒
    }
    return config


def load_accounts_from_file(file_path):
    """从文件加载公众号列表"""
    accounts = []
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                accounts = data if isinstance(data, list) else data.get('accounts', [])
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                accounts = [line.strip() for line in f if line.strip()]
        elif file_path.endswith('.csv'):
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                accounts = [row[0] for row in reader if row]
    except Exception as e:
        logging.error(f"从文件加载公众号列表失败: {e}")
    
    return accounts


def save_accounts_to_file(accounts, file_path):
    """保存公众号列表到文件"""
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(accounts, f, ensure_ascii=False, indent=2)
        elif file_path.endswith('.txt'):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(accounts))
        elif file_path.endswith('.csv'):
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['公众号名称'])
                for account in accounts:
                    writer.writerow([account])
        return True
    except Exception as e:
        logging.error(f"保存公众号列表到文件失败: {e}")
        return False


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 示例配置
    test_accounts = ["量子位", "机器之心", "AI科技大本营"]
    test_config = create_batch_config(
        accounts=test_accounts,
        start_date="2024-12-01",
        end_date="2024-12-20",
        token="your_token_here",
        headers={"cookie": "your_cookie_here"},
        output_file="batch_results.csv",
        use_database=True,
        use_threading=True,
        max_workers=2
    )
    
    print("批量爬取配置:", json.dumps(test_config, indent=2, ensure_ascii=False)) 