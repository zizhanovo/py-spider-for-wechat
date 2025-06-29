#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号批量爬虫
==================

专注于批量公众号文章爬取的简洁界面，
提供高效的多公众号、时间范围筛选的批量爬取功能。

主要功能:
    1. 批量爬取 - 多公众号、时间范围的批量爬取
    2. 自动登录 - 一键获取token和cookie
    3. 智能配置 - 简化的设置界面，专注核心参数
    4. 进度监控 - 实时显示爬取进度和状态

核心特性:
    - 公众号列表管理（添加、导入、导出）
    - 时间范围选择（快捷时间按钮）
    - 请求间隔控制（20-1200秒可调）
    - 实时进度显示和日志记录

作者: 基于main.py简化改进
创建时间: 2024/12/20
版本: 2.0
"""

import sys
import os
import datetime
import json
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QGroupBox, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QSpinBox,
                            QComboBox, QProgressBar, QTextBrowser, QCheckBox,
                            QDateEdit, QListWidget, QTableWidget, QTableWidgetItem,
                            QHeaderView, QFileDialog, QMessageBox, QSplitter,
                            QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

# 导入自动登录和批量爬取模块
try:
    from utils.wechat_login import WeChatLogin
    AUTO_LOGIN_AVAILABLE = True
except ImportError:
    AUTO_LOGIN_AVAILABLE = False

try:
    from utils.batch_scraper import (BatchScraperManager, create_batch_config, 
                                   load_accounts_from_file, save_accounts_to_file,
                                   BatchScraperDatabase)
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


class BatchAddDialog(QWidget):
    """批量添加公众号对话框"""
    accounts_added = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量添加公众号")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setFixedSize(500, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 说明标题
        title_label = QLabel("批量添加公众号")
        title_label.setStyleSheet("font-weight: bold; color: #2E86AB; font-size: 16px;")
        layout.addWidget(title_label)
        
        # 使用说明
        info_text = """支持多种分隔符，可以使用以下任意符号分隔公众号名称：
• 换行（回车）
• 逗号 (,)
• 分号 (;)
• 空格
• 制表符（Tab）
• 顿号 (、)
• 中文逗号 (，)
• 竖线 (|)

示例：
量子位,机器之心;AI科技大本营
或者每行一个公众号名称"""
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666666; font-size: 12px; background-color: #f5f5f5; padding: 10px; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 输入区域
        input_label = QLabel("请输入公众号名称（支持批量输入）：")
        input_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(input_label)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("例如：\n量子位\n机器之心\nAI科技大本营\n\n或者：量子位,机器之心,AI科技大本营")
        self.text_input.setMaximumHeight(150)
        layout.addWidget(self.text_input)
        
        # 预览区域
        preview_label = QLabel("解析预览：")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(preview_label)
        
        self.preview_list = QListWidget()
        self.preview_list.setMaximumHeight(80)
        layout.addWidget(self.preview_list)
        
        # 实时预览
        self.text_input.textChanged.connect(self.update_preview)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("清空")
        self.preview_btn = QPushButton("刷新预览")
        self.add_btn = QPushButton("添加到列表")
        self.cancel_btn = QPushButton("取消")
        
        self.clear_btn.clicked.connect(self.clear_input)
        self.preview_btn.clicked.connect(self.update_preview)
        self.add_btn.clicked.connect(self.add_accounts)
        self.cancel_btn.clicked.connect(self.close)
        
        # 按钮样式
        self.add_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        self.cancel_btn.setStyleSheet("QPushButton { padding: 8px 16px; }")
        self.clear_btn.setStyleSheet("QPushButton { padding: 8px 16px; }")
        self.preview_btn.setStyleSheet("QPushButton { padding: 8px 16px; }")
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.preview_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.add_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def update_preview(self):
        """更新预览列表"""
        self.preview_list.clear()
        text = self.text_input.toPlainText()
        
        if text.strip():
            accounts = self.parse_accounts(text)
            for account in accounts:
                self.preview_list.addItem(f"• {account}")
            
            if accounts:
                self.add_btn.setText(f"添加 {len(accounts)} 个公众号")
                self.add_btn.setEnabled(True)
            else:
                self.add_btn.setText("添加到列表")
                self.add_btn.setEnabled(False)
        else:
            self.add_btn.setText("添加到列表")
            self.add_btn.setEnabled(False)
    
    def parse_accounts(self, text):
        """解析公众号文本"""
        import re
        
        if not text.strip():
            return []
        
        # 支持的分隔符
        separators = r'[\n\r,;，；、\s\t|]+'
        accounts = re.split(separators, text.strip())
        
        # 清理和过滤
        cleaned_accounts = []
        for account in accounts:
            account = account.strip()
            account = account.strip('"\'""''')
            if account and len(account) > 0:
                cleaned_accounts.append(account)
        
        return cleaned_accounts
    
    def clear_input(self):
        """清空输入"""
        self.text_input.clear()
        self.preview_list.clear()
        self.add_btn.setText("添加到列表")
        self.add_btn.setEnabled(False)
    
    def add_accounts(self):
        """添加公众号到主列表"""
        text = self.text_input.toPlainText()
        if text.strip():
            self.accounts_added.emit(text)
            self.close()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.hide()
        event.ignore()


class BatchScraperTab(QWidget):
    """批量爬取标签页"""
    
    def __init__(self, login_widget):
        super().__init__()
        self.login_widget = login_widget
        self.batch_manager = None
        self.db_manager = None  # 添加数据库管理器
        self.enhanced_db_manager = None  # 增强数据库管理器（支持自然语言查询）
        self.current_batch_id = None  # 当前批次ID
        self.init_ui()
        self.setup_batch_manager()
        self.setup_database()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧配置面板 - 使用滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumWidth(420)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)  # 减少间距
        
        # 公众号列表 - 压缩高度
        accounts_group = QGroupBox("公众号列表")
        accounts_layout = QVBoxLayout()
        accounts_layout.setSpacing(6)
        
        # 添加公众号
        add_layout = QHBoxLayout()
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("输入公众号名称")
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_account)
        self.batch_add_btn = QPushButton("批量添加")
        self.batch_add_btn.clicked.connect(self.show_batch_add_dialog)
        self.batch_add_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")
        add_layout.addWidget(self.account_input)
        add_layout.addWidget(self.add_btn)
        add_layout.addWidget(self.batch_add_btn)
        accounts_layout.addLayout(add_layout)
        
        # 批量操作 - 压缩按钮
        batch_ops_layout = QHBoxLayout()
        self.import_btn = QPushButton("导入")
        self.export_btn = QPushButton("导出")
        self.clear_btn = QPushButton("清空")
        self.import_btn.clicked.connect(self.import_accounts)
        self.export_btn.clicked.connect(self.export_accounts)
        self.clear_btn.clicked.connect(self.clear_accounts)
        
        # 设置按钮样式，减少高度
        button_style = "QPushButton { padding: 4px 8px; }"
        self.import_btn.setStyleSheet(button_style)
        self.export_btn.setStyleSheet(button_style)
        self.clear_btn.setStyleSheet(button_style)
        
        batch_ops_layout.addWidget(self.import_btn)
        batch_ops_layout.addWidget(self.export_btn)
        batch_ops_layout.addWidget(self.clear_btn)
        accounts_layout.addLayout(batch_ops_layout)
        
        # 公众号列表 - 减少高度
        self.accounts_list = QListWidget()
        self.accounts_list.setMaximumHeight(100)  # 从150减少到100
        accounts_layout.addWidget(self.accounts_list)
        
        # 删除选中和统计 - 合并到一行
        remove_count_layout = QHBoxLayout()
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.remove_btn.setStyleSheet(button_style)
        self.count_label = QLabel("共 0 个公众号")
        self.count_label.setStyleSheet("font-size: 12px; color: #666;")
        remove_count_layout.addWidget(self.remove_btn)
        remove_count_layout.addStretch()
        remove_count_layout.addWidget(self.count_label)
        accounts_layout.addLayout(remove_count_layout)
        
        accounts_group.setLayout(accounts_layout)
        left_layout.addWidget(accounts_group)
        
        # 时间范围设置 - 压缩
        time_group = QGroupBox("时间设置")
        time_layout = QVBoxLayout()
        time_layout.setSpacing(4)
        
        # 日期选择 - 水平布局节省空间
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-3))
        self.start_date.setCalendarPopup(True)
        self.start_date.setMaximumWidth(120)
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel("结束:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setMaximumWidth(120)
        date_layout.addWidget(self.end_date)
        time_layout.addLayout(date_layout)
        
        # 快捷时间按钮 - 小按钮
        quick_layout = QHBoxLayout()
        self.last_1day_btn = QPushButton("1天")
        self.last_3days_btn = QPushButton("3天")
        self.last_5days_btn = QPushButton("5天")
        self.last_1day_btn.clicked.connect(lambda: self.set_date_range(1))
        self.last_3days_btn.clicked.connect(lambda: self.set_date_range(3))
        self.last_5days_btn.clicked.connect(lambda: self.set_date_range(5))
        
        quick_button_style = "QPushButton { padding: 2px 6px; font-size: 12px; }"
        self.last_1day_btn.setStyleSheet(quick_button_style)
        self.last_3days_btn.setStyleSheet(quick_button_style)
        self.last_5days_btn.setStyleSheet(quick_button_style)
        
        quick_layout.addWidget(self.last_1day_btn)
        quick_layout.addWidget(self.last_3days_btn)
        quick_layout.addWidget(self.last_5days_btn)
        quick_layout.addStretch()
        time_layout.addLayout(quick_layout)
        
        time_group.setLayout(time_layout)
        left_layout.addWidget(time_group)
        
        # 请求间隔设置 - 压缩
        interval_group = QGroupBox("请求间隔")
        interval_layout = QVBoxLayout()
        interval_layout.setSpacing(4)
        
        interval_input_layout = QHBoxLayout()
        interval_input_layout.addWidget(QLabel("间隔:"))
        self.request_interval = QSpinBox()
        self.request_interval.setRange(20, 1200)
        self.request_interval.setValue(60)
        self.request_interval.setSuffix(" 秒")
        self.request_interval.setMaximumWidth(100)
        interval_input_layout.addWidget(self.request_interval)
        interval_input_layout.addStretch()
        interval_layout.addLayout(interval_input_layout)
        
        # 快捷间隔按钮 - 小按钮
        quick_interval_layout = QHBoxLayout()
        self.interval_30s_btn = QPushButton("30s")
        self.interval_60s_btn = QPushButton("60s")
        self.interval_120s_btn = QPushButton("2m")
        self.interval_300s_btn = QPushButton("5m")
        
        self.interval_30s_btn.clicked.connect(lambda: self.request_interval.setValue(30))
        self.interval_60s_btn.clicked.connect(lambda: self.request_interval.setValue(60))
        self.interval_120s_btn.clicked.connect(lambda: self.request_interval.setValue(120))
        self.interval_300s_btn.clicked.connect(lambda: self.request_interval.setValue(300))
        
        for btn in [self.interval_30s_btn, self.interval_60s_btn, self.interval_120s_btn, self.interval_300s_btn]:
            btn.setStyleSheet(quick_button_style)
        
        quick_interval_layout.addWidget(self.interval_30s_btn)
        quick_interval_layout.addWidget(self.interval_60s_btn)
        quick_interval_layout.addWidget(self.interval_120s_btn)
        quick_interval_layout.addWidget(self.interval_300s_btn)
        interval_layout.addLayout(quick_interval_layout)
        
        # 简化说明
        interval_note = QLabel("建议60秒以上")
        interval_note.setStyleSheet("color: #666666; font-size: 11px;")
        interval_layout.addWidget(interval_note)
        
        interval_group.setLayout(interval_layout)
        left_layout.addWidget(interval_group)
        
        # 输出设置 - 压缩
        output_group = QGroupBox("保存设置")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(4)
        
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("目录:"))
        self.output_dir = QLineEdit()
        self.output_dir.setText("./batch_results")
        self.browse_btn = QPushButton("...")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        self.browse_btn.setMaximumWidth(30)
        self.browse_btn.setStyleSheet(button_style)
        output_path_layout.addWidget(self.output_dir)
        output_path_layout.addWidget(self.browse_btn)
        output_layout.addLayout(output_path_layout)
        
        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)
        
        # AI智能查询功能 - 新设计
        query_group = QGroupBox("AI智能查询")
        query_layout = QVBoxLayout()
        query_layout.setSpacing(4)
        
        # 查询输入
        query_input_layout = QVBoxLayout()
        query_input_layout.addWidget(QLabel("自然语言查询:"))
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("支持AI理解自然语言查询，例如：\n• 标题为ai的\n• 关于人工智能的文章\n• 包含机器学习的内容")
        self.query_input.setMaximumHeight(60)
        query_input_layout.addWidget(self.query_input)
        query_layout.addLayout(query_input_layout)
        
        # 筛选选项
        filter_options_layout = QHBoxLayout()
        self.use_account_filter = QCheckBox("按公众号筛选")
        self.use_time_filter = QCheckBox("按时间筛选")
        self.use_account_filter.setToolTip("使用上方选中的公众号进行筛选")
        self.use_time_filter.setToolTip("使用上方设置的时间范围进行筛选")
        filter_options_layout.addWidget(self.use_account_filter)
        filter_options_layout.addWidget(self.use_time_filter)
        filter_options_layout.addStretch()
        query_layout.addLayout(filter_options_layout)
        
        # 查询按钮
        query_button_layout = QHBoxLayout()
        self.query_btn = QPushButton("AI智能查询")
        self.query_btn.clicked.connect(self.execute_natural_language_query)
        self.query_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 6px 12px; }")
        
        self.clear_query_btn = QPushButton("清空")
        self.clear_query_btn.clicked.connect(self.clear_query)
        self.clear_query_btn.setStyleSheet("QPushButton { padding: 6px 12px; }")
        
        query_button_layout.addWidget(self.query_btn)
        query_button_layout.addWidget(self.clear_query_btn)
        query_layout.addLayout(query_button_layout)
        
        # 功能说明
        api_note = QLabel("✓ 使用GPT-4生成SQL查询\n✓ 可复用上方公众号和时间设置")
        api_note.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
        api_note.setWordWrap(True)
        query_layout.addWidget(api_note)
        
        query_group.setLayout(query_layout)
        left_layout.addWidget(query_group)
        
        # 添加弹性空间，确保控制按钮在底部
        left_layout.addStretch()
        
        # 控制按钮 - 确保可见
        button_layout = QVBoxLayout()  # 改为垂直布局，节省高度
        self.batch_start_btn = QPushButton("开始批量爬取")
        self.batch_stop_btn = QPushButton("停止爬取")
        self.batch_start_btn.clicked.connect(self.start_batch_scraping)
        self.batch_stop_btn.clicked.connect(self.stop_batch_scraping)
        
        # 突出显示的按钮样式
        self.batch_start_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 8px; 
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.batch_stop_btn.setStyleSheet("""
            QPushButton { 
                background-color: #f44336; 
                color: white; 
                font-weight: bold; 
                padding: 8px; 
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #da190b; }
        """)
        self.batch_stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.batch_start_btn)
        button_layout.addWidget(self.batch_stop_btn)
        left_layout.addLayout(button_layout)
        
        left_panel.setLayout(left_layout)
        scroll_area.setWidget(left_panel)
        
        # 右侧进度面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 总体进度
        overall_group = QGroupBox("爬取进度")
        overall_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        overall_layout.addWidget(self.overall_progress)
        
        self.progress_label = QLabel("等待开始...")
        overall_layout.addWidget(self.progress_label)
        
        overall_group.setLayout(overall_layout)
        right_layout.addWidget(overall_group)
        
        # 账号状态 - 改为简化的状态显示
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout()
        
        self.current_status_label = QLabel("等待开始...")
        self.current_status_label.setWordWrap(True)
        status_layout.addWidget(self.current_status_label)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # 文章展示区域
        articles_group = QGroupBox("抓取文章")
        articles_layout = QVBoxLayout()
        
        # 搜索和过滤
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索标题...")
        self.search_input.textChanged.connect(self.search_articles)
        search_layout.addWidget(self.search_input)
        
        self.account_filter = QComboBox()
        self.account_filter.addItem("全部公众号")
        self.account_filter.currentTextChanged.connect(self.filter_by_account)
        search_layout.addWidget(self.account_filter)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_recent_articles)
        self.refresh_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")
        search_layout.addWidget(self.refresh_btn)
        
        # 添加导出Markdown按钮
        self.export_md_btn = QPushButton("导出MD")
        self.export_md_btn.clicked.connect(self.export_articles_to_markdown)
        self.export_md_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 4px 12px; }")
        search_layout.addWidget(self.export_md_btn)
        
        articles_layout.addLayout(search_layout)
        
        # 文章表格
        self.articles_table = QTableWidget()
        self.articles_table.setColumnCount(6)  # 公众号、标题、发布时间、摘要、内容预览、链接(隐藏)
        self.articles_table.setHorizontalHeaderLabels(["公众号", "标题", "发布时间", "摘要", "内容预览", "链接"])
        
        # 设置列宽
        header = self.articles_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 公众号列
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 标题列可拉伸
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 时间列
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 摘要列可拉伸
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # 内容预览列可拉伸
        header.hideSection(5)  # 隐藏链接列
        
        # 设置表格属性
        self.articles_table.setAlternatingRowColors(True)
        self.articles_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.articles_table.setSortingEnabled(True)
        self.articles_table.setWordWrap(True)
        self.articles_table.setMaximumHeight(300)  # 限制高度
        
        # 双击打开链接
        self.articles_table.doubleClicked.connect(self.open_article_link)
        
        articles_layout.addWidget(self.articles_table)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.articles_count_label = QLabel("共 0 篇文章")
        self.accounts_count_label = QLabel("0 个公众号")
        stats_layout.addWidget(self.articles_count_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.accounts_count_label)
        articles_layout.addLayout(stats_layout)
        
        articles_group.setLayout(articles_layout)
        right_layout.addWidget(articles_group)
        
        # 日志
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.batch_log = QTextBrowser()
        self.batch_log.setMaximumHeight(100)  # 减少日志高度
        log_layout.addWidget(self.batch_log)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        right_panel.setLayout(right_layout)
        
        # 添加到主布局
        layout.addWidget(scroll_area)
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
        request_interval = self.request_interval.value()  # 获取请求间隔
        filename = f"batch_articles_{start_date}_to_{end_date}.csv"
        output_file = os.path.join(output_dir, filename)
        
        # 生成批次ID
        self.current_batch_id = f"batch_{int(time.time())}"
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 添加爬取设置日志
        self.add_log(f"爬取设置:")
        self.add_log(f"  - 时间范围: {start_date} 至 {end_date}")
        self.add_log(f"  - 公众号数量: {len(accounts)}")
        self.add_log(f"  - 请求间隔: {request_interval}秒")
        self.add_log(f"  - 保存位置: {output_file}")
        self.add_log(f"  - 批次ID: {self.current_batch_id}")
        
        # 创建批量爬取配置
        if BATCH_SCRAPER_AVAILABLE:
            batch_config = create_batch_config(
                accounts=accounts,
                start_date=start_date,
                end_date=end_date,
                token=token,
                headers={"cookie": cookie, "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                output_file=output_file,
                request_interval=request_interval,  # 添加请求间隔配置
                use_threading=True,
                use_database=True,  # 启用数据库存储
                db_file=os.path.join(output_dir, "wechat_articles.db"),  # 数据库文件路径
                batch_id=self.current_batch_id,  # 设置批次ID
                include_content=True  # 启用文章内容读取
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
        # 更新公众号过滤器
        self.account_filter.clear()
        self.account_filter.addItem("全部公众号")
        for account in accounts:
            self.account_filter.addItem(account)
            
        self.overall_progress.setValue(0)
        self.progress_label.setText("等待开始...")
        self.current_status_label.setText("准备开始爬取...")
        self.batch_log.clear()
        self.add_log(f"开始批量爬取 {len(accounts)} 个公众号")
        
    def on_progress_updated(self, batch_id, current, total):
        progress = int((current / total) * 100) if total > 0 else 0
        self.overall_progress.setValue(progress)
        self.progress_label.setText(f"进度: {current}/{total} ({progress}%)")
        
    def on_account_status(self, account_name, status, message):
        self.current_status_label.setText(f"{account_name}: {message}")
        self.add_log(f"{account_name}: {message}")
        
        # 如果有新文章，刷新文章列表
        if "完成" in status and "篇文章" in message:
            self.load_recent_articles()
        
    def on_batch_completed(self, batch_id, total_articles):
        self.add_log(f"批量爬取完成！共获得 {total_articles} 篇文章")
        self.current_status_label.setText(f"爬取完成！共获得 {total_articles} 篇文章")
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)
        
        # 刷新文章列表
        self.load_recent_articles()
        
        QMessageBox.information(self, "完成", f"批量爬取完成！\n共获得 {total_articles} 篇文章")
        
    def on_error_occurred(self, account_name, error_message):
        self.add_log(f"错误 - {account_name}: {error_message}")
        self.current_status_label.setText(f"错误 - {account_name}: {error_message}")

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.batch_log.append(f"[{timestamp}] {message}")

    def show_batch_add_dialog(self):
        """显示批量添加公众号对话框"""
        dialog = BatchAddDialog(self)
        dialog.accounts_added.connect(self.add_batch_accounts)
        dialog.show()
    
    def add_batch_accounts(self, accounts_text):
        """批量添加公众号"""
        accounts = self.parse_batch_accounts(accounts_text)
        added_count = 0
        existing_accounts = self.get_accounts()
        
        for account in accounts:
            if account and account not in existing_accounts:
                self.accounts_list.addItem(account)
                existing_accounts.append(account)
                added_count += 1
        
        self.update_count()
        
        if added_count > 0:
            QMessageBox.information(self, "成功", f"成功添加 {added_count} 个公众号")
        else:
            QMessageBox.warning(self, "提示", "没有找到新的公众号，可能都已存在")
    
    def parse_batch_accounts(self, text):
        """解析批量输入的公众号文本，支持多种分隔符"""
        import re
        
        if not text.strip():
            return []
        
        # 支持的分隔符：换行、逗号、分号、空格、制表符、顿号、中文逗号、竖线
        # 使用正则表达式分割
        separators = r'[\n\r,;，；、\s\t|]+'
        accounts = re.split(separators, text.strip())
        
        # 清理和过滤
        cleaned_accounts = []
        for account in accounts:
            account = account.strip()
            # 移除可能的引号
            account = account.strip('"\'""''')
            if account and len(account) > 0:
                cleaned_accounts.append(account)
        
        return cleaned_accounts

    def setup_database(self):
        """初始化数据库"""
        if BATCH_SCRAPER_AVAILABLE:
            try:
                db_file = os.path.join("./batch_results", "wechat_articles.db")
                os.makedirs(os.path.dirname(db_file), exist_ok=True)
                
                # 保留原有的批量爬取数据库管理器
                try:
                    self.db_manager = BatchScraperDatabase(db_file)
                    print("BatchScraperDatabase 初始化成功")
                except Exception as e:
                    print(f"BatchScraperDatabase 初始化失败: {e}")
                    self.db_manager = None
                
                # 使用增强的数据库管理器，支持自然语言查询
                try:
                    # 需要先确保表结构兼容
                    self.create_compatible_tables(db_file)
                    
                    # 尝试导入DatabaseManager，但使用简化的初始化
                    import sys
                    note_path = os.path.join(os.path.dirname(__file__), 'note', 'other')
                    if note_path not in sys.path:
                        sys.path.append(note_path)
                    
                    # 创建一个简化的数据库管理器，跳过FTS5初始化
                    from WeChat import DatabaseManager
                    
                    # 先检查数据库是否已经存在复杂结构
                    import sqlite3
                    with sqlite3.connect(db_file) as test_conn:
                        test_cursor = test_conn.cursor()
                        # 检查是否存在FTS表
                        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles_fts'")
                        has_fts = test_cursor.fetchone() is not None
                    
                    if has_fts:
                        # 如果已有FTS表，直接使用
                        self.enhanced_db_manager = DatabaseManager(db_file)
                    else:
                        # 创建一个简化版本，不使用FTS5
                        self.enhanced_db_manager = self.create_simple_enhanced_db_manager(db_file)
                    
                    print("增强数据库管理器初始化成功")
                except ImportError as e:
                    print(f"无法导入WeChat.DatabaseManager: {e}")
                    self.enhanced_db_manager = None
                    # 禁用智能查询按钮
                    if hasattr(self, 'query_btn'):
                        self.query_btn.setEnabled(False)
                        self.query_btn.setText("智能查询(不可用)")
                except Exception as e:
                    print(f"增强数据库管理器初始化失败: {e}")
                    self.enhanced_db_manager = None
                    if hasattr(self, 'query_btn'):
                        self.query_btn.setEnabled(False)
                        self.query_btn.setText("智能查询(不可用)")
                
                # 加载文章
                if self.db_manager:
                    self.load_recent_articles()
                else:
                    print("无数据库管理器，跳过文章加载")
                    
            except Exception as e:
                print(f"数据库初始化失败: {e}")
                self.db_manager = None
                self.enhanced_db_manager = None
                if hasattr(self, 'query_btn'):
                    self.query_btn.setEnabled(False)
                    self.query_btn.setText("智能查询(不可用)")
        
        # 最后更新智能查询按钮状态
        self.update_query_button_status()

    def create_simple_enhanced_db_manager(self, db_file):
        """创建增强的数据库管理器，支持AI接口调用生成SQL查询"""
        # 创建一个完整的DatabaseManager类来支持AI查询
        class AIEnhancedDBManager:
            def __init__(self, db_path):
                self.db_file = db_path
                
            def generate_sql_from_natural_language(self, query_text, api_key=None, model="gpt-4o", api_endpoint=None):
                """
                使用大模型将自然语言转换为SQL查询
                支持OpenAI API或其他兼容的API
                """
                import requests
                import os
                
                # 表结构信息 - 适配batch_articles表
                table_schema = """
                表名: batch_articles
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
                - idx_batch_articles_account_time: (account_name, publish_timestamp)
                - idx_batch_articles_time_range: (publish_timestamp) 
                - idx_batch_articles_account_name: (account_name)
                - idx_batch_articles_publish_time: (publish_time)
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
5. 返回字段必须包括：account_name, title, link, digest, publish_time, publish_timestamp, content
6. 默认按时间倒序排列：ORDER BY publish_timestamp DESC
7. 添加合理的LIMIT限制结果数量（如未指定，默认20条）
8. 只返回SQL语句，不要包含其他文字

示例:
用户: "查找量子位发布的关于AI的文章"
SQL: SELECT account_name, title, link, digest, publish_time, publish_timestamp, content FROM batch_articles WHERE account_name LIKE '%量子位%' AND (title LIKE '%AI%' OR content LIKE '%AI%' OR digest LIKE '%AI%') ORDER BY publish_timestamp DESC LIMIT 20

用户: "最近3天的文章，按公众号分组"
SQL: SELECT account_name, COUNT(*) as count, MAX(publish_time) as latest FROM batch_articles WHERE publish_timestamp > strftime('%s', 'now', '-3 days') GROUP BY account_name ORDER BY count DESC

用户: "标题为ai的"
SQL: SELECT account_name, title, link, digest, publish_time, publish_timestamp, content FROM batch_articles WHERE title LIKE '%ai%' ORDER BY publish_timestamp DESC LIMIT 20

用户输入: {query_text}
SQL:"""

                try:
                    if not api_key:
                        # 尝试从环境变量获取API密钥
                        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('API_KEY')
                        
                    if not api_key:
                        # 使用默认的API密钥
                        api_key = "sk-Oqs4DhEZ8B7e0e85a375T3BlBkFJF1E23C555B5b482fbefA"
                    
                    # 配置API端点
                    if not api_endpoint:
                        api_endpoint = os.getenv('OPENAI_API_ENDPOINT', 'https://c-z0-api-01.hash070.com')
                    
                    # 构建完整的API URL
                    if api_endpoint.endswith('/'):
                        api_endpoint = api_endpoint[:-1]
                    
                    api_url = f"{api_endpoint}/v1/chat/completions"
                    
                    print(f"使用API端点: {api_url}")
                    
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
                        print(f"AI生成的SQL查询: {sql_query}")
                        return sql_query
                    else:
                        print(f"API调用失败: {response.status_code} - {response.text}")
                        return None
                        
                except Exception as e:
                    print(f"生成SQL查询失败: {e}")
                    return None
                
            def query_articles_by_natural_language(self, query_text, api_key=None, model="gpt-4o", api_endpoint=None):
                """
                根据自然语言查询文章
                
                Args:
                    query_text: 自然语言查询文本
                    api_key: OpenAI API密钥
                    model: 使用的模型
                    api_endpoint: API端点
                """
                # 生成SQL查询
                sql_query = self.generate_sql_from_natural_language(query_text, api_key, model, api_endpoint)
                if not sql_query:
                    return {
                        'success': False,
                        'error': 'SQL生成失败',
                        'articles': []
                    }
                
                # 安全检查：确保只允许SELECT查询
                sql_upper = sql_query.upper().strip()
                if not sql_upper.startswith('SELECT'):
                    print(f"非法SQL查询被拦截: {sql_query}")
                    return {
                        'success': False,
                        'error': '只允许SELECT查询',
                        'articles': []
                    }
                
                # 检查是否包含危险操作
                dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'EXEC']
                if any(keyword in sql_upper for keyword in dangerous_keywords):
                    print(f"包含危险关键词的SQL查询被拦截: {sql_query}")
                    return {
                        'success': False,
                        'error': '查询包含不允许的操作',
                        'articles': []
                    }
                
                # 执行查询
                import sqlite3
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                try:
                    print(f"执行AI生成的SQL查询: {sql_query}")
                    
                    # 检查表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='batch_articles'")
                    if not cursor.fetchone():
                        return {
                            'success': False,
                            'error': '数据库中没有文章数据，请先进行爬取',
                            'articles': []
                        }
                    
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
                        'query_method': 'ai_generated'
                    }
                    
                except Exception as e:
                    conn.close()
                    print(f"执行SQL查询失败: {e}")
                    return {
                        'success': False,
                        'error': f'查询执行失败: {str(e)}',
                        'articles': [],
                        'sql_query': sql_query
                    }
        
        return AIEnhancedDBManager(db_file)

    def update_query_button_status(self):
        """更新AI智能查询按钮的状态"""
        if hasattr(self, 'query_btn'):
            if self.enhanced_db_manager:
                self.query_btn.setEnabled(True)
                self.query_btn.setText("AI智能查询")
                print("AI智能查询功能已启用")
            else:
                self.query_btn.setEnabled(False)
                self.query_btn.setText("AI查询(不可用)")
                print("AI智能查询功能不可用")

    def create_compatible_tables(self, db_file):
        """创建兼容的数据库表结构"""
        import sqlite3
        try:
            with sqlite3.connect(db_file) as conn:
                cursor = conn.cursor()
                
                # 检查是否存在articles表，如果不存在则创建
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
                if not cursor.fetchone():
                    # 创建articles表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS articles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            account_name TEXT NOT NULL,
                            title TEXT NOT NULL,
                            link TEXT UNIQUE NOT NULL,
                            digest TEXT,
                            publish_time TEXT,
                            publish_timestamp INTEGER,
                            content TEXT,
                            created_at INTEGER DEFAULT (strftime('%s', 'now')),
                            UNIQUE(link)
                        )
                    ''')
                    
                    # 创建索引
                    try:
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_account_time ON articles(account_name, publish_timestamp)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_time_range ON articles(publish_timestamp)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_account_name ON articles(account_name)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_publish_time ON articles(publish_time)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at)')
                        print("✓ 索引创建成功")
                    except Exception as idx_e:
                        print(f"索引创建警告: {idx_e}")
                     
                # 如果batch_articles表存在数据，则同步数据到articles表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='batch_articles'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM batch_articles")
                    batch_count = cursor.fetchone()[0]
                    
                    if batch_count > 0:
                        cursor.execute("SELECT COUNT(*) FROM articles")
                        articles_count = cursor.fetchone()[0]
                        
                        if articles_count < batch_count:
                            # 将batch_articles的数据复制到articles表
                            cursor.execute('''
                                INSERT OR REPLACE INTO articles 
                                (account_name, title, link, digest, content, publish_time, publish_timestamp)
                                SELECT account_name, title, link, digest, content, publish_time, publish_timestamp
                                FROM batch_articles
                            ''')
                            print(f"同步了 {batch_count} 条数据到articles表")
                else:
                    print("batch_articles表不存在，跳过数据同步")
                
                conn.commit()
                print("数据库表结构兼容性处理完成")
                
        except Exception as e:
            print(f"创建兼容表结构失败: {e}")

    def load_recent_articles(self):
        """加载最近的文章到列表"""
        if not self.db_manager:
            return
            
        try:
            # 获取搜索和过滤条件
            keyword = self.search_input.text().strip()
            selected_account = self.account_filter.currentText()
            
            # 构建查询语句
            conn = self.db_manager.db_file
            import sqlite3
            with sqlite3.connect(conn) as db:
                cursor = db.cursor()
                
                # 检查batch_articles表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='batch_articles'")
                if not cursor.fetchone():
                    print("batch_articles表不存在，显示空列表")
                    self.articles_table.setRowCount(0)
                    self.articles_count_label.setText("共 0 篇文章")
                    self.accounts_count_label.setText("0 个公众号")
                    return
                
                # 基础查询
                base_query = '''
                    SELECT account_name, title, link, digest, publish_time, publish_timestamp 
                    FROM batch_articles 
                '''
                
                conditions = []
                params = []
                
                # 添加关键词搜索条件
                if keyword:
                    conditions.append("(title LIKE ? OR digest LIKE ?)")
                    params.extend([f'%{keyword}%', f'%{keyword}%'])
                
                # 添加公众号过滤条件
                if selected_account and selected_account != "全部公众号":
                    conditions.append("account_name = ?")
                    params.append(selected_account)
                
                # 组合条件
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY publish_timestamp DESC LIMIT 200"
                
                cursor.execute(base_query, params)
                articles = cursor.fetchall()
                
                # 更新表格
                self.articles_table.setRowCount(len(articles))
                for i, article in enumerate(articles):
                    account_name, title, link, digest, publish_time, _ = article
                    
                    self.articles_table.setItem(i, 0, QTableWidgetItem(account_name))
                    self.articles_table.setItem(i, 1, QTableWidgetItem(title))
                    self.articles_table.setItem(i, 2, QTableWidgetItem(publish_time))
                    
                    # 处理摘要显示
                    digest_text = digest if digest else ""
                    if len(digest_text) > 100:
                        digest_text = digest_text[:100] + "..."
                    self.articles_table.setItem(i, 3, QTableWidgetItem(digest_text))
                    
                    # 存储完整链接在最后一列（隐藏）
                    self.articles_table.setItem(i, 4, QTableWidgetItem(link))
                
                # 更新统计信息
                self.articles_count_label.setText(f"共 {len(articles)} 篇文章")
                
                # 获取公众号统计
                cursor.execute('''
                    SELECT COUNT(DISTINCT account_name) FROM batch_articles
                ''')
                account_count = cursor.fetchone()[0]
                self.accounts_count_label.setText(f"{account_count} 个公众号")
                    
        except Exception as e:
            print(f"加载文章失败: {e}")
            # 设置空表格显示
            self.articles_table.setRowCount(0)
            self.articles_count_label.setText("共 0 篇文章")
            self.accounts_count_label.setText("0 个公众号")
            if hasattr(self, 'add_log'):
                self.add_log(f"加载文章失败: {e}")
    
    def search_articles(self):
        """搜索文章"""
        self.load_recent_articles()
    
    def filter_by_account(self):
        """根据公众号过滤文章"""
        self.load_recent_articles()
    
    def open_article_link(self, item):
        """打开文章链接"""
        row = item.row()
        link = self.articles_table.item(row, 4).text()
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def export_articles_to_markdown(self):
        """导出文章为Markdown格式"""
        if not self.db_manager:
            QMessageBox.warning(self, "警告", "数据库未初始化")
            return
            
        try:
            # 获取当前显示的文章数据
            articles_data = []
            for row in range(self.articles_table.rowCount()):
                account_name = self.articles_table.item(row, 0).text() if self.articles_table.item(row, 0) else ""
                title = self.articles_table.item(row, 1).text() if self.articles_table.item(row, 1) else ""
                publish_time = self.articles_table.item(row, 2).text() if self.articles_table.item(row, 2) else ""
                digest = self.articles_table.item(row, 3).text() if self.articles_table.item(row, 3) else ""
                link = self.articles_table.item(row, 5).text() if self.articles_table.item(row, 5) else ""
                
                # 从数据库获取完整内容
                content = self.get_full_article_content(link)
                
                articles_data.append({
                    'account_name': account_name,
                    'title': title,
                    'publish_time': publish_time,
                    'digest': digest,
                    'link': link,
                    'content': content
                })
            
            if not articles_data:
                QMessageBox.warning(self, "警告", "没有文章可导出")
                return
            
            # 选择保存位置
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"微信文章_{timestamp}.md"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出文章为Markdown", default_filename,
                "Markdown文件 (*.md);;所有文件 (*.*)"
            )
            
            if not file_path:
                return
            
            # 生成Markdown内容
            markdown_content = self.generate_markdown_content(articles_data)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            QMessageBox.information(self, "成功", f"成功导出 {len(articles_data)} 篇文章到:\n{file_path}")
            self.add_log(f"导出完成: {len(articles_data)} 篇文章 -> {file_path}")
            
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.add_log(error_msg)
    
    def get_full_article_content(self, link):
        """从数据库获取文章完整内容"""
        if not self.db_manager:
            return ""
            
        try:
            import sqlite3
            with sqlite3.connect(self.db_manager.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT content FROM batch_articles WHERE link = ?", (link,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else ""
        except Exception as e:
            print(f"获取文章内容失败: {e}")
            return ""
    
    def generate_markdown_content(self, articles_data):
        """生成Markdown格式内容"""
        markdown_lines = []
        
        # 添加标题和目录
        markdown_lines.append("# 微信公众号文章合集")
        markdown_lines.append("")
        markdown_lines.append(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_lines.append(f"文章数量: {len(articles_data)}")
        markdown_lines.append("")
        markdown_lines.append("## 目录")
        markdown_lines.append("")
        
        # 添加目录
        for i, article in enumerate(articles_data, 1):
            title = article['title'].replace('[', '\\[').replace(']', '\\]')  # 转义Markdown特殊字符
            markdown_lines.append(f"{i}. [{title}](#{i}-{article['account_name'].replace(' ', '-')})")
        
        markdown_lines.append("")
        markdown_lines.append("---")
        markdown_lines.append("")
        
        # 添加文章内容
        for i, article in enumerate(articles_data, 1):
            # 文章标题
            title = article['title']
            account_name = article['account_name']
            publish_time = article['publish_time']
            
            markdown_lines.append(f"## {i}. {title}")
            markdown_lines.append("")
            markdown_lines.append(f"**公众号:** {account_name}")
            markdown_lines.append(f"**发布时间:** {publish_time}")
            if article['link']:
                markdown_lines.append(f"**原文链接:** [{article['link']}]({article['link']})")
            markdown_lines.append("")
            
            # 文章摘要
            if article['digest']:
                markdown_lines.append("**摘要:**")
                markdown_lines.append("")
                markdown_lines.append(f"> {article['digest']}")
                markdown_lines.append("")
            
            # 文章内容
            content = article['content']
            if content and content != "未获取内容":
                markdown_lines.append("**正文:**")
                markdown_lines.append("")
                # 处理内容，确保格式正确
                content_lines = content.split('\n')
                for line in content_lines:
                    if line.strip():
                        markdown_lines.append(line.strip())
                    else:
                        markdown_lines.append("")
            else:
                markdown_lines.append("*（未获取到文章内容）*")
            
            markdown_lines.append("")
            markdown_lines.append("---")
            markdown_lines.append("")
        
        return '\n'.join(markdown_lines)

    def execute_natural_language_query(self):
        """执行自然语言查询，支持共用筛选条件"""
        if not self.enhanced_db_manager:
            # 如果增强数据库管理器不可用，提供提示信息
            if not self.db_manager:
                QMessageBox.warning(self, "警告", "数据库未初始化，无法执行查询")
            else:
                QMessageBox.warning(self, "警告", "AI智能查询功能不可用\n\n原因可能是：\n1. 缺少WeChat.py模块\n2. API配置问题\n\n请使用基本的搜索和过滤功能")
            return
            
        query_text = self.query_input.toPlainText().strip()
        if not query_text:
            QMessageBox.warning(self, "警告", "请输入查询内容")
            return
            
        try:
            self.add_log(f"正在执行AI智能查询: {query_text}")
            self.query_btn.setEnabled(False)
            self.query_btn.setText("查询中...")
            
            # 构建额外的筛选条件
            additional_filters = []
            
            # 如果启用公众号筛选
            if self.use_account_filter.isChecked():
                selected_accounts = self.get_accounts()
                if selected_accounts:
                    # 构建公众号筛选条件
                    account_conditions = []
                    for account in selected_accounts:
                        account_conditions.append(f"account_name LIKE '%{account}%'")
                    if account_conditions:
                        account_filter = f"({' OR '.join(account_conditions)})"
                        additional_filters.append(f"AND {account_filter}")
                        self.add_log(f"应用公众号筛选: {', '.join(selected_accounts)}")
            
            # 如果启用时间筛选
            if self.use_time_filter.isChecked():
                start_date = self.start_date.date()
                end_date = self.end_date.date()
                
                # 转换为时间戳
                import time
                from datetime import datetime
                start_timestamp = int(time.mktime(start_date.toPyDate().timetuple()))
                end_timestamp = int(time.mktime(end_date.toPyDate().timetuple())) + 86399  # 加上一天的秒数-1
                
                time_filter = f"AND publish_timestamp >= {start_timestamp} AND publish_timestamp <= {end_timestamp}"
                additional_filters.append(time_filter)
                self.add_log(f"应用时间筛选: {start_date.toString('yyyy-MM-dd')} 至 {end_date.toString('yyyy-MM-dd')}")
            
            # 合并筛选条件
            additional_filters_str = " ".join(additional_filters) if additional_filters else None
            
            # 检查是否有query_articles_by_natural_language方法
            if not hasattr(self.enhanced_db_manager, 'query_articles_by_natural_language'):
                error_msg = "DatabaseManager不支持自然语言查询功能"
                self.add_log(f"查询失败: {error_msg}")
                QMessageBox.warning(self, "功能不支持", error_msg)
                return
            
            # 调用AI智能查询功能
            result = self.enhanced_db_manager.query_articles_by_natural_language(
                query_text=query_text,
                api_key="sk-Oqs4DhEZ8B7e0e85a375T3BlBkFJF1E23C555B5b482fbefA",
                model="gpt-4o",
                api_endpoint="https://c-z0-api-01.hash070.com",
                additional_filters=additional_filters_str
            )
            
            if result.get('success', False):
                articles = result.get('articles', [])
                sql_query = result.get('sql_query', '')
                query_method = result.get('query_method', 'unknown')
                
                # 显示生成的SQL查询（用于调试和学习）
                if sql_query:
                    self.add_log(f"AI生成的SQL查询: {sql_query}")
                    
                # 根据查询方法显示不同的提示
                if query_method == 'ai_generated':
                    filter_info = ""
                    if additional_filters_str:
                        filter_info = f"（已应用筛选条件）"
                    self.add_log(f"使用AI生成SQL查询{filter_info}，找到 {len(articles)} 篇文章")
                else:
                    self.add_log(f"查询完成，找到 {len(articles)} 篇文章")
                
                # 显示查询结果
                self.display_query_results(articles, query_text)
                
                if len(articles) == 0:
                    filter_tip = ""
                    if additional_filters_str:
                        filter_tip = "\n注意：已应用额外筛选条件，可能过滤了部分结果"
                    QMessageBox.information(self, "查询结果", f"查询：{query_text}\n\n未找到匹配的文章，请尝试：\n1. 修改关键词\n2. 调整筛选条件\n3. 检查公众号名称{filter_tip}")
                else:
                    # 在日志中显示一些示例结果
                    sample_count = min(3, len(articles))
                    self.add_log(f"查询结果示例（前{sample_count}篇）：")
                    for i, article in enumerate(articles[:sample_count]):
                        self.add_log(f"  {i+1}. {article.get('name', '')} - {article.get('title', '')}")
                        
            else:
                error_msg = result.get('error', '未知错误')
                self.add_log(f"查询失败: {error_msg}")
                QMessageBox.warning(self, "查询失败", f"查询失败: {error_msg}\n\n请尝试：\n1. 简化查询语句\n2. 使用更明确的关键词\n3. 检查是否有爬取的数据\n4. 调整筛选条件")
                
        except AttributeError as e:
            error_msg = f"方法不存在: {str(e)}"
            self.add_log(error_msg)
            QMessageBox.warning(self, "功能不支持", "当前DatabaseManager版本不支持自然语言查询")
        except Exception as e:
            error_msg = f"查询出错: {str(e)}"
            self.add_log(error_msg)
            QMessageBox.critical(self, "错误", f"查询执行出错:\n{error_msg}")
        finally:
            self.query_btn.setEnabled(True)
            self.query_btn.setText("AI智能查询")
    
    def clear_query(self):
        """清空查询内容和筛选选项"""
        self.query_input.clear()
        self.use_account_filter.setChecked(False)
        self.use_time_filter.setChecked(False)
        self.load_recent_articles()  # 重新加载所有文章
    
    def display_query_results(self, articles, query_text):
        """显示查询结果"""
        # 更新文章表格显示查询结果
        self.articles_table.setRowCount(len(articles))
        for i, article in enumerate(articles):
            # 注意：这里的article字段名可能与数据库字段不同，需要适配
            account_name = article.get('name', '')
            title = article.get('title', '')
            link = article.get('link', '')
            digest = article.get('digest', '')
            publish_time = article.get('publish_time', '')
            content = article.get('content', '')
            
            self.articles_table.setItem(i, 0, QTableWidgetItem(account_name))
            self.articles_table.setItem(i, 1, QTableWidgetItem(title))
            self.articles_table.setItem(i, 2, QTableWidgetItem(publish_time))
            
            # 处理摘要显示
            digest_text = digest if digest else ""
            if len(digest_text) > 100:
                digest_text = digest_text[:100] + "..."
            self.articles_table.setItem(i, 3, QTableWidgetItem(digest_text))
            
            # 处理内容预览显示
            content_text = content if content else "未获取内容"
            if len(content_text) > 150:
                content_text = content_text[:150] + "..."
            self.articles_table.setItem(i, 4, QTableWidgetItem(content_text))
            
            # 存储完整链接在最后一列（隐藏）
            self.articles_table.setItem(i, 5, QTableWidgetItem(link))
        
        # 更新统计信息
        self.articles_count_label.setText(f"查询结果: {len(articles)} 篇文章")
        self.accounts_count_label.setText(f"查询: {query_text[:20]}...")
        
        self.add_log(f"显示查询结果: {len(articles)} 篇文章")


class UnifiedGUI(QMainWindow):
    """统一GUI主界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("微信公众号批量爬虫 v2.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("微信公众号批量爬虫")
        title.setFont(QFont("", 22, QFont.Bold))
        title.setStyleSheet("color: #2E86AB; text-decoration: underline;")
        version = QLabel("v2.0")
        contact = QLabel("联系作者：zizhan66@outlook.com")
        
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
        
        # 直接添加批量爬取界面（去掉标签页）
        self.batch_tab = BatchScraperTab(self.login_widget)
        main_layout.addWidget(self.batch_tab)
        
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