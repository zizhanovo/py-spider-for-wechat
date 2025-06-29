#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量公众号爬取GUI界面
==================

这是一个专门用于批量公众号爬取的图形界面，
支持多个公众号、时间范围设置、进度跟踪等功能。

主要功能:
    1. 批量公众号管理 - 添加、删除、导入、导出公众号列表
    2. 时间范围设置 - 灵活的开始和结束日期配置
    3. 高级选项 - 多线程、数据库存储、内容抓取等
    4. 实时进度 - 显示每个公众号的处理状态和进度
    5. 结果管理 - 查看和导出爬取结果

作者: 基于WeChat.py设计理念
创建时间: 2024/12/20
版本: 1.0
"""

import sys
import os
import json
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                            QPushButton, QTextEdit, QListWidget, QDateEdit,
                            QCheckBox, QSpinBox, QProgressBar, QTableWidget,
                            QTableWidgetItem, QHeaderView, QFileDialog,
                            QMessageBox, QTabWidget, QGroupBox, QSplitter,
                            QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

# 导入批量爬取模块
try:
    from utils.batch_scraper import (BatchScraperManager, create_batch_config, 
                                   load_accounts_from_file, save_accounts_to_file)
    from utils.wechat_login import WeChatLogin
    BATCH_SCRAPER_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] 批量爬取模块不可用: {e}")
    BATCH_SCRAPER_AVAILABLE = False


class AccountListWidget(QWidget):
    """公众号列表管理组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("公众号列表")
        title.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 添加公众号区域
        add_layout = QHBoxLayout()
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("输入公众号名称")
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_account)
        
        add_layout.addWidget(self.account_input)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        
        # 批量操作按钮
        batch_layout = QHBoxLayout()
        self.import_btn = QPushButton("从文件导入")
        self.export_btn = QPushButton("导出到文件")
        self.clear_btn = QPushButton("清空列表")
        
        self.import_btn.clicked.connect(self.import_accounts)
        self.export_btn.clicked.connect(self.export_accounts)
        self.clear_btn.clicked.connect(self.clear_accounts)
        
        batch_layout.addWidget(self.import_btn)
        batch_layout.addWidget(self.export_btn)
        batch_layout.addWidget(self.clear_btn)
        layout.addLayout(batch_layout)
        
        # 公众号列表
        self.account_list = QListWidget()
        self.account_list.setMinimumHeight(200)
        layout.addWidget(self.account_list)
        
        # 删除选中按钮
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        layout.addWidget(self.remove_btn)
        
        # 统计信息
        self.count_label = QLabel("共 0 个公众号")
        layout.addWidget(self.count_label)
        
        self.setLayout(layout)
        
        # 回车键添加公众号
        self.account_input.returnPressed.connect(self.add_account)
    
    def add_account(self):
        """添加公众号"""
        account = self.account_input.text().strip()
        if account and account not in self.get_accounts():
            self.account_list.addItem(account)
            self.account_input.clear()
            self.update_count()
    
    def remove_selected(self):
        """删除选中的公众号"""
        for item in self.account_list.selectedItems():
            self.account_list.takeItem(self.account_list.row(item))
        self.update_count()
    
    def clear_accounts(self):
        """清空公众号列表"""
        reply = QMessageBox.question(self, '确认', '确定要清空所有公众号吗？',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.account_list.clear()
            self.update_count()
    
    def import_accounts(self):
        """从文件导入公众号"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入公众号列表", "", 
            "文本文件 (*.txt);;JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                accounts = load_accounts_from_file(file_path)
                if accounts:
                    for account in accounts:
                        if account.strip() and account not in self.get_accounts():
                            self.account_list.addItem(account.strip())
                    self.update_count()
                    QMessageBox.information(self, "成功", f"成功导入 {len(accounts)} 个公众号")
                else:
                    QMessageBox.warning(self, "警告", "文件中没有找到有效的公众号")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def export_accounts(self):
        """导出公众号到文件"""
        accounts = self.get_accounts()
        if not accounts:
            QMessageBox.warning(self, "警告", "没有公众号可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出公众号列表", f"公众号列表_{datetime.date.today()}.txt",
            "文本文件 (*.txt);;JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                if save_accounts_to_file(accounts, file_path):
                    QMessageBox.information(self, "成功", f"成功导出 {len(accounts)} 个公众号")
                else:
                    QMessageBox.critical(self, "错误", "导出失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def get_accounts(self):
        """获取所有公众号列表"""
        return [self.account_list.item(i).text() 
                for i in range(self.account_list.count())]
    
    def set_accounts(self, accounts):
        """设置公众号列表"""
        self.account_list.clear()
        for account in accounts:
            if account.strip():
                self.account_list.addItem(account.strip())
        self.update_count()
    
    def update_count(self):
        """更新统计信息"""
        count = self.account_list.count()
        self.count_label.setText(f"共 {count} 个公众号")


class ConfigWidget(QWidget):
    """配置选项组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 时间范围设置
        time_group = QGroupBox("时间范围设置")
        time_layout = QGridLayout()
        
        time_layout.addWidget(QLabel("开始日期:"), 0, 0)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-3))  # 默认3天前
        self.start_date.setCalendarPopup(True)
        time_layout.addWidget(self.start_date, 0, 1)
        
        time_layout.addWidget(QLabel("结束日期:"), 1, 0)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())  # 默认今天
        self.end_date.setCalendarPopup(True)
        time_layout.addWidget(self.end_date, 1, 1)
        
        # 快捷时间按钮
        quick_layout = QHBoxLayout()
        self.last_1day_btn = QPushButton("最近1天")
        self.last_3days_btn = QPushButton("最近3天")
        self.last_5days_btn = QPushButton("最近5天")
        
        self.last_1day_btn.clicked.connect(lambda: self.set_date_range(1))
        self.last_3days_btn.clicked.connect(lambda: self.set_date_range(3))
        self.last_5days_btn.clicked.connect(lambda: self.set_date_range(5))
        
        quick_layout.addWidget(self.last_1day_btn)
        quick_layout.addWidget(self.last_3days_btn)
        quick_layout.addWidget(self.last_5days_btn)
        time_layout.addLayout(quick_layout, 2, 0, 1, 2)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QGridLayout()
        
        # 多线程选项
        self.use_threading = QCheckBox("启用多线程爬取")
        self.use_threading.setChecked(True)
        advanced_layout.addWidget(self.use_threading, 0, 0)
        
        advanced_layout.addWidget(QLabel("线程数:"), 0, 1)
        self.max_workers = QSpinBox()
        self.max_workers.setRange(1, 10)
        self.max_workers.setValue(3)
        advanced_layout.addWidget(self.max_workers, 0, 2)
        
        # 数据库选项
        self.use_database = QCheckBox("保存到数据库")
        self.use_database.setChecked(True)
        advanced_layout.addWidget(self.use_database, 1, 0)
        
        # 内容抓取选项
        self.include_content = QCheckBox("抓取文章内容")
        self.include_content.setChecked(False)
        advanced_layout.addWidget(self.include_content, 1, 1)
        
        # 每个公众号最大页数
        advanced_layout.addWidget(QLabel("每号最大页数:"), 2, 0)
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 1000)
        self.max_pages.setValue(100)
        advanced_layout.addWidget(self.max_pages, 2, 1)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QGridLayout()
        
        output_layout.addWidget(QLabel("保存目录:"), 0, 0)
        self.output_dir = QLineEdit()
        self.output_dir.setText("./batch_results")
        output_layout.addWidget(self.output_dir, 0, 1)
        
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.browse_btn, 0, 2)
        
        output_layout.addWidget(QLabel("文件名前缀:"), 1, 0)
        self.filename_prefix = QLineEdit()
        self.filename_prefix.setText("batch_articles")
        output_layout.addWidget(self.filename_prefix, 1, 1, 1, 2)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_date_range(self, days):
        """设置日期范围"""
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        self.start_date.setDate(start_date)
        self.end_date.setDate(end_date)
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.output_dir.text())
        if dir_path:
            self.output_dir.setText(dir_path)
    
    def get_config(self):
        """获取配置"""
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 生成输出文件路径
        output_dir = self.output_dir.text()
        filename = f"{self.filename_prefix.text()}_{start_date}_to_{end_date}.csv"
        output_file = os.path.join(output_dir, filename)
        
        # 生成数据库文件路径
        db_file = os.path.join(output_dir, "batch_scraper.db")
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'use_threading': self.use_threading.isChecked(),
            'max_workers': self.max_workers.value(),
            'use_database': self.use_database.isChecked(),
            'include_content': self.include_content.isChecked(),
            'max_pages_per_account': self.max_pages.value(),
            'output_file': output_file,
            'db_file': db_file
        }


class ProgressWidget(QWidget):
    """进度显示组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 总体进度
        progress_group = QGroupBox("总体进度")
        progress_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        progress_layout.addWidget(self.overall_progress)
        
        self.progress_label = QLabel("等待开始...")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 账号状态表格
        status_group = QGroupBox("账号状态")
        status_layout = QVBoxLayout()
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["公众号", "状态", "结果"])
        
        # 设置表格列宽
        header = self.status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        status_layout.addWidget(self.status_table)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 日志显示
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def setup_accounts(self, accounts):
        """设置账号列表"""
        self.status_table.setRowCount(len(accounts))
        for i, account in enumerate(accounts):
            self.status_table.setItem(i, 0, QTableWidgetItem(account))
            self.status_table.setItem(i, 1, QTableWidgetItem("等待中"))
            self.status_table.setItem(i, 2, QTableWidgetItem(""))
    
    def update_progress(self, batch_id, current, total):
        """更新总体进度"""
        progress = int((current / total) * 100) if total > 0 else 0
        self.overall_progress.setValue(progress)
        self.progress_label.setText(f"进度: {current}/{total} ({progress}%)")
    
    def update_account_status(self, account_name, status, message):
        """更新账号状态"""
        for i in range(self.status_table.rowCount()):
            item = self.status_table.item(i, 0)
            if item and item.text() == account_name:
                self.status_table.setItem(i, 1, QTableWidgetItem(status))
                self.status_table.setItem(i, 2, QTableWidgetItem(message))
                break
    
    def add_log(self, message):
        """添加日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def clear_progress(self):
        """清空进度"""
        self.overall_progress.setValue(0)
        self.progress_label.setText("等待开始...")
        self.status_table.setRowCount(0)
        self.log_text.clear()


class BatchScraperGUI(QMainWindow):
    """批量爬取主界面"""
    
    def __init__(self):
        super().__init__()
        self.batch_manager = None
        self.login_manager = None
        self.init_ui()
        self.setup_batch_manager()
        self.check_login_status()
    
    def init_ui(self):
        self.setWindowTitle("微信公众号批量爬取工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        
        # 左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout()
        
        # 登录状态
        self.login_status_label = QLabel("检查登录状态中...")
        self.login_status_label.setStyleSheet("color: #666666; font-size: 12px;")
        left_layout.addWidget(self.login_status_label)
        
        # 自动登录按钮
        self.auto_login_btn = QPushButton("自动登录")
        self.auto_login_btn.clicked.connect(self.auto_login)
        left_layout.addWidget(self.auto_login_btn)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(line)
        
        # 公众号管理
        self.account_widget = AccountListWidget()
        left_layout.addWidget(self.account_widget)
        
        # 配置选项
        self.config_widget = ConfigWidget()
        left_layout.addWidget(self.config_widget)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始爬取")
        self.start_btn.clicked.connect(self.start_scraping)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        
        self.stop_btn = QPushButton("停止爬取")
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        left_layout.addLayout(button_layout)
        
        left_panel.setLayout(left_layout)
        
        # 右侧面板 - 进度显示
        self.progress_widget = ProgressWidget()
        
        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.progress_widget, 1)
        
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
    
    def setup_batch_manager(self):
        """设置批量爬取管理器"""
        if not BATCH_SCRAPER_AVAILABLE:
            QMessageBox.critical(self, "错误", "批量爬取模块不可用，请检查依赖安装")
            return
        
        self.batch_manager = BatchScraperManager()
        
        # 设置回调函数
        self.batch_manager.set_callback('progress_updated', self.on_progress_updated)
        self.batch_manager.set_callback('account_status', self.on_account_status)
        self.batch_manager.set_callback('batch_completed', self.on_batch_completed)
        self.batch_manager.set_callback('error_occurred', self.on_error_occurred)
    
    def check_login_status(self):
        """检查登录状态"""
        try:
            self.login_manager = WeChatLogin()
            status = self.login_manager.check_login_status()
            
            if status['isLoggedIn']:
                self.login_status_label.setText(f"已登录 - {status['loginTime']}")
                self.login_status_label.setStyleSheet("color: #008000; font-size: 12px;")
                self.auto_login_btn.setText("重新登录")
            else:
                self.login_status_label.setText("未登录")
                self.login_status_label.setStyleSheet("color: #666666; font-size: 12px;")
                self.auto_login_btn.setText("自动登录")
        except Exception as e:
            self.login_status_label.setText("登录状态检查失败")
            self.login_status_label.setStyleSheet("color: #FF0000; font-size: 12px;")
    
    def auto_login(self):
        """自动登录"""
        self.auto_login_btn.setEnabled(False)
        self.auto_login_btn.setText("登录中...")
        
        try:
            if self.login_manager.login():
                self.login_status_label.setText(f"登录成功 - {datetime.datetime.now().strftime('%H:%M:%S')}")
                self.login_status_label.setStyleSheet("color: #008000; font-size: 12px;")
                self.auto_login_btn.setText("重新登录")
                QMessageBox.information(self, "成功", "自动登录成功！")
            else:
                self.login_status_label.setText("登录失败")
                self.login_status_label.setStyleSheet("color: #FF0000; font-size: 12px;")
                QMessageBox.warning(self, "失败", "自动登录失败，请检查网络连接")
        except Exception as e:
            self.login_status_label.setText("登录失败")
            self.login_status_label.setStyleSheet("color: #FF0000; font-size: 12px;")
            QMessageBox.critical(self, "错误", f"登录过程中出现错误: {str(e)}")
        finally:
            self.auto_login_btn.setEnabled(True)
            if self.auto_login_btn.text() == "登录中...":
                self.auto_login_btn.setText("自动登录")
    
    def start_scraping(self):
        """开始爬取"""
        # 检查登录状态
        if not self.login_manager or not self.login_manager.is_logged_in():
            QMessageBox.warning(self, "警告", "请先登录微信公众平台")
            return
        
        # 检查公众号列表
        accounts = self.account_widget.get_accounts()
        if not accounts:
            QMessageBox.warning(self, "警告", "请至少添加一个公众号")
            return
        
        # 获取配置
        config = self.config_widget.get_config()
        
        # 确保输出目录存在
        output_dir = os.path.dirname(config['output_file'])
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建批量爬取配置
        batch_config = create_batch_config(
            accounts=accounts,
            start_date=config['start_date'],
            end_date=config['end_date'],
            token=self.login_manager.get_token(),
            headers=self.login_manager.get_headers(),
            **config
        )
        
        # 设置进度显示
        self.progress_widget.setup_accounts(accounts)
        self.progress_widget.clear_progress()
        self.progress_widget.add_log(f"开始批量爬取 {len(accounts)} 个公众号")
        self.progress_widget.add_log(f"时间范围: {config['start_date']} 到 {config['end_date']}")
        
        # 更新界面状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 开始爬取
        self.batch_manager.start_batch_scrape(batch_config)
    
    def stop_scraping(self):
        """停止爬取"""
        if self.batch_manager:
            self.batch_manager.cancel_batch_scrape()
            self.progress_widget.add_log("用户取消了爬取任务")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def on_progress_updated(self, batch_id, current, total):
        """进度更新回调"""
        self.progress_widget.update_progress(batch_id, current, total)
    
    def on_account_status(self, account_name, status, message):
        """账号状态更新回调"""
        self.progress_widget.update_account_status(account_name, status, message)
        self.progress_widget.add_log(f"{account_name}: {message}")
    
    def on_batch_completed(self, batch_id, total_articles):
        """批次完成回调"""
        self.progress_widget.add_log(f"批量爬取完成！共获得 {total_articles} 篇文章")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        QMessageBox.information(self, "完成", 
                              f"批量爬取完成！\n共获得 {total_articles} 篇文章\n\n"
                              f"结果已保存到指定目录")
    
    def on_error_occurred(self, account_name, error_message):
        """错误发生回调"""
        self.progress_widget.add_log(f"错误 - {account_name}: {error_message}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("微信公众号批量爬取工具")
    app.setApplicationVersion("1.0")
    
    # 创建主窗口
    window = BatchScraperGUI()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 