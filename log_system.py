"""
日志系统模块
记录交易操作、系统状态和行情变化
"""

import os
import sys
import logging
import json
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QPushButton, QComboBox, QCheckBox,
                            QFileDialog, QMessageBox, QTabWidget, QTableWidget,
                            QTableWidgetItem, QFrame)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QColor


class LogHandler(logging.Handler):
    """自定义日志处理器"""
    
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        """发送日志记录到UI"""
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module
            }
            self.signal.emit(log_entry)
        except Exception:
            pass  # 忽略日志记录错误








class MarketLog(QWidget):
    """行情日志面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.price_history = []
        self.init_ui()
        
    def init_ui(self):
        """初始化行情日志界面"""
        layout = QVBoxLayout(self)
        
        # 标题和统计信息
        header_layout = QHBoxLayout()
        
        title_label = QLabel("行情日志")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 价格统计
        self.price_stats_label = QLabel("最高: --  最低: --  涨幅: --")
        header_layout.addWidget(self.price_stats_label)
        
        # 导出按钮
        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_price_data)
        header_layout.addWidget(export_button)
        
        layout.addLayout(header_layout)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 行情表格
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(6)
        self.price_table.setHorizontalHeaderLabels([
            "时间", "价格", "24h涨跌", "24h成交量", "5m涨跌幅", "信号"
        ])
        
        # 设置表格样式
        header = self.price_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.price_table.setAlternatingRowColors(True)
        self.price_table.setSortingEnabled(True)
        
        layout.addWidget(self.price_table)
        
    def add_price_data(self, price_data):
        """添加价格数据"""
        try:
            # 计算5分钟涨跌幅
            change_5m = 0
            if len(self.price_history) > 0:
                prev_price = self.price_history[-1]['price']
                change_5m = (price_data['price'] - prev_price) / prev_price * 100
                
            price_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': price_data['price'],
                'change_24h': price_data.get('change_24h', 0),
                'volume_24h': price_data.get('volume_24h', 0),
                'change_5m': change_5m,
                'signal': price_data['signal']
            }
            
            self.price_history.append(price_entry)
            
            # 保持最近500条记录
            if len(self.price_history) > 500:
                self.price_history.pop(0)
                
            self.update_price_table()
            
        except Exception as e:
            print(f"添加价格数据失败: {e}")
            
    def update_price_table(self):
        """更新价格表格"""
        try:
            self.price_table.setRowCount(len(self.price_history))
            
            for row, entry in enumerate(self.price_history):
                # 时间
                self.price_table.setItem(row, 0, QTableWidgetItem(entry['timestamp']))
                
                # 价格
                price_item = QTableWidgetItem(f"{entry['price']:.2f}")
                self.price_table.setItem(row, 1, price_item)
                
                # 24h涨跌
                change_24h = entry['change_24h']
                change_24h_item = QTableWidgetItem(f"{change_24h:.2f}%")
                if change_24h >= 0:
                    change_24h_item.setForeground(QColor('green'))
                else:
                    change_24h_item.setForeground(QColor('red'))
                self.price_table.setItem(row, 2, change_24h_item)
                
                # 24h成交量
                volume_item = QTableWidgetItem(f"{entry['volume_24h']:.2f}")
                self.price_table.setItem(row, 3, volume_item)
                
                # 5m涨跌幅
                change_5m = entry['change_5m']
                change_5m_item = QTableWidgetItem(f"{change_5m:.3f}%")
                if change_5m >= 0:
                    change_5m_item.setForeground(QColor('green'))
                else:
                    change_5m_item.setForeground(QColor('red'))
                self.price_table.setItem(row, 4, change_5m_item)
                
                # 交易信号
                signal_item = QTableWidgetItem(entry['signal'])
                if entry['signal'] == 'BUY':
                    signal_item.setForeground(QColor('green'))
                elif entry['signal'] == 'SELL':
                    signal_item.setForeground(QColor('red'))
                self.price_table.setItem(row, 5, signal_item)
                
            # 更新价格统计
            if self.price_history:
                prices = [p['price'] for p in self.price_history]
                max_price = max(prices)
                min_price = min(prices)
                
                current_price = self.price_history[-1]['price']
                if len(self.price_history) > 1:
                    first_price = self.price_history[0]['price']
                    price_change = (current_price - first_price) / first_price * 100
                else:
                    price_change = 0
                    
                self.price_stats_label.setText(f"最高: {max_price:.2f}  最低: {min_price:.2f}  涨幅: {price_change:.2f}%")
                
            # 滚动到底部
            self.price_table.scrollToBottom()
            
        except Exception as e:
            print(f"更新价格表格失败: {e}")
            
    def export_price_data(self):
        """导出价格数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出价格数据", f"price_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)")
            
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.price_history, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", "价格数据已导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class SystemLog(QWidget):
    """系统日志面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_events = []
        self.init_ui()
        
    def init_ui(self):
        """初始化系统日志界面"""
        layout = QVBoxLayout(self)
        
        # 标题和状态
        header_layout = QHBoxLayout()
        
        title_label = QLabel("")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 系统状态
        self.system_status_label = QLabel("状态: 正常运行")
        self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
        header_layout.addWidget(self.system_status_label)
        
        # 清除按钮
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self.clear_system_logs)
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 系统日志文本框（命令行风格）
        self.system_text_edit = QTextEdit()
        self.system_text_edit.setReadOnly(True)
        self.system_text_edit.setFont(QFont("Consolas", 10))  # 使用等宽字体，模拟命令行
        self.system_text_edit.setStyleSheet("background-color: #f8f8f8; color: #333333;")
        self.system_text_edit.setWordWrapMode(True)  # 自动换行
        
        layout.addWidget(self.system_text_edit)
        
    def add_system_event(self, event_type, description):
        """添加系统事件"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            event = {
                'timestamp': timestamp,
                'type': event_type,
                'description': description
            }
            
            self.system_events.append(event)
            
            # 保持最近200条记录
            if len(self.system_events) > 200:
                self.system_events.pop(0)
                
            self.update_system_text()
            
        except Exception as e:
            print(f"添加系统事件失败: {e}")
            
    def update_system_text(self):
        """更新系统日志文本框"""
        try:
            self.system_text_edit.clear()
            
            for event in self.system_events:
                # 根据事件类型设置颜色
                if event['type'] == 'ERROR':
                    color = '#ff0000'  # 红色
                elif event['type'] == 'WARNING':
                    color = '#ff8000'  # 橙色
                elif event['type'] == 'INFO':
                    color = '#0000ff'  # 蓝色
                else:
                    color = '#333333'  # 黑色
                
                # 格式化日志条目，模拟命令行输出
                log_entry = f"[{event['timestamp']}] [{event['type']}] {event['description']}\n"
                
                # 添加带颜色的文本
                self.system_text_edit.append(f"<font color='{color}'>{log_entry}</font>")
            
            # 滚动到底部
            self.system_text_edit.verticalScrollBar().setValue(
                self.system_text_edit.verticalScrollBar().maximum()
            )
            
        except Exception as e:
            print(f"更新系统日志文本失败: {e}")
            
    def update_system_status(self, status):
        """更新系统状态"""
        if status == 'normal':
            self.system_status_label.setText("状态: 正常运行")
            self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
        elif status == 'warning':
            self.system_status_label.setText("状态: 警告")
            self.system_status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif status == 'error':
            self.system_status_label.setText("状态: 错误")
            self.system_status_label.setStyleSheet("color: red; font-weight: bold;")
            
    def clear_system_logs(self):
        """清空系统日志"""
        reply = QMessageBox.question(self, '确认', '确定要清空所有系统日志吗？',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.system_events.clear()
            self.system_text_edit.clear()


class LogSystem(QWidget):
    """日志系统主面板"""
    
    # 信号定义
    log_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = None
        self.log_handler = None
        self.init_ui()
        self.setup_logging()
        
    def init_ui(self):
        """初始化日志系统界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 行情日志标签页
        self.market_log_panel = MarketLog()
        tab_widget.addTab(self.market_log_panel, "行情日志")
        
        # 系统日志标签页
        self.system_log_panel = SystemLog()
        tab_widget.addTab(self.system_log_panel, "系统日志")
        
    def setup_logging(self):
        """设置日志系统"""
        try:
            # 创建日志目录
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建logger
            self.logger = logging.getLogger('TradingBot')
            self.logger.setLevel(logging.INFO)
            
            # 文件处理器
            file_handler = logging.FileHandler(
                os.path.join(log_dir, f'trading_bot_{datetime.now().strftime("%Y%m%d")}.log'),
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 格式器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"设置日志系统失败: {e}")
        finally:
            # 添加测试系统事件，验证系统日志是否正常
            self.add_system_event('INFO', '系统日志模块初始化成功')
    
    def get_logger(self):
        """获取logger实例"""
        return self.logger
        
    def add_market_log(self, price_data):
        """添加行情日志"""
        self.market_log_panel.add_price_data(price_data)
        
    def add_system_event(self, event_type, description):
        """添加系统事件"""
        self.system_log_panel.add_system_event(event_type, description)
        
    def update_system_status(self, status):
        """更新系统状态"""
        self.system_log_panel.update_system_status(status)