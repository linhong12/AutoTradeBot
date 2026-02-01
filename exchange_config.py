"""
交易所配置模块
管理OKX API密钥和连接配置
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QWidget, QPushButton, QMessageBox, QTabWidget)
from PyQt5.QtCore import pyqtSignal
from okx import Account, Trade

from okx_api import OKXAPIClient


class ExchangeConfig(QDialog):
    """交易所配置对话框"""
    
    # 信号定义
    connection_status_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = ""
        self.secret_key = ""
        self.passphrase = ""
        self.exchange_api = None
        self.is_connected = False
        self.init_ui()
        self.load_config()

    def set_exchange_api(self, exchange_api):
        """设置交易所API实例"""
        self.exchange_api = exchange_api

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("交易所配置")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # API配置标签页
        self.create_api_config_tab(tab_widget)
        
        # 测试连接标签页
        self.create_test_tab(tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def create_api_config_tab(self, tab_widget):
        """创建API配置标签页"""
        api_widget = QWidget()
        layout = QVBoxLayout(api_widget)
        
        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_input)
        layout.addLayout(api_key_layout)
        
        # Secret Key
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(QLabel("Secret Key:"))
        self.secret_key_input = QLineEdit()
        self.secret_key_input.setEchoMode(QLineEdit.Password)
        secret_layout.addWidget(self.secret_key_input)
        layout.addLayout(secret_layout)
        
        # Passphrase
        passphrase_layout = QHBoxLayout()
        passphrase_layout.addWidget(QLabel("Passphrase:"))
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.Password)
        passphrase_layout.addWidget(self.passphrase_input)
        layout.addLayout(passphrase_layout)
        
        # 说明文本
        info_label = QLabel("""
        请在OKX官网获取API密钥：
        1. 登录OKX官网 (okx.com)
        2. 进入"账户" -> "API管理"
        3. 创建新的API密钥
        4. 设置适当的权限（读取、交易等）
        
        安全提醒：
        - 请妥善保管您的API密钥
        - 建议设置IP白名单
        - 定期更换密钥
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        tab_widget.addTab(api_widget, "API配置")
        
    def create_test_tab(self, tab_widget):
        """创建测试连接标签页"""
        test_widget = QWidget()
        layout = QVBoxLayout(test_widget)
        
        # 连接状态
        self.status_label = QLabel("连接状态: 未测试")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 测试按钮
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        layout.addWidget(self.test_button)
        
        # 连接信息
        self.connection_info = QLabel("点击'测试连接'验证API密钥是否有效")
        self.connection_info.setWordWrap(True)
        layout.addWidget(self.connection_info)
        
        layout.addStretch()
        
        tab_widget.addTab(test_widget, "连接测试")
        
    def save_config(self):
        """保存配置"""
        self.api_key = self.api_key_input.text().strip()
        self.secret_key = self.secret_key_input.text().strip()
        self.passphrase = self.passphrase_input.text().strip()
        
        if not all([self.api_key, self.secret_key, self.passphrase]):
            QMessageBox.warning(self, "警告", "请填写完整的API配置信息")
            return
            
        # 保存到配置文件
        config_data = {
            "api_key": self.encrypt_data(self.api_key),
            "secret_key": self.encrypt_data(self.secret_key),
            "passphrase": self.encrypt_data(self.passphrase)
        }
        
        config_dir = os.path.join(os.path.dirname(__file__), "config")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, "exchange_config.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
                
            QMessageBox.information(self, "成功", "配置已保存")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
            
    def load_config(self):
        """加载配置"""
        config_file = os.path.join(os.path.dirname(__file__), "config", "exchange_config.json")
        
        if not os.path.exists(config_file):
            return
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            self.api_key = self.decrypt_data(config_data.get("api_key", ""))
            self.secret_key = self.decrypt_data(config_data.get("secret_key", ""))
            self.passphrase = self.decrypt_data(config_data.get("passphrase", ""))
            
            # 填充输入框
            self.api_key_input.setText(self.api_key)
            self.secret_key_input.setText(self.secret_key)
            self.passphrase_input.setText(self.passphrase)
            
        except Exception as e:
            print(f"加载配置失败: {e}")
            
    def test_connection(self):
        """测试API连接"""
        if not all([self.api_key_input.text(), self.secret_key_input.text(), self.passphrase_input.text()]):
            QMessageBox.warning(self, "警告", "请先填写API配置信息")
            return
            
        self.test_button.setEnabled(False)
        self.test_button.setText("测试中...")
        
        try:
            # 更新配置
            self.api_key = self.api_key_input.text()
            self.secret_key = self.secret_key_input.text()
            self.passphrase = self.passphrase_input.text()
            self.exchange_api = OKXAPIClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                passphrase=self.passphrase
            )
            # 尝试获取账户信息
            result = self.exchange_api.get_account_balance()
            
            if result.get('code') == '0':
                self.status_label.setText("连接状态: ✅ 连接成功")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.connection_info.setText("API密钥有效，可以正常连接OKX交易所")
                self.is_connected = True
                self.connection_status_changed.emit(True)
                
            else:
                raise Exception(result.get('msg', '未知错误'))
                
        except Exception as e:
            self.status_label.setText("连接状态: ❌ 连接失败")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connection_info.setText(f"连接失败: {str(e)}")
            self.is_connected = False
            self.connection_status_changed.emit(False)
            
        finally:
            self.test_button.setEnabled(True)
            self.test_button.setText("测试连接")
            
    def get_config_dialog(self, parent):
        """获取配置对话框"""
        return self
        
    def is_connected(self):
        """检查是否已连接"""
        return self.is_connected
        
    def get_api_credentials(self):
        """获取API凭据"""
        return {
            "api_key": self.api_key,
            "secret_key": self.secret_key,
            "passphrase": self.passphrase,
            "flag": "0"  # 实盘
        }
        
    def encrypt_data(self, data):
        """加密数据"""
        if not data:
            return ""
            
        key_file = os.path.join(os.path.dirname(__file__), "config", "account.key")
        
        # 生成或加载加密密钥
        if not os.path.exists(key_file):
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        else:
            with open(key_file, 'rb') as f:
                key = f.read()
                
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
        
    def decrypt_data(self, encrypted_data):
        """解密数据"""
        if not encrypted_data:
            return ""
            
        try:
            key_file = os.path.join(os.path.dirname(__file__), "config", "account.key")
            
            if not os.path.exists(key_file):
                return ""
                
            with open(key_file, 'rb') as f:
                key = f.read()
                
            f = Fernet(key)
            decrypted_data = f.decrypt(base64.b64decode(encrypted_data))
            return decrypted_data.decode()
            
        except Exception:
            return ""