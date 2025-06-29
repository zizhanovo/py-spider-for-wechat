# encoding: utf-8
"""
微信公众号文章抓取工具 - 桌面版

功能:
1. 支持配置多个公众号
2. 支持配置抓取的时间范围
3. 自动处理登录和缓存（缓存有效期可配）
4. 请求失败时会自动重试
5. 支持内容解析和SQLite数据库存储
6. 实时状态更新和日志输出
7. 可配置的随机延迟
"""

# 设置Windows兼容的UTF-8编码 - 增强版本
import sys
import os
import io
import locale

# 强制设置全局编码环境，解决Windows下所有编码问题
if sys.platform.startswith('win'):
    # 1. 设置控制台编码为UTF-8
    os.system('chcp 65001 >nul 2>&1')
    
    # 2. 设置环境变量强制UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    
    # 3. 设置locale为UTF-8
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass
    
    # 4. 重新包装stdout和stderr为UTF-8（最强力的修复）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            errors='replace',
            newline='\n',
            line_buffering=True
        )
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            errors='replace',
            newline='\n',
            line_buffering=True
        )
    
    # 5. 设置默认编码
    if hasattr(sys, '_getframe'):
        import codecs
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import re
import random
import time
import os
import csv
import logging
import argparse
import sqlite3
from datetime import datetime, date
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from bs4 import BeautifulSoup

# ====================================================================
# --- 配置区 ---
DEFAULT_ACCOUNTS = ["四二六人才发展院","IP云课堂","今日IP"]
DEFAULT_START_DATE = "2025-06-22"
DEFAULT_END_DATE = "2025-06-24"
CACHE_FILE = 'wechat_cache.json'
CACHE_EXPIRE_HOURS = 24 * 4  # 缓存有效期（小时），4天
RETRY_COUNT = 3  # 请求失败时的重试次数
RETRY_DELAY_SECONDS = 10  # 每次重试前的等待时间（秒）
LOG_FILE = 'wechat_scraper.log'
# --- 配置区结束 ---
# ====================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='微信公众号文章抓取工具')
    parser.add_argument('--accounts', type=str, help='公众号列表，用逗号分隔')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, default='.', help='输出目录')
    parser.add_argument('--random-delay', type=str, default='20,30', help='随机延迟范围，格式: min,max (最低20秒，最高300秒)')
    
    args = parser.parse_args()
    
    # 解析参数
    if args.accounts:
        accounts = [acc.strip() for acc in args.accounts.split(',')]
    else:
        accounts = DEFAULT_ACCOUNTS
    
    start_date = args.start if args.start else DEFAULT_START_DATE
    end_date = args.end if args.end else DEFAULT_END_DATE
    
    # 解析随机延迟
    delay_parts = args.random_delay.split(',')
    random_delay = (float(delay_parts[0]), float(delay_parts[1]))
    
    output_csv_file = os.path.join(args.output_dir, f'wechat_articles_{start_date}_to_{end_date}.csv')
    output_db_file = os.path.join(args.output_dir, 'wechat_articles.db')  # 使用统一的数据库文件名
    
    # 默认开启内容解析和数据库存储
    extract_content = True
    save_to_database = True
    
    return (accounts, start_date, end_date, output_csv_file, output_db_file, 
            random_delay, extract_content, save_to_database)

# 解析命令行参数
(OFFICIAL_ACCOUNTS, START_DATE, END_DATE, OUTPUT_CSV_FILE, OUTPUT_DB_FILE,
 RANDOM_DELAY, EXTRACT_CONTENT, SAVE_TO_DATABASE) = parse_args()

# --- 日志配置 ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 添加文件处理器
file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# --- 日志配置结束 ---


class DatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 创建主表，使用优化的表结构
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,  -- 防重复
                digest TEXT,
                publish_time TEXT,
                publish_timestamp INTEGER,  -- 用于快速时间范围查询
                content TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(link)  -- 防止重复抓取
            )
        ''')
        
        # 创建复合索引提升查询效率
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_time ON articles(account_name, publish_timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_range ON articles(publish_timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_name ON articles(account_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON articles(publish_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON articles(created_at)')
        
        # 创建全文搜索虚拟表（用于内容搜索）
        try:
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                    title, content, digest, 
                    content='articles', 
                    content_rowid='id'
                )
            ''')
            
            # 创建触发器保持FTS表同步
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                    INSERT INTO articles_fts(rowid, title, content, digest) 
                    VALUES (new.id, new.title, new.content, new.digest);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                    INSERT INTO articles_fts(articles_fts, rowid, title, content, digest) 
                    VALUES('delete', old.id, old.title, old.content, old.digest);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                    INSERT INTO articles_fts(articles_fts, rowid, title, content, digest) 
                    VALUES('delete', old.id, old.title, old.content, old.digest);
                    INSERT INTO articles_fts(rowid, title, content, digest) 
                    VALUES (new.id, new.title, new.content, new.digest);
                END
            ''')
            
            logger.info("✓ 全文搜索索引创建完成")
        except Exception as e:
            logger.warning(f"全文搜索索引创建失败（可能不支持FTS5）: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✓ 数据库初始化完成: {self.db_file}")
    
    def save_article(self, article):
        """保存文章到数据库"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (account_name, title, link, digest, content, publish_time, publish_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['name'],
                article['title'],
                article['link'],
                article['digest'],
                article.get('content', ''),
                article['publish_time'],
                article['publish_timestamp']
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"保存文章到数据库失败: {e}")
        finally:
            conn.close()
    
    def get_article_count(self):
        """获取文章总数"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM articles')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_articles_paginated(self, page=1, page_size=10, account_filter=None, 
                              date_range=None, sort_by='publish_timestamp', sort_order='DESC'):
        """分页查询文章，支持过滤和排序"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if account_filter:
            where_conditions.append('account_name LIKE ?')
            params.append(f'%{account_filter}%')
        
        if date_range and len(date_range) == 2:
            where_conditions.append('publish_timestamp >= ?')
            where_conditions.append('publish_timestamp <= ?')
            params.extend(date_range)
        
        where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        # 排序和分页
        order_clause = f' ORDER BY {sort_by} {sort_order}'
        limit_clause = f' LIMIT {page_size} OFFSET {(page - 1) * page_size}'
        
        # 获取总数
        count_query = f'SELECT COUNT(*) FROM articles{where_clause}'
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 获取数据
        data_query = f'''
            SELECT id, account_name, title, link, digest, publish_time, 
                   publish_timestamp, content, created_at 
            FROM articles{where_clause}{order_clause}{limit_clause}
        '''
        cursor.execute(data_query, params)
        articles = cursor.fetchall()
        
        conn.close()
        
        return {
            'articles': articles,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
    
    def search_articles_fulltext(self, search_term, page=1, page_size=10):
        """全文搜索文章"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # 使用FTS5全文搜索
            search_query = '''
                SELECT a.id, a.account_name, a.title, a.link, a.digest, 
                       a.publish_time, a.publish_timestamp, a.content, a.created_at,
                       articles_fts.rank
                FROM articles_fts 
                JOIN articles a ON articles_fts.rowid = a.id
                WHERE articles_fts MATCH ? 
                ORDER BY articles_fts.rank
                LIMIT ? OFFSET ?
            '''
            
            cursor.execute(search_query, (search_term, page_size, (page - 1) * page_size))
            articles = cursor.fetchall()
            
            # 获取搜索结果总数
            count_query = '''
                SELECT COUNT(*) FROM articles_fts WHERE articles_fts MATCH ?
            '''
            cursor.execute(count_query, (search_term,))
            total_count = cursor.fetchone()[0]
            
        except Exception as e:
            logger.warning(f"全文搜索失败，使用LIKE搜索: {e}")
            # 降级到LIKE搜索
            like_query = '''
                SELECT id, account_name, title, link, digest, publish_time, 
                       publish_timestamp, content, created_at
                FROM articles 
                WHERE title LIKE ? OR content LIKE ? OR digest LIKE ?
                ORDER BY publish_timestamp DESC
                LIMIT ? OFFSET ?
            '''
            search_pattern = f'%{search_term}%'
            cursor.execute(like_query, (search_pattern, search_pattern, search_pattern, 
                                      page_size, (page - 1) * page_size))
            articles = cursor.fetchall()
            
            count_query = '''
                SELECT COUNT(*) FROM articles 
                WHERE title LIKE ? OR content LIKE ? OR digest LIKE ?
            '''
            cursor.execute(count_query, (search_pattern, search_pattern, search_pattern))
            total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'articles': articles,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
    
    def get_account_stats(self):
        """获取账号统计信息"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT account_name, COUNT(*) as article_count,
                   MIN(publish_timestamp) as earliest,
                   MAX(publish_timestamp) as latest
            FROM articles 
            GROUP BY account_name 
            ORDER BY article_count DESC
        ''')
        
        stats = cursor.fetchall()
        conn.close()
        return stats
    
    def optimize_database(self):
        """优化数据库性能"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # 分析表和索引
            cursor.execute('ANALYZE')
            
            # 重建FTS索引
            cursor.execute('INSERT INTO articles_fts(articles_fts) VALUES("rebuild")')
            
            # 清理数据库
            cursor.execute('VACUUM')
            
            conn.commit()
            logger.info("✓ 数据库优化完成")
        except Exception as e:
            logger.warning(f"数据库优化失败: {e}")
        finally:
            conn.close()
    
    def generate_sql_from_natural_language(self, query_text, api_key=None, model="gpt-3.5-turbo", api_endpoint=None, api_port=None):
        """
        使用大模型将自然语言转换为SQL查询
        支持OpenAI API或其他兼容的API
        """
        import requests
        
        # 表结构信息
        table_schema = """
        表名: articles
        字段:
        - id: INTEGER (主键)
        - account_name: TEXT (公众号名称)
        - title: TEXT (文章标题) 
        - link: TEXT (文章链接)
        - digest: TEXT (文章摘要)
        - publish_time: TEXT (发布时间，格式：'2025-06-24 17:27:58')
        - publish_timestamp: INTEGER (发布时间戳)
        - content: TEXT (文章内容)
        - created_at: INTEGER (创建时间戳)
        
        索引:
        - idx_account_time: (account_name, publish_timestamp)
        - idx_time_range: (publish_timestamp) 
        - idx_account_name: (account_name)
        - idx_publish_time: (publish_time)
        """
        
        # 构建提示词
        system_prompt = f"""你是一个SQL查询生成专家。根据用户的自然语言描述，生成对应的SQLite查询语句。

数据库结构:
{table_schema}

规则:
1. 只生成SELECT查询，不允许UPDATE/DELETE/DROP等操作
2. 使用适当的WHERE条件、ORDER BY和LIMIT
3. 时间范围查询优先使用publish_timestamp字段
4. 模糊搜索使用LIKE操作符，格式：column LIKE '%keyword%'
5. 返回字段必须包括：id, account_name, title, link, digest, publish_time
6. 默认按时间倒序排列：ORDER BY publish_timestamp DESC
7. 添加合理的LIMIT限制结果数量（如未指定，默认20条）
8. 只返回SQL语句，不要包含其他文字

示例:
用户: "查找量子位发布的关于AI的文章"
SQL: SELECT id, account_name, title, link, digest, publish_time FROM articles WHERE account_name LIKE '%量子位%' AND (title LIKE '%AI%' OR content LIKE '%AI%' OR digest LIKE '%AI%') ORDER BY publish_timestamp DESC LIMIT 20

用户: "最近3天的文章，按公众号分组"
SQL: SELECT account_name, COUNT(*) as count, MAX(publish_time) as latest FROM articles WHERE publish_timestamp > strftime('%s', 'now', '-3 days') GROUP BY account_name ORDER BY count DESC

用户输入: {query_text}
SQL:"""

        try:
            if not api_key:
                # 尝试从环境变量获取API密钥
                import os
                api_key = os.getenv('OPENAI_API_KEY') or os.getenv('API_KEY')
                
            if not api_key:
                logger.error("未提供API密钥，请设置环境变量OPENAI_API_KEY或在调用时传入api_key参数")
                return None
            
            # 配置API端点
            if not api_endpoint:
                import os
                api_endpoint = os.getenv('OPENAI_API_ENDPOINT', 'https://api.openai.com')
            
            if not api_port:
                import os
                api_port = os.getenv('OPENAI_API_PORT', '443')
            
            # 构建完整的API URL
            if api_endpoint.endswith('/'):
                api_endpoint = api_endpoint[:-1]
            
            # 如果端点不包含端口，则添加端口
            if ':' not in api_endpoint.split('://')[-1]:
                if api_endpoint.startswith('https://') and api_port != '443':
                    api_url = f"{api_endpoint}:{api_port}/v1/chat/completions"
                elif api_endpoint.startswith('http://') and api_port != '80':
                    api_url = f"{api_endpoint}:{api_port}/v1/chat/completions"
                else:
                    api_url = f"{api_endpoint}/v1/chat/completions"
            else:
                api_url = f"{api_endpoint}/v1/chat/completions"
            
            logger.info(f"使用API端点: {api_url}")
            
            # 调用OpenAI API
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': query_text}
                ],
                'max_tokens': 500,
                'temperature': 0.1
            }
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                sql_query = result['choices'][0]['message']['content'].strip()
                
                # 清理SQL（移除可能的代码块标记）
                if sql_query.startswith('```sql'):
                    sql_query = sql_query[6:]
                if sql_query.startswith('```'):
                    sql_query = sql_query[3:]
                if sql_query.endswith('```'):
                    sql_query = sql_query[:-3]
                
                sql_query = sql_query.strip()
                logger.info(f"生成的SQL查询: {sql_query}")
                return sql_query
            else:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"生成SQL查询失败: {e}")
            return None
    
    def query_articles_by_natural_language(self, query_text, api_key=None, model="gpt-3.5-turbo", api_endpoint=None, api_port=None, additional_filters=None):
        """
        根据自然语言查询文章
        
        Args:
            query_text: 自然语言查询文本
            api_key: OpenAI API密钥
            model: 使用的模型
            api_endpoint: API端点
            api_port: API端口
            additional_filters: 额外的SQL筛选条件，会附加到生成的SQL末尾
        """
        # 生成SQL查询
        sql_query = self.generate_sql_from_natural_language(query_text, api_key, model, api_endpoint, api_port)
        if not sql_query:
            return {
                'success': False,
                'error': 'SQL生成失败',
                'articles': [],
                'total': 0
            }
        
        # 如果有额外的筛选条件，拼接到SQL末尾
        if additional_filters and additional_filters.strip():
            # 清理SQL，移除末尾的分号
            sql_query = sql_query.rstrip(';').rstrip()
            
            # 解析SQL，找到ORDER BY和LIMIT的位置
            sql_upper = sql_query.upper()
            
            # 查找ORDER BY和LIMIT的位置
            order_by_pos = sql_upper.find(' ORDER BY ')
            limit_pos = sql_upper.find(' LIMIT ')
            
            # 确定插入位置
            if order_by_pos != -1:
                insert_pos = order_by_pos
                remaining_sql = sql_query[insert_pos:]
            elif limit_pos != -1:
                insert_pos = limit_pos
                remaining_sql = sql_query[insert_pos:]
            else:
                insert_pos = len(sql_query)
                remaining_sql = ''
            
            # 获取主查询部分
            main_query = sql_query[:insert_pos]
            
            # 处理筛选条件
            filter_condition = additional_filters.strip()
            
            # 检查主查询是否已经有WHERE子句
            main_query_upper = main_query.upper()
            if 'WHERE' in main_query_upper:
                # 已有WHERE子句，使用AND连接
                sql_query = main_query + f" {filter_condition}" + remaining_sql
            else:
                # 没有WHERE子句，添加WHERE关键字
                if filter_condition.startswith('AND '):
                    filter_condition = filter_condition[4:]  # 移除开头的"AND "
                sql_query = main_query + f" WHERE {filter_condition}" + remaining_sql
        
        # 安全检查：确保只允许SELECT查询
        sql_upper = sql_query.upper().strip()
        if not sql_upper.startswith('SELECT'):
            logger.warning(f"非法SQL查询被拦截: {sql_query}")
            return {
                'success': False,
                'error': '只允许SELECT查询',
                'articles': [],
                'total': 0
            }
        
        # 检查是否包含危险操作
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'EXEC']
        if any(keyword in sql_upper for keyword in dangerous_keywords):
            logger.warning(f"包含危险关键词的SQL查询被拦截: {sql_query}")
            return {
                'success': False,
                'error': '查询包含不允许的操作',
                'articles': [],
                'total': 0
            }
        
        # 执行查询
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            logger.info(f"执行SQL查询: {sql_query}")
            cursor.execute(sql_query)
            articles = cursor.fetchall()
            
            # 获取列名
            column_names = [description[0] for description in cursor.description]
            
            # 转换为字典格式
            articles_list = []
            for row in articles:
                article_dict = dict(zip(column_names, row))
                
                # 字段名映射，确保与前端期望一致
                mapped_article = {
                    'name': article_dict.get('account_name', ''),  # 映射 account_name -> name
                    'title': article_dict.get('title', ''),
                    'link': article_dict.get('link', ''),
                    'digest': article_dict.get('digest', ''),
                    'publish_time': article_dict.get('publish_time', ''),
                    'content': article_dict.get('content', ''),
                    'publish_timestamp': article_dict.get('publish_timestamp', 0)
                }
                articles_list.append(mapped_article)
            
            conn.close()
            
            return {
                'success': True,
                'articles': articles_list,
                'total': len(articles_list),
                'sql_query': sql_query,
                'query_text': query_text,
                'additional_filters': additional_filters
            }
            
        except Exception as e:
            conn.close()
            logger.error(f"执行SQL查询失败: {e}")
            return {
                'success': False,
                'error': f'查询执行失败: {str(e)}',
                'articles': [],
                'total': 0,
                'sql_query': sql_query
            }


class ContentExtractor:
    """文章内容提取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        })
    
    def extract_content(self, url):
        """提取文章内容"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 尝试找到文章内容区域
            content_selectors = [
                'div#js_content',
                'div.rich_media_content',
                'div.article-content',
                'div.content',
                'div.post-content'
            ]
            
            content_text = ''
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    # 移除脚本和样式标签
                    for script in content_div(['script', 'style']):
                        script.decompose()
                    
                    content_text = content_div.get_text(strip=True)
                    break
            
            if not content_text:
                # 如果没有找到特定的内容区域，获取body文本
                body = soup.find('body')
                if body:
                    content_text = body.get_text(strip=True)
            
            return content_text[:5000] if content_text else ''  # 限制长度
            
        except Exception as e:
            logger.warning(f"提取内容失败 {url}: {e}")
            return ''


class WeChatScraper:
    """微信公众号文章抓取器"""

    def __init__(self):
        self.token = None
        self.cookies = None
        self.cache_file = CACHE_FILE
        self.cache_expire_hours = CACHE_EXPIRE_HOURS
        self.db_manager = None
        self.content_extractor = None
        
        if SAVE_TO_DATABASE:
            self.db_manager = DatabaseManager(OUTPUT_DB_FILE)
        
        if EXTRACT_CONTENT:
            self.content_extractor = ContentExtractor()
        
        # 加载登录信息
        self.load_cache()

    def send_status_update(self, account_name, status, articles_found=0, current_page=0, error=None):
        """发送账号状态更新"""
        status_data = {
            'name': account_name,
            'status': status,
            'articlesFound': articles_found,
            'currentPage': current_page
        }
        if error:
            status_data['error'] = error
        
        print(f"ACCOUNT_STATUS:{json.dumps(status_data)}")

    def _make_request(self, url, params, headers, request_name="请求"):
        """发起网络请求，支持重试"""
        for i in range(RETRY_COUNT + 1):
            try:
                response = requests.get(url, cookies=self.cookies, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"[{request_name}] 第 {i+1} 次请求失败: {e}")
                if i < RETRY_COUNT:
                    logger.info(f"将在 {RETRY_DELAY_SECONDS} 秒后重试...")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"[{request_name}] 重试 {RETRY_COUNT} 次后仍然失败。")
                    return None

    def load_cache(self):
        """从缓存文件加载token和cookies"""
        if not os.path.exists(self.cache_file):
            logger.error("登录缓存文件不存在，请先登录")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            current_time = datetime.now()
            hours_diff = (current_time - cache_time).total_seconds() / 3600
            
            if hours_diff > self.cache_expire_hours:
                logger.error(f"登录缓存已过期（{hours_diff:.1f}小时前），请重新登录")
                return False
            
            # 检查是否有有效的cookies
            if not cache_data.get('cookies') or not isinstance(cache_data['cookies'], dict) or len(cache_data['cookies']) == 0:
                logger.error("登录信息不完整，缺少必要的cookies。请在应用中点击【登录微信】按钮进行完整登录。")
                return False
            
            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            logger.info(f"✓ 加载登录缓存成功（{hours_diff:.1f}小时前保存）")
            return True
            
        except Exception as e:
            logger.error(f"读取登录缓存失败: {e}，请重新登录")
            return False

    @staticmethod
    def parse_date(date_str):
        """将 'YYYY-MM-DD' 格式的字符串解析为 date 对象"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"日期格式错误，应为 'YYYY-MM-DD'，收到: {date_str}")
            return None

    @staticmethod
    def format_timestamp(timestamp):
        """将时间戳转换为可读格式"""
        try:
            if timestamp:
                return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            return ''
        except Exception:
            return ''

    @staticmethod
    def is_in_date_range(timestamp, start_date, end_date):
        """判断文章是否在指定日期范围内"""
        try:
            if timestamp:
                article_date = datetime.fromtimestamp(int(timestamp)).date()
                return start_date <= article_date <= end_date
            return False
        except Exception:
            return False

    def extract_article_info(self, article_item, official_account):
        """提取文章的关键信息"""
        publish_timestamp = article_item.get('create_time')
        
        article_info = {
            'name': official_account,
            'title': article_item.get('title', '').strip(),
            'link': article_item.get('link', ''),
            'digest': article_item.get('digest', '').strip(),
            'publish_time': self.format_timestamp(publish_timestamp),
            'publish_timestamp': publish_timestamp
        }
        
        # 如果需要提取内容
        if EXTRACT_CONTENT and self.content_extractor and article_info['link']:
            logger.info(f"正在提取文章内容: {article_info['title']}")
            article_info['content'] = self.content_extractor.extract_content(article_info['link'])
            time.sleep(random.uniform(1, 2))  # 短暂延迟避免频繁请求
        
        return article_info

    def scrape_articles_by_account(self, official_account, start_date, end_date):
        """抓取单个公众号在指定时间范围内的文章"""
        header = {
            "HOST": "mp.weixin.qq.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }

        # 更新状态为处理中
        self.send_status_update(official_account, 'processing')

        # 1. 搜索公众号，获取fakeid
        logger.info(f"[{official_account}] 正在搜索公众号...")
        search_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
        search_params = {
            'action': 'search_biz', 'token': self.token, 'lang': 'zh_CN', 'f': 'json', 'ajax': '1',
            'random': random.random(), 'query': official_account, 'begin': '0', 'count': '5',
        }
        
        search_response = self._make_request(search_url, search_params, header, f"[{official_account}] 搜索")
        if not search_response:
            self.send_status_update(official_account, 'error', error='搜索请求失败')
            return []

        try:
            search_result = search_response.json()
            if 'base_resp' in search_result and search_result['base_resp']['ret'] != 0:
                error_msg = search_result['base_resp']['err_msg']
                logger.error(f"[{official_account}] 搜索公众号失败: {error_msg}")
                self.send_status_update(official_account, 'error', error=error_msg)
                return []
            if not search_result.get('list'):
                logger.warning(f"[{official_account}] 未搜索到公众号")
                self.send_status_update(official_account, 'error', error='未找到公众号')
                return []
            fakeid = search_result['list'][0].get('fakeid')
            logger.info(f"[{official_account}] 成功获取公众号的 fakeid: {fakeid}")
        except json.JSONDecodeError:
            logger.error(f"[{official_account}] 搜索结果解析JSON失败: {search_response.text}")
            self.send_status_update(official_account, 'error', error='JSON解析失败')
            return []
        except Exception as e:
            logger.error(f"[{official_account}] 处理搜索结果时发生未知错误: {e}", exc_info=True)
            self.send_status_update(official_account, 'error', error=str(e))
            return []

        # 2. 获取文章列表
        logger.info(f"[{official_account}] 开始获取文章, 时间范围: {start_date} 到 {end_date}...")
        appmsg_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg'
        begin = 0
        articles_in_range = []
        has_more = True

        while has_more:
            # 更新当前页状态
            current_page = begin // 5 + 1
            self.send_status_update(official_account, 'processing', len(articles_in_range), current_page)
            
            list_params = {
                'token': self.token, 'lang': 'zh_CN', 'f': 'json', 'ajax': '1', 'random': random.random(),
                'action': 'list_ex', 'begin': str(begin), 'count': '5', 'query': '', 'fakeid': fakeid, 'type': '9'
            }

            list_response = self._make_request(appmsg_url, list_params, header, f"[{official_account}] 获取文章列表 (第 {current_page} 页)")
            if not list_response:
                self.send_status_update(official_account, 'error', len(articles_in_range), current_page, '请求失败')
                break

            try:
                list_data = list_response.json()
                if 'base_resp' in list_data and list_data['base_resp']['ret'] != 0:
                    err_msg = list_data['base_resp'].get('err_msg', '未知错误')
                    logger.error(f"[{official_account}] 获取文章列表失败: {err_msg}")
                    if list_data['base_resp']['ret'] in (200013, -6):
                        raise SystemExit("Token 失效，请删除缓存文件后重新运行程序。")
                    self.send_status_update(official_account, 'error', len(articles_in_range), current_page, err_msg)
                    break

                if 'app_msg_list' in list_data and list_data['app_msg_list']:
                    if begin == 0:
                        total_articles = list_data.get('app_msg_cnt', 0)
                        logger.info(f"[{official_account}] 该公众号总共有 {total_articles} 篇文章。")

                    app_msg_list = list_data['app_msg_list']
                    
                    for item in app_msg_list:
                        publish_timestamp = item.get('create_time')
                        article_date = datetime.fromtimestamp(int(publish_timestamp)).date()
                        
                        if article_date < start_date:
                            logger.info(f"[{official_account}] 文章 '{item.get('title')}' ({self.format_timestamp(publish_timestamp)}) 早于指定开始日期，停止抓取。")
                            has_more = False
                            break
                        
                        if self.is_in_date_range(publish_timestamp, start_date, end_date):
                            article_info = self.extract_article_info(item, official_account)
                            articles_in_range.append(article_info)
                            logger.info(f"✓ [{official_account}] 找到范围内的文章: {article_info['title']}")
                            
                            # 保存到数据库
                            if self.db_manager:
                                self.db_manager.save_article(article_info)

                    if not app_msg_list or len(app_msg_list) < 5:
                        has_more = False
                    
                    if has_more:
                        begin += 5
                        delay = random.uniform(*RANDOM_DELAY)
                        logger.info(f"[{official_account}] 继续获取下一页... (延迟 {delay:.2f} 秒)")
                        time.sleep(delay)
                else:
                    logger.info(f"[{official_account}] 未获取到更多文章，抓取结束。")
                    has_more = False
            except json.JSONDecodeError:
                logger.error(f"[{official_account}] 文章列表解析JSON失败: {list_response.text}")
                self.send_status_update(official_account, 'error', len(articles_in_range), current_page, 'JSON解析失败')
                break
            except SystemExit as e:
                raise e
            except Exception as e:
                logger.error(f"[{official_account}] 处理文章列表时发生未知错误: {e}", exc_info=True)
                self.send_status_update(official_account, 'error', len(articles_in_range), current_page, str(e))
                break

        # 标记为完成
        self.send_status_update(official_account, 'completed', len(articles_in_range))
        return articles_in_range

    def save_to_csv(self, articles, filename):
        """将文章数据保存到CSV文件"""
        if not articles:
            return
            
        fieldnames = ['name', 'title', 'link', 'digest', 'publish_time', 'publish_timestamp']
        if EXTRACT_CONTENT:
            fieldnames.append('content')
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
            logger.info(f"\n✓ 成功将 {len(articles)} 篇文章保存到CSV文件: {filename}")
        except Exception as e:
            logger.error(f"保存CSV文件时出错: {e}", exc_info=True)

    def run(self):
        """主运行函数"""
        start_date = self.parse_date(START_DATE)
        end_date = self.parse_date(END_DATE)

        if not start_date or not end_date:
            logger.error("日期格式错误，程序终止。")
            return

        if start_date > end_date:
            logger.error("开始日期不能晚于结束日期，程序终止。")
            return
            
        if not self.token or not self.cookies:
            logger.error("未找到有效的登录信息，请先登录。")
            return

        all_results = []
        try:
            for i, account in enumerate(OFFICIAL_ACCOUNTS):
                logger.info("\n" + "="*80 + f"\n[*] 开始处理公众号 ({i+1}/{len(OFFICIAL_ACCOUNTS)}): {account}\n" + "="*80)
                
                # 设置状态为等待中
                self.send_status_update(account, 'pending')
                
                account_articles = self.scrape_articles_by_account(account, start_date, end_date)
                all_results.extend(account_articles)
                
                logger.info(f"[*] 公众号 '{account}' 处理完毕，找到 {len(account_articles)} 篇文章。")
                if len(OFFICIAL_ACCOUNTS) > 1 and i < len(OFFICIAL_ACCOUNTS) - 1:
                    delay = random.uniform(15, 20)  # 公众号之间的延迟
                    logger.info(f"暂停 {delay:.2f} 秒后继续...")
                    time.sleep(delay)

        except SystemExit as e:
            logger.critical(f"\n! 系统中止: {e}")
        except KeyboardInterrupt:
            logger.warning("\n! 用户手动中断程序。")
        finally:
            logger.info("\n" + "="*80 + "\n所有公众号抓取任务完成。\n" + "="*80)
            if all_results:
                logger.info(f"总共找到 {len(all_results)} 篇文章。")
                # 保存CSV文件
                self.save_to_csv(all_results, OUTPUT_CSV_FILE)
                
                # 如果使用数据库，输出统计信息
                if self.db_manager:
                    total_count = self.db_manager.get_article_count()
                    logger.info(f"数据库中共有 {total_count} 篇文章")
            else:
                logger.info("在指定时间范围内没有找到任何文章。")
            
            logger.info(f"详细日志请查看文件: {LOG_FILE}")
            logger.info("="*80)


if __name__ == '__main__':
    logger.info(f"[*] 目标公众号: {', '.join(OFFICIAL_ACCOUNTS)}")
    logger.info(f"[*] 抓取时间范围: {START_DATE} to {END_DATE}")
    logger.info(f"[*] 随机延迟: {RANDOM_DELAY[0]}-{RANDOM_DELAY[1]}秒")
    logger.info(f"[*] 解析内容: {'是' if EXTRACT_CONTENT else '否'}")
    logger.info(f"[*] 保存到数据库: {'是' if SAVE_TO_DATABASE else '否'}")
    
    scraper = WeChatScraper()
    scraper.run()
