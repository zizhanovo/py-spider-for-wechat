#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的GUI测试
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox

class SimpleTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("GUI测试")
        self.setGeometry(300, 300, 400, 200)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("GUI界面测试")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E86AB;")
        layout.addWidget(title)
        
        # 测试按钮
        test_btn = QPushButton("点击测试")
        test_btn.clicked.connect(self.show_message)
        test_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(test_btn)
        
        central_widget.setLayout(layout)
        
    def show_message(self):
        QMessageBox.information(self, "测试", "GUI界面正常工作！")

def main():
    app = QApplication(sys.argv)
    window = SimpleTestWindow()
    window.show()
    
    print("GUI界面已启动，请查看是否显示窗口")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 