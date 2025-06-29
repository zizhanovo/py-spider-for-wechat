#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号爬虫 - 统一GUI界面
============================

整合了单个公众号爬取和批量爬取功能的统一界面，
使用标签页组织不同功能，提供更清晰的用户体验。

主要功能:
    1. 单个爬取 - 传统的单个公众号文章爬取
    2. 批量爬取 - 多公众号、时间范围的批量爬取
    3. 自动登录 - 一键获取token和cookie
    4. 设置管理 - 统一的配置和设置

作者: 基于main.py和batch_scraper_gui.py整合
创建时间: 2024/12/20
版本: 2.0
"""

import sys
import os
import datetime
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QGroupBox, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QSpinBox,
                            QComboBox, QProgressBar, QTextBrowser, QCheckBox,
                            QDateEdit, QListWidget, QTableWidget, QTableWidgetItem,
                            QHeaderView, QFileDialog, QMessageBox, QSplitter,
                            QFrame)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# 导入业务逻辑模块
from utils.getFakId import get_fakid
from utils.getAllUrls import run_getAllUrls
from utils.getContentsByUrls_MultiThread import run_getContentsByUrls_MultiThread
from utils.getRealTimeByTimeStamp import run_getRealTimeByTimeStamp
from utils.getTitleByKeywords import run_getTitleByKeywords

# 导入自动登录和批量爬取模块
try:
    from utils.wechat_login import WeChatLogin
    AUTO_LOGIN_AVAILABLE = True
except ImportError:
    AUTO_LOGIN_AVAILABLE = False

try:
    from utils.batch_scraper import (BatchScraperManager, create_batch_config, 
                                   load_accounts_from_file, save_accounts_to_file)
    BATCH_SCRAPER_AVAILABLE = True
except ImportError:
    BATCH_SCRAPER_AVAILABLE = False

# 全局配置
dic = {
    "page_start": None, "page_num": None, "savepath": None,
    "tok": None, "fad": None, "headers": None,
    "filename": None, "keywords": None
}

log_info = {
    "start": ["开始爬取...", 0],
    "url": ["正在获取所有文章url...", 0],
    "content": ["正在根据所有文章的url获取文章内容...", 25],
    "timestamp": ["正在进行时间戳转换...", 75],
    "keywords": ["正在根据关键词筛选文章...", 90],
    "finish": ["爬取完成！", 100],
    "tok_null": ["token不能为空！", 0],
    "cok_null": ["cookie不能为空！", 0],
    "wpub_name_null": ['查询的公众号名不能为空！', 0],
    "frequent": ["请检查token、cookie是否正确；如正确则由于请求次数过多，需要您稍后重试！", 0],
    "res_null": ["无公众号匹配，请更换公众号名称", 0],
    "page_num_null": ["爬取页数不能为0！", 0],
    "savepath_null": ["文件保存位置不能为空！", 0],
    "fad_null": ["选择公众号不能为空！", 0],
    "filename_null": ["保存文件名不能为空！", 0],
    "port_busy": ["请求次数过多，请您稍后重试！", 0],
    "no_wpub": ["请先查询并选择公众号！", 0],
    "settings_err": ["请检查所填信息是否完整！", 0]
}


class SingleScraperThread(QThread):
    """单个公众号爬取线程"""
    sig_progress = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        self.sig_progress.emit('start')
        self.sig_progress.emit('url')
        run_getAllUrls(
            page_start=self.config['page_start'],
            page_num=self.config['page_num'],
            save_path=self.config['savepath'],
            tok=self.config['tok'],
            fad=self.config['fad'],
            headers=self.config['headers'],
            filename='raw/' + self.config['filename']
        )
        self.sig_progress.emit('content')
        run_getContentsByUrls_MultiThread(
            savepath=self.config['savepath'],
            filename='raw/' + self.config['filename'],
            headers=self.config['headers']
        )
        self.sig_progress.emit('timestamp')
        run_getRealTimeByTimeStamp(
            savepath=self.config['savepath'],
            filename='raw/' + self.config['filename']
        )
        if self.config['keywords']:
            self.sig_progress.emit('keywords')
        run_getTitleByKeywords(
            keywords_str=self.config['keywords'],
            filename=self.config['filename'],
            savepath=self.config['savepath']
        )
        self.sig_progress.emit('finish')


class AutoLoginThread(QThread):
    """自动登录线程"""
    login_success = pyqtSignal(str, str)
    login_failed = pyqtSignal(str)
    login_status = pyqtSignal(str)
    
    def run(self):
        try:
            self.login_status.emit("正在初始化自动登录...")
            login_manager = WeChatLogin()
            
            self.login_status.emit("正在检查登录状态...")
            if login_manager.login():
                token = login_manager.get_token()
                cookie_string = login_manager.get_cookie_string()
                self.login_success.emit(token, cookie_string)
            else:
                self.login_failed.emit("自动登录失败，请检查网络连接")
        except Exception as e:
            self.login_failed.emit(f"自动登录出错: {str(e)}")


class LoginWidget(QWidget):
    """登录组件 - 精简版"""
    login_changed = pyqtSignal(str, str)  # token, cookie
    
    def __init__(self):
        super().__init__()
        self.is_logged_in = False
        self.token_value = ""
        self.cookie_value = ""
        self.init_ui()
        self.check_login_status()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 登录状态显示
        self.status_label = QLabel("检查登录状态中...")
        self.status_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 登录/重新登录按钮
        self.login_btn = QPushButton("自动登录")
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        layout.addWidget(self.login_btn)
        
        # 手动输入按钮（备用）
        self.manual_btn = QPushButton("手动输入")
        self.manual_btn.clicked.connect(self.show_manual_input)
        self.manual_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px 16px; }")
        layout.addWidget(self.manual_btn)
        
        self.setLayout(layout)
        
        # 手动输入对话框（隐藏）
        self.manual_dialog = None
        
    def handle_login(self):
        if not AUTO_LOGIN_AVAILABLE:
            QMessageBox.warning(self, "警告", "自动登录功能不可用，请安装selenium")
            return
            
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        self.status_label.setText("正在启动自动登录...")
        
        self.login_thread = AutoLoginThread()
        self.login_thread.login_success.connect(self.on_login_success)
        self.login_thread.login_failed.connect(self.on_login_failed)
        self.login_thread.login_status.connect(self.on_login_status)
        self.login_thread.start()
        
    def on_login_success(self, token, cookie):
        self.token_value = token
        self.cookie_value = cookie
        self.is_logged_in = True
        
        self.login_btn.setEnabled(True)
        self.login_btn.setText("重新登录")
        self.status_label.setText(f"✓ 已登录 - {datetime.datetime.now().strftime('%H:%M:%S')}")
        self.status_label.setStyleSheet("color: #008000; font-size: 14px; font-weight: bold;")
        
        self.login_changed.emit(token, cookie)
        QMessageBox.information(self, "成功", "自动登录成功！")
        
    def on_login_failed(self, error):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("自动登录")
        self.status_label.setText("✗ 登录失败")
        self.status_label.setStyleSheet("color: #FF0000; font-size: 14px; font-weight: bold;")
        QMessageBox.warning(self, "失败", f"自动登录失败：\n{error}")
        
    def on_login_status(self, status):
        self.status_label.setText(status)
        
    def show_manual_input(self):
        """显示手动输入对话框"""
        if self.manual_dialog is None:
            self.manual_dialog = ManualInputDialog(self)
            self.manual_dialog.credentials_entered.connect(self.on_manual_credentials)
            
        # 如果已有登录信息，预填充
        if self.is_logged_in:
            self.manual_dialog.set_credentials(self.token_value, self.cookie_value)
            
        self.manual_dialog.show()
        
    def on_manual_credentials(self, token, cookie):
        """手动输入凭据回调"""
        self.token_value = token
        self.cookie_value = cookie
        self.is_logged_in = bool(token and cookie)
        
        if self.is_logged_in:
            self.status_label.setText("✓ 手动登录完成")
            self.status_label.setStyleSheet("color: #008000; font-size: 14px; font-weight: bold;")
            self.login_btn.setText("重新登录")
        else:
            self.status_label.setText("请输入登录信息")
            self.status_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold;")
            
        self.login_changed.emit(token, cookie)
        
    def check_login_status(self):
        if not AUTO_LOGIN_AVAILABLE:
            self.status_label.setText("自动登录功能不可用")
            self.status_label.setStyleSheet("color: #999999; font-size: 14px;")
            self.login_btn.setEnabled(False)
            return
            
        try:
            login_manager = WeChatLogin()
            status = login_manager.check_login_status()
            
            if status['isLoggedIn']:
                token = login_manager.get_token()
                cookie_string = login_manager.get_cookie_string()
                
                if token and cookie_string:
                    self.token_value = token
                    self.cookie_value = cookie_string
                    self.is_logged_in = True
                    
                    self.status_label.setText(f"✓ 已登录 - {status['loginTime']}")
                    self.status_label.setStyleSheet("color: #008000; font-size: 14px; font-weight: bold;")
                    self.login_btn.setText("重新登录")
                    
                    self.login_changed.emit(token, cookie_string)
            else:
                self.status_label.setText("未登录")
                self.status_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold;")
                self.login_btn.setText("自动登录")
        except Exception as e:
            self.status_label.setText("状态检查失败")
            self.status_label.setStyleSheet("color: #FF0000; font-size: 14px; font-weight: bold;")
            
    def get_credentials(self):
        return self.token_value, self.cookie_value


class ManualInputDialog(QWidget):
    """手动输入对话框"""
    credentials_entered = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动输入登录信息")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setFixedSize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 说明
        info_label = QLabel("请按照以下步骤获取登录信息：")
        info_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
        layout.addWidget(info_label)
        
        steps_text = """
1. 打开微信公众平台 (https://mp.weixin.qq.com/)
2. 登录后按F12打开开发者工具
3. 切换到"网络"标签页，刷新页面
4. 找到 "home" 请求，复制其中的token和cookie
        """
        steps_label = QLabel(steps_text)
        steps_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(steps_label)
        
        # Token输入
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("将复制的token直接粘贴")
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)
        
        # Cookie输入
        layout.addWidget(QLabel("Cookie:"))
        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText("将复制的cookie直接粘贴")
        self.cookie_input.setMaximumHeight(120)
        layout.addWidget(self.cookie_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.confirm_btn = QPushButton("确认")
        self.cancel_btn = QPushButton("取消")
        
        self.clear_btn.clicked.connect(self.clear_all)
        self.confirm_btn.clicked.connect(self.confirm)
        self.cancel_btn.clicked.connect(self.close)
        
        self.confirm_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.confirm_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def set_credentials(self, token, cookie):
        """设置凭据"""
        self.token_input.setText(token)
        self.cookie_input.setText(cookie)
        
    def clear_all(self):
        self.token_input.clear()
        self.cookie_input.clear()
        
    def confirm(self):
        token = self.token_input.text().strip()
        cookie = self.cookie_input.toPlainText().strip()
        self.credentials_entered.emit(token, cookie)
        self.close()
        
    def closeEvent(self, event):
        self.hide()
        event.ignore()


class SingleScraperTab(QWidget):
    """单个公众号爬取标签页"""
    
    def __init__(self, login_widget):
        super().__init__()
        self.login_widget = login_widget
        self.wpub_search_res = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 公众号选择区域 - 精简版
        wpub_group = QGroupBox("公众号选择")
        wpub_layout = QVBoxLayout()
        
        # 搜索区域
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("公众号名称:"))
        self.wpub_name = QLineEdit()
        self.wpub_name.setPlaceholderText("输入想要爬取的公众号名称")
        self.wpub_search_btn = QPushButton("查询")
        self.wpub_search_btn.clicked.connect(self.search_wpub)
        search_layout.addWidget(self.wpub_name, 2)
        search_layout.addWidget(self.wpub_search_btn)
        wpub_layout.addLayout(search_layout)
        
        # 选择结果
        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel("选择:"))
        self.wpub_result = QComboBox()
        self.wpub_result.addItem('请在查询后选择您要爬取的公众号')
        result_layout.addWidget(self.wpub_result, 1)
        wpub_layout.addLayout(result_layout)
        
        wpub_group.setLayout(wpub_layout)
        layout.addWidget(wpub_group)
        
        # 爬取设置区域 - 精简版
        settings_group = QGroupBox("爬取设置")
        settings_layout = QVBoxLayout()
        
        # 第一行：页码和文件名
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("起始页码:"))
        self.start_page = QSpinBox()
        self.start_page.setMinimum(0)
        self.start_page.setMaximumWidth(80)
        first_row.addWidget(self.start_page)
        
        first_row.addWidget(QLabel("爬取页数:"))
        self.page_count = QSpinBox()
        self.page_count.setMinimum(1)
        self.page_count.setValue(1)
        self.page_count.setMaximumWidth(80)
        first_row.addWidget(self.page_count)
        
        first_row.addWidget(QLabel("文件名:"))
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("输入文件名")
        first_row.addWidget(self.filename, 1)
        settings_layout.addLayout(first_row)
        
        # 第二行：关键词和保存路径
        second_row = QHBoxLayout()
        second_row.addWidget(QLabel("关键词:"))
        self.keywords = QLineEdit()
        self.keywords.setPlaceholderText("中文分号分隔，可不填")
        second_row.addWidget(self.keywords, 1)
        
        second_row.addWidget(QLabel("保存位置:"))
        self.save_path = QLineEdit()
        self.save_path.setPlaceholderText("选择保存位置")
        self.save_path.setReadOnly(True)
        self.choose_path_btn = QPushButton("浏览")
        self.choose_path_btn.clicked.connect(self.choose_save_path)
        second_row.addWidget(self.save_path, 1)
        second_row.addWidget(self.choose_path_btn)
        settings_layout.addLayout(second_row)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 开始按钮
        self.start_btn = QPushButton("开始爬取")
        self.start_btn.clicked.connect(self.start_scraping)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 12px; font-size: 14px; }")
        layout.addWidget(self.start_btn)
        
        # 进度显示区域 - 精简版
        progress_group = QGroupBox("爬取进度")
        progress_layout = QVBoxLayout()
        
        # 进度条和百分比在同一行
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_percentage = QLabel("0%")
        self.progress_percentage.setMinimumWidth(40)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_percentage)
        progress_layout.addLayout(progress_row)
        
        # 日志信息
        self.log_text = QTextBrowser()
        self.log_text.setMaximumHeight(120)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        self.setLayout(layout)
        
    def search_wpub(self):
        token, cookie = self.login_widget.get_credentials()
        wpub_name = self.wpub_name.text().strip()
        
        if not token:
            QMessageBox.warning(self, "警告", "Token不能为空！")
            return
        if not cookie:
            QMessageBox.warning(self, "警告", "Cookie不能为空！")
            return
        if not wpub_name:
            QMessageBox.warning(self, "警告", "公众号名称不能为空！")
            return
            
        headers = {
            "cookie": cookie,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }
        
        try:
            self.wpub_search_res = get_fakid(headers, token, wpub_name)
            if self.wpub_search_res:
                self.wpub_result.clear()
                self.wpub_result.addItems([f"{x['wpub_name']}   {x['wpub_fakid']}" for x in self.wpub_search_res])
            else:
                QMessageBox.information(self, "提示", "无公众号匹配，请更换公众号名称")
        except Exception as e:
            QMessageBox.warning(self, "错误", "请检查token、cookie是否正确")
            
    def choose_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "选取文件夹", "./")
        if path:
            self.save_path.setText(path)
            
    def start_scraping(self):
        # 验证输入
        token, cookie = self.login_widget.get_credentials()
        if not token or not cookie:
            QMessageBox.warning(self, "警告", "请先登录或手动输入token和cookie")
            return
            
        if not self.wpub_search_res:
            QMessageBox.warning(self, "警告", "请先查询并选择公众号")
            return
            
        if not self.filename.text().strip():
            QMessageBox.warning(self, "警告", "保存文件名不能为空")
            return
            
        if not self.save_path.text().strip():
            QMessageBox.warning(self, "警告", "请选择保存位置")
            return
            
        # 准备配置
        wpub_index = self.wpub_result.currentIndex()
        if wpub_index < 0:
            QMessageBox.warning(self, "警告", "请选择公众号")
            return
            
        fakeid = self.wpub_search_res[wpub_index]['wpub_fakid']
        save_path = self.save_path.text() + f'/{self.filename.text()}_{datetime.date.today()}'
        
        config = {
            'page_start': self.start_page.value(),
            'page_num': self.page_count.value(),
            'savepath': save_path,
            'tok': token,
            'fad': fakeid,
            'headers': {"cookie": cookie, "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            'filename': self.filename.text(),
            'keywords': self.keywords.text()
        }
        
        # 启动爬取线程
        self.scraper_thread = SingleScraperThread(config)
        self.scraper_thread.sig_progress.connect(self.update_progress)
        self.scraper_thread.start()
        
        self.start_btn.setEnabled(False)
        
    def update_progress(self, status):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        info = log_info.get(status, [f"状态: {status}", 0])
        
        self.log_text.append(f'[{current_time}] {info[0]}')
        self.progress_bar.setValue(info[1])
        self.progress_percentage.setText(f"{info[1]}%")
        
        if status == 'finish':
            self.start_btn.setEnabled(True)
            QMessageBox.information(self, "完成", "爬取完成！")


class BatchScraperTab(QWidget):
    """批量爬取标签页"""
    
    def __init__(self, login_widget):
        super().__init__()
        self.login_widget = login_widget
        self.batch_manager = None
        self.init_ui()
        self.setup_batch_manager()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧配置面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout()
        
        # 公众号列表
        accounts_group = QGroupBox("公众号列表")
        accounts_layout = QVBoxLayout()
        
        # 添加公众号
        add_layout = QHBoxLayout()
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("输入公众号名称")
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_account)
        add_layout.addWidget(self.account_input)
        add_layout.addWidget(self.add_btn)
        accounts_layout.addLayout(add_layout)
        
        # 批量操作
        batch_ops_layout = QHBoxLayout()
        self.import_btn = QPushButton("导入文件")
        self.export_btn = QPushButton("导出文件")
        self.clear_btn = QPushButton("清空列表")
        self.import_btn.clicked.connect(self.import_accounts)
        self.export_btn.clicked.connect(self.export_accounts)
        self.clear_btn.clicked.connect(self.clear_accounts)
        batch_ops_layout.addWidget(self.import_btn)
        batch_ops_layout.addWidget(self.export_btn)
        batch_ops_layout.addWidget(self.clear_btn)
        accounts_layout.addLayout(batch_ops_layout)
        
        # 公众号列表
        self.accounts_list = QListWidget()
        self.accounts_list.setMaximumHeight(150)
        accounts_layout.addWidget(self.accounts_list)
        
        # 删除选中
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        accounts_layout.addWidget(self.remove_btn)
        
        # 统计
        self.count_label = QLabel("共 0 个公众号")
        accounts_layout.addWidget(self.count_label)
        
        accounts_group.setLayout(accounts_layout)
        left_layout.addWidget(accounts_group)
        
        # 时间范围设置
        time_group = QGroupBox("时间范围")
        time_layout = QVBoxLayout()
        
        # 日期选择
        date_layout = QVBoxLayout()
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        start_layout.addWidget(self.start_date)
        date_layout.addLayout(start_layout)
        
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        end_layout.addWidget(self.end_date)
        date_layout.addLayout(end_layout)
        time_layout.addLayout(date_layout)
        
        # 快捷按钮
        quick_layout = QHBoxLayout()
        self.last_7days_btn = QPushButton("最近7天")
        self.last_30days_btn = QPushButton("最近30天")
        self.last_90days_btn = QPushButton("最近90天")
        self.last_7days_btn.clicked.connect(lambda: self.set_date_range(7))
        self.last_30days_btn.clicked.connect(lambda: self.set_date_range(30))
        self.last_90days_btn.clicked.connect(lambda: self.set_date_range(90))
        quick_layout.addWidget(self.last_7days_btn)
        quick_layout.addWidget(self.last_30days_btn)
        quick_layout.addWidget(self.last_90days_btn)
        time_layout.addLayout(quick_layout)
        
        time_group.setLayout(time_layout)
        left_layout.addWidget(time_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout()
        
        self.use_threading = QCheckBox("启用多线程")
        self.use_threading.setChecked(True)
        advanced_layout.addWidget(self.use_threading)
        
        self.use_database = QCheckBox("保存到数据库")
        self.use_database.setChecked(True)
        advanced_layout.addWidget(self.use_database)
        
        # 输出设置
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("保存目录:"))
        self.output_dir = QLineEdit()
        self.output_dir.setText("./batch_results")
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(self.browse_btn)
        advanced_layout.addLayout(output_layout)
        
        advanced_group.setLayout(advanced_layout)
        left_layout.addWidget(advanced_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.batch_start_btn = QPushButton("开始批量爬取")
        self.batch_stop_btn = QPushButton("停止爬取")
        self.batch_start_btn.clicked.connect(self.start_batch_scraping)
        self.batch_stop_btn.clicked.connect(self.stop_batch_scraping)
        self.batch_start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.batch_stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        self.batch_stop_btn.setEnabled(False)
        button_layout.addWidget(self.batch_start_btn)
        button_layout.addWidget(self.batch_stop_btn)
        left_layout.addLayout(button_layout)
        
        left_panel.setLayout(left_layout)
        
        # 右侧进度面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 总体进度
        overall_group = QGroupBox("总体进度")
        overall_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        overall_layout.addWidget(self.overall_progress)
        
        self.progress_label = QLabel("等待开始...")
        overall_layout.addWidget(self.progress_label)
        
        overall_group.setLayout(overall_layout)
        right_layout.addWidget(overall_group)
        
        # 账号状态
        status_group = QGroupBox("账号状态")
        status_layout = QVBoxLayout()
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["公众号", "状态", "结果"])
        header = self.status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        status_layout.addWidget(self.status_table)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # 日志
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.batch_log = QTextBrowser()
        self.batch_log.setMaximumHeight(150)
        log_layout.addWidget(self.batch_log)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        right_panel.setLayout(right_layout)
        
        # 添加到主布局
        layout.addWidget(left_panel)
        layout.addWidget(right_panel, 1)
        
        self.setLayout(layout)
        
        # 回车键添加公众号
        self.account_input.returnPressed.connect(self.add_account)
        
    def setup_batch_manager(self):
        if not BATCH_SCRAPER_AVAILABLE:
            self.batch_start_btn.setEnabled(False)
            self.batch_start_btn.setText("批量爬取功能不可用")
            return
            
        self.batch_manager = BatchScraperManager()
        self.batch_manager.set_callback('progress_updated', self.on_progress_updated)
        self.batch_manager.set_callback('account_status', self.on_account_status)
        self.batch_manager.set_callback('batch_completed', self.on_batch_completed)
        self.batch_manager.set_callback('error_occurred', self.on_error_occurred)
        
    def add_account(self):
        account = self.account_input.text().strip()
        if account and account not in self.get_accounts():
            self.accounts_list.addItem(account)
            self.account_input.clear()
            self.update_count()
            
    def remove_selected(self):
        for item in self.accounts_list.selectedItems():
            self.accounts_list.takeItem(self.accounts_list.row(item))
        self.update_count()
        
    def clear_accounts(self):
        reply = QMessageBox.question(self, '确认', '确定要清空所有公众号吗？')
        if reply == QMessageBox.Yes:
            self.accounts_list.clear()
            self.update_count()
            
    def get_accounts(self):
        return [self.accounts_list.item(i).text() for i in range(self.accounts_list.count())]
        
    def update_count(self):
        count = self.accounts_list.count()
        self.count_label.setText(f"共 {count} 个公众号")
        
    def set_date_range(self, days):
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        self.start_date.setDate(start_date)
        self.end_date.setDate(end_date)
        
    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.output_dir.text())
        if dir_path:
            self.output_dir.setText(dir_path)
            
    def import_accounts(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入公众号列表", "", 
            "文本文件 (*.txt);;JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        
        if file_path and BATCH_SCRAPER_AVAILABLE:
            try:
                accounts = load_accounts_from_file(file_path)
                if accounts:
                    for account in accounts:
                        if account.strip() and account not in self.get_accounts():
                            self.accounts_list.addItem(account.strip())
                    self.update_count()
                    QMessageBox.information(self, "成功", f"成功导入 {len(accounts)} 个公众号")
                else:
                    QMessageBox.warning(self, "警告", "文件中没有找到有效的公众号")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
                
    def export_accounts(self):
        accounts = self.get_accounts()
        if not accounts:
            QMessageBox.warning(self, "警告", "没有公众号可导出")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出公众号列表", f"公众号列表_{datetime.date.today()}.txt",
            "文本文件 (*.txt);;JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        
        if file_path and BATCH_SCRAPER_AVAILABLE:
            try:
                if save_accounts_to_file(accounts, file_path):
                    QMessageBox.information(self, "成功", f"成功导出 {len(accounts)} 个公众号")
                else:
                    QMessageBox.critical(self, "错误", "导出失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def start_batch_scraping(self):
        # 检查登录状态
        token, cookie = self.login_widget.get_credentials()
        if not token or not cookie:
            QMessageBox.warning(self, "警告", "请先登录")
            return
            
        # 检查公众号列表
        accounts = self.get_accounts()
        if not accounts:
            QMessageBox.warning(self, "警告", "请至少添加一个公众号")
            return
            
        # 准备配置
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        output_dir = self.output_dir.text()
        filename = f"batch_articles_{start_date}_to_{end_date}.csv"
        output_file = os.path.join(output_dir, filename)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建批量爬取配置
        if BATCH_SCRAPER_AVAILABLE:
            batch_config = create_batch_config(
                accounts=accounts,
                start_date=start_date,
                end_date=end_date,
                token=token,
                headers={"cookie": cookie, "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                output_file=output_file,
                use_threading=self.use_threading.isChecked(),
                use_database=self.use_database.isChecked()
            )
            
            # 设置进度显示
            self.setup_progress_display(accounts)
            
            # 更新界面状态
            self.batch_start_btn.setEnabled(False)
            self.batch_stop_btn.setEnabled(True)
            
            # 开始爬取
            self.batch_manager.start_batch_scrape(batch_config)
            
    def stop_batch_scraping(self):
        if self.batch_manager:
            self.batch_manager.cancel_batch_scrape()
            self.add_log("用户取消了爬取任务")
            self.batch_start_btn.setEnabled(True)
            self.batch_stop_btn.setEnabled(False)
            
    def setup_progress_display(self, accounts):
        self.status_table.setRowCount(len(accounts))
        for i, account in enumerate(accounts):
            self.status_table.setItem(i, 0, QTableWidgetItem(account))
            self.status_table.setItem(i, 1, QTableWidgetItem("等待中"))
            self.status_table.setItem(i, 2, QTableWidgetItem(""))
            
        self.overall_progress.setValue(0)
        self.progress_label.setText("等待开始...")
        self.batch_log.clear()
        self.add_log(f"开始批量爬取 {len(accounts)} 个公众号")
        
    def on_progress_updated(self, batch_id, current, total):
        progress = int((current / total) * 100) if total > 0 else 0
        self.overall_progress.setValue(progress)
        self.progress_label.setText(f"进度: {current}/{total} ({progress}%)")
        
    def on_account_status(self, account_name, status, message):
        for i in range(self.status_table.rowCount()):
            item = self.status_table.item(i, 0)
            if item and item.text() == account_name:
                self.status_table.setItem(i, 1, QTableWidgetItem(status))
                self.status_table.setItem(i, 2, QTableWidgetItem(message))
                break
        self.add_log(f"{account_name}: {message}")
        
    def on_batch_completed(self, batch_id, total_articles):
        self.add_log(f"批量爬取完成！共获得 {total_articles} 篇文章")
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)
        QMessageBox.information(self, "完成", f"批量爬取完成！\n共获得 {total_articles} 篇文章")
        
    def on_error_occurred(self, account_name, error_message):
        self.add_log(f"错误 - {account_name}: {error_message}")
        
    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.batch_log.append(f"[{timestamp}] {message}")


class UnifiedGUI(QMainWindow):
    """统一GUI主界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("微信公众号爬虫 v2.0 - 统一界面")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("微信公众号爬虫")
        title.setFont(QFont("", 22, QFont.Bold))
        title.setStyleSheet("color: #2E86AB; text-decoration: underline;")
        version = QLabel("v2.0")
        contact = QLabel("联系作者：wsz2002@foxmail.com")
        
        title_layout.addWidget(title)
        title_layout.addWidget(version)
        title_layout.addStretch()
        title_layout.addWidget(contact)
        main_layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # 登录组件
        self.login_widget = LoginWidget()
        main_layout.addWidget(self.login_widget)
        
        # 另一条分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line2)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 单个爬取标签页
        self.single_tab = SingleScraperTab(self.login_widget)
        self.tab_widget.addTab(self.single_tab, "单个公众号爬取")
        
        # 批量爬取标签页
        self.batch_tab = BatchScraperTab(self.login_widget)
        self.tab_widget.addTab(self.batch_tab, "批量公众号爬取")
        
        main_layout.addWidget(self.tab_widget)
        
        central_widget.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom-color: #ffffff;
            }
        """)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("微信公众号爬虫 v2.0")
    app.setApplicationVersion("2.0")
    
    # 创建主窗口
    window = UnifiedGUI()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 