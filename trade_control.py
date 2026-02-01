"""
交易控制模块
管理交易操作和策略执行
"""

import json
import os
import torch
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QSlider, QTabWidget, QFrame, QMessageBox,
                             QFileDialog, QGridLayout, QRadioButton, QButtonGroup)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from model import Kronos, KronosTokenizer, KronosPredictor


class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.predictor = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
    def load_models(self, base_model_path, tokenizer_model_path):
        """加载模型和分词器"""
        try:
            # 检查路径
            if not os.path.exists(base_model_path):
                raise FileNotFoundError(f"基础模型路径不存在: {base_model_path}")
            if not os.path.exists(tokenizer_model_path):
                raise FileNotFoundError(f"分词器模型路径不存在: {tokenizer_model_path}")
                
            # 加载基础模型
            print(f"正在加载基础模型从: {base_model_path}")
            self.model = Kronos.from_pretrained(base_model_path)
            
            # 加载分词器
            print(f"正在加载分词器从: {tokenizer_model_path}")
            self.tokenizer = KronosTokenizer.from_pretrained(tokenizer_model_path)
            
            # 创建预测器
            self.predictor = KronosPredictor(
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device,
                max_context=512,
                clip=5
            )
            print("模型加载成功!")
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
            
    def predict(self, df, x_timestamp, y_timestamp, pred_len=120):
        """进行预测"""
        if not self.predictor:
            return None
            
        try:
            predictions = self.predictor.predict(
                df=df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=1.0,
                top_p=0.9,
                sample_count=1,
                verbose=False
            )
            # 转换预测结果为图表数据格式
            pred_data = []
            for idx, (_, row) in enumerate(predictions.iterrows()):
                pred_timestamp = y_timestamp[idx].timestamp()
                pred_data.append({
                    'timestamp': pred_timestamp,
                    'predicted_close': row['close'],
                    'predicted_open': row['open'],
                    'predicted_high': row['high'],
                    'predicted_low': row['low'],
                    'predicted_volume': row['volume']
                })
            return pred_data
        except Exception as e:
            print(f"预测失败: {e}")
            return None

class TradeControl(QWidget):
    """交易参数设置面板"""
    
    # 信号定义
    model_loaded = pyqtSignal()
    model_manager_updated = pyqtSignal(object)  # 添加传递模型管理器的信号
    strategy_params_updated = pyqtSignal(dict)  # 策略参数更新信号
    
    def __init__(self):
        super().__init__()
        self.exchange_api = None
        self.model_manager = ModelManager()  # 正确初始化模型管理器
        
        self.init_ui()
        self.load_parameters()

    def init_ui(self):
        """初始化参数设置界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("交易参数设置")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 仓位大小设置
        position_group = QGroupBox("仓位管理")
        position_layout = QVBoxLayout(position_group)
        
        # 最大仓位比例
        max_position_layout = QHBoxLayout()
        max_position_layout.addWidget(QLabel("最大仓位比例:"))
        self.max_position_slider = QSlider(Qt.Horizontal)
        self.max_position_slider.setRange(10, 100)
        self.max_position_slider.setValue(50)
        self.max_position_slider.setTickPosition(QSlider.TicksBelow)
        self.max_position_slider.setTickInterval(10)
        self.max_position_slider.valueChanged.connect(self.update_position_label)
        max_position_layout.addWidget(self.max_position_slider)
        self.max_position_label = QLabel("50%")
        max_position_layout.addWidget(self.max_position_label)
        position_layout.addLayout(max_position_layout)
        
        # 杠杆倍数
        leverage_layout = QHBoxLayout()
        leverage_layout.addWidget(QLabel("杠杆倍数:"))
        self.leverage_input = QSpinBox()
        self.leverage_input.setRange(1, 125)
        self.leverage_input.setValue(1)
        self.leverage_input.setSuffix("x")
        leverage_layout.addWidget(self.leverage_input)
        position_layout.addLayout(leverage_layout)
        
        layout.addWidget(position_group)
        
        # 止损止盈设置
        stop_group = QGroupBox("止损止盈")
        stop_layout = QVBoxLayout(stop_group)
        
        # 止损比例
        stop_loss_layout = QHBoxLayout()
        stop_loss_layout.addWidget(QLabel("止损比例:"))
        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(0.1, 20)
        self.stop_loss_input.setValue(2.0)
        self.stop_loss_input.setSuffix(" %")
        stop_loss_layout.addWidget(self.stop_loss_input)
        stop_layout.addLayout(stop_loss_layout)
        
        # 止盈比例
        take_profit_layout = QHBoxLayout()
        take_profit_layout.addWidget(QLabel("止盈比例:"))
        self.take_profit_input = QDoubleSpinBox()
        self.take_profit_input.setRange(0.1, 50)
        self.take_profit_input.setValue(4.0)
        self.take_profit_input.setSuffix(" %")
        take_profit_layout.addWidget(self.take_profit_input)
        stop_layout.addLayout(take_profit_layout)
        
        layout.addWidget(stop_group)
        
        # 模型配置设置
        model_group = QGroupBox("模型配置")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(12)  # 增加组件间距
        
        # 基础模型路径
        base_model_layout = QHBoxLayout()
        base_model_layout.setSpacing(10)  # 增加元素间距
        
        base_model_label = QLabel("基础模型:")
        base_model_label.setMinimumWidth(100)  # 设置固定标签宽度
        base_model_layout.addWidget(base_model_label)
        
        self.base_model_path_input = QLineEdit()
        self.base_model_path_input.setPlaceholderText("请输入基础模型路径...")
        self.base_model_path_input.setText("../finetune/pretrained/Kronos-base")
        self.base_model_path_input.setMinimumWidth(100)  # 设置最小宽度
        base_model_layout.addWidget(self.base_model_path_input)
        
        browse_base_button = QPushButton("浏览...")
        browse_base_button.setMinimumWidth(80)  # 设置按钮最小宽度
        browse_base_button.setMinimumHeight(30)  # 设置按钮高度
        browse_base_button.clicked.connect(self.browse_base_model_path)
        base_model_layout.addWidget(browse_base_button)
        
        model_layout.addLayout(base_model_layout)
        
        # 分词模型路径
        tokenizer_model_layout = QHBoxLayout()
        tokenizer_model_layout.setSpacing(10)  # 增加元素间距
        
        tokenizer_model_label = QLabel("分词模型:")
        tokenizer_model_label.setMinimumWidth(100)  # 设置固定标签宽度
        tokenizer_model_layout.addWidget(tokenizer_model_label)
        
        self.tokenizer_model_path_input = QLineEdit()
        self.tokenizer_model_path_input.setPlaceholderText("请输入分词模型路径...")
        self.tokenizer_model_path_input.setText("../finetune/pretrained/Kronos-Tokenizer-base")
        self.tokenizer_model_path_input.setMinimumWidth(100)  # 设置最小宽度
        tokenizer_model_layout.addWidget(self.tokenizer_model_path_input)
        
        browse_tokenizer_button = QPushButton("浏览...")
        browse_tokenizer_button.setMinimumWidth(80)  # 设置按钮最小宽度
        browse_tokenizer_button.setMinimumHeight(30)  # 设置按钮高度
        browse_tokenizer_button.clicked.connect(self.browse_tokenizer_model_path)
        tokenizer_model_layout.addWidget(browse_tokenizer_button)
        
        model_layout.addLayout(tokenizer_model_layout)
        
        # 分割线
        model_line = QFrame()
        model_line.setFrameShape(QFrame.HLine)
        model_line.setFrameShadow(QFrame.Sunken)
        model_layout.addWidget(model_line)
        
        # 模型状态显示
        model_status_layout = QHBoxLayout()
        model_status_layout.setSpacing(10)
        
        model_status_label = QLabel("模型状态:")
        model_status_label.setMinimumWidth(100)  # 设置固定标签宽度
        model_status_layout.addWidget(model_status_label)
        
        self.model_status_label = QLabel("未加载")
        self.model_status_label.setStyleSheet("font-weight: bold; color: #DC143C;")
        self.model_status_label.setMinimumHeight(25)  # 设置标签高度
        model_status_layout.addWidget(self.model_status_label)
        
        model_layout.addLayout(model_status_layout)
        
        # 模型加载按钮
        model_load_layout = QHBoxLayout()
        model_load_layout.setSpacing(10)
        
        self.load_model_button = QPushButton("加载模型")
        self.load_model_button.setMinimumWidth(120)  # 设置按钮最小宽度
        self.load_model_button.setMinimumHeight(35)  # 设置按钮高度
        self.load_model_button.clicked.connect(self.load_models)
        self.load_model_button.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3164CC;
            }
            QPushButton:pressed {
                background-color: #1E4A99;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        model_load_layout.addWidget(self.load_model_button)
        model_layout.addLayout(model_load_layout)
        layout.addWidget(model_group)
        
        # 进场策略参数设置
        strategy_group = QGroupBox("进场策略参数")
        strategy_layout = QVBoxLayout(strategy_group)
        strategy_layout.setSpacing(15)  # 增加组件间距
        
        # 创建策略参数选项卡
        self.strategy_tabs = QTabWidget()
        
        # RSI策略选项卡
        rsi_tab = QWidget()
        rsi_tab_layout = QVBoxLayout(rsi_tab)
        rsi_tab_layout.setSpacing(15)
        
        # RSI参数详细设置
        rsi_params_layout = QGridLayout()
        rsi_params_layout.setSpacing(15)
        
        rsi_params_layout.addWidget(QLabel("超买线:"), 1, 0)
        self.rsi_overbought = QDoubleSpinBox()
        self.rsi_overbought.setRange(50, 95)
        self.rsi_overbought.setValue(70)
        self.rsi_overbought.setSingleStep(5)
        self.rsi_overbought.setMinimumWidth(100)
        self.rsi_overbought.valueChanged.connect(self.emit_strategy_params_changed)
        rsi_params_layout.addWidget(self.rsi_overbought, 1, 1)
        
        rsi_params_layout.addWidget(QLabel("超卖线:"), 2, 0)
        self.rsi_oversold = QDoubleSpinBox()
        self.rsi_oversold.setRange(5, 50)
        self.rsi_oversold.setValue(30)
        self.rsi_oversold.setSingleStep(5)
        self.rsi_oversold.setMinimumWidth(100)
        self.rsi_oversold.valueChanged.connect(self.emit_strategy_params_changed)
        rsi_params_layout.addWidget(self.rsi_oversold, 2, 1)
        
        rsi_tab_layout.addLayout(rsi_params_layout)
        rsi_tab_layout.addStretch()
        
        self.strategy_tabs.addTab(rsi_tab, "RSI")
        
        # 双均线策略选项卡
        ma_tab = QWidget()
        ma_tab_layout = QVBoxLayout(ma_tab)
        ma_tab_layout.setSpacing(15)
        
        # 双均线参数详细设置
        ma_params_layout = QGridLayout()
        ma_params_layout.setSpacing(15)
        
        ma_params_layout.addWidget(QLabel("短线周期:"), 0, 0)
        self.ma_short_period = QSpinBox()
        self.ma_short_period.setRange(5, 550)
        self.ma_short_period.setValue(40)
        self.ma_short_period.setMinimumWidth(100)
        self.ma_short_period.valueChanged.connect(self.emit_strategy_params_changed)
        ma_params_layout.addWidget(self.ma_short_period, 0, 1)
        
        ma_params_layout.addWidget(QLabel("长线周期:"), 1, 0)
        self.ma_long_period = QSpinBox()
        self.ma_long_period.setRange(5, 550)
        self.ma_long_period.setValue(120)
        self.ma_long_period.setMinimumWidth(100)
        self.ma_long_period.valueChanged.connect(self.emit_strategy_params_changed)
        ma_params_layout.addWidget(self.ma_long_period, 1, 1)
        
        ma_tab_layout.addLayout(ma_params_layout)
        ma_tab_layout.addStretch()
        
        self.strategy_tabs.addTab(ma_tab, "双均线")
        
        strategy_layout.addWidget(self.strategy_tabs)
        
        # 策略组合参数
        combo_layout = QVBoxLayout()
        combo_layout.setSpacing(10)
        
        # 创建策略单选框组 - 水平布局
        self.strategy_radio_group = QButtonGroup()
        
        # 创建水平布局的单选框
        radio_layout = QHBoxLayout()
        
        # RSI策略单选框
        self.rsi_strategy_radio = QRadioButton("RSI策略")
        self.rsi_strategy_radio.setChecked(True)  # 默认选中RSI策略
        self.rsi_strategy_radio.toggled.connect(self.emit_strategy_params_changed)
        self.strategy_radio_group.addButton(self.rsi_strategy_radio, 0)
        radio_layout.addWidget(self.rsi_strategy_radio)
        
        # 双均线策略单选框
        self.ma_strategy_radio = QRadioButton("双均线策略")
        self.ma_strategy_radio.toggled.connect(self.emit_strategy_params_changed)
        self.strategy_radio_group.addButton(self.ma_strategy_radio, 1)
        radio_layout.addWidget(self.ma_strategy_radio)
        
        combo_layout.addLayout(radio_layout)
        
        strategy_layout.addLayout(combo_layout)
        
        layout.addWidget(strategy_group)
        
        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_button = QPushButton("保存参数")
        self.save_button.clicked.connect(self.save_parameters)
        save_layout.addWidget(self.save_button)
        layout.addLayout(save_layout)
        
        layout.addStretch()

        
    def update_position_label(self, value):
        """更新仓位比例标签"""
        self.max_position_label.setText(f"{value}%")
        
    def get_parameters(self):
        """获取当前策略参数"""
        # 获取当前选中的策略
        current_strategy = ""
        if self.rsi_strategy_radio.isChecked():
            current_strategy = "RSI"
        elif self.ma_strategy_radio.isChecked():
            current_strategy = "双均线"
            
        return {
            # 基础参数
            'take_profit_ratio': self.take_profit_input.value() / 100,
            
            # 仓位管理参数
            'max_position_ratio': self.max_position_slider.value() / 100,
            'leverage': self.leverage_input.value(),
            'stop_loss_ratio': self.stop_loss_input.value() / 100,
            
            # 模型路径参数
            'base_model_path': self.base_model_path_input.text().strip(),
            'tokenizer_model_path': self.tokenizer_model_path_input.text().strip(),
            
            # RSI策略参数
            'rsi_overbought': self.rsi_overbought.value(),
            'rsi_oversold': self.rsi_oversold.value(),
            
            # 双均线策略参数
            'ma_short_period': self.ma_short_period.value(),
            'ma_long_period': self.ma_long_period.value(),
            
            # 策略组合参数 - 使用单选框选择的策略
            'strategy_mode': current_strategy,
        }
        
    def browse_base_model_path(self):
        """浏览基础模型路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择基础模型目录",
            "../finetune/pretrained"
        )
        if path:
            self.base_model_path_input.setText(path)
            
    def browse_tokenizer_model_path(self):
        """浏览分词模型路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择分词模型目录",
            "../finetune/pretrained"
        )
        if path:
            self.tokenizer_model_path_input.setText(path)
            
    def load_models(self):
        """加载模型"""
        base_model_path = self.base_model_path_input.text().strip()
        tokenizer_model_path = self.tokenizer_model_path_input.text().strip()
        
        if not base_model_path or not tokenizer_model_path:
            QMessageBox.warning(self, "警告", "请先设置模型路径")
            return
            
        # 检查路径是否存在
        if not os.path.exists(base_model_path):
            QMessageBox.critical(self, "错误", f"基础模型目录不存在:\n{base_model_path}")
            return
            
        if not os.path.exists(tokenizer_model_path):
            QMessageBox.critical(self, "错误", f"分词模型目录不存在:\n{tokenizer_model_path}")
            return
            
        try:
            self.model_status_label.setText("加载中...")
            self.model_status_label.setStyleSheet("font-weight: bold; color: #4169E1;")
            self.load_model_button.setEnabled(False)
            
            # 使用QTimer延迟执行，避免界面卡顿
            QTimer.singleShot(100, lambda: self._load_models_async(base_model_path, tokenizer_model_path))
            
        except Exception as e:
            self.model_status_label.setText("加载失败")
            self.model_status_label.setStyleSheet("font-weight: bold; color: #DC143C;")
            QMessageBox.critical(self, "错误", f"模型加载失败:\n{str(e)}")
            self.load_model_button.setEnabled(True)
            
    def _load_models_async(self, base_model_path, tokenizer_model_path):
        """异步加载模型"""
        try:
            success = self.model_manager.load_models(base_model_path, tokenizer_model_path)
            
            if success:
                self.model_status_label.setText("已加载")
                self.model_status_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
                self.model_loaded.emit()  # 发射模型加载成功信号
                self.model_manager_updated.emit(self.model_manager)  # 发射模型管理器更新信号
                QMessageBox.information(self, "成功", "模型加载成功！\n现在可以开始预测了。")
            else:
                raise Exception("模型加载失败")
                
        except Exception as e:
            self.model_status_label.setText("加载失败")
            self.model_status_label.setStyleSheet("font-weight: bold; color: #DC143C;")
            QMessageBox.critical(self, "错误", f"模型加载失败:\n{str(e)}")
        finally:
            self.load_model_button.setEnabled(True)
            
    def get_model_manager(self):
        """获取模型管理器"""
        return self.model_manager
        
    def save_parameters(self):
        """保存参数到文件"""
        params = self.get_parameters()
        
        config_dir = os.path.join(os.path.dirname(__file__), "config")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, "trade_parameters.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=2)
            QMessageBox.information(self, "成功", "交易参数已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存参数失败: {str(e)}")
            
    def load_parameters(self):
        """从文件加载参数"""
        config_file = os.path.join(os.path.dirname(__file__), "config", "trade_parameters.json")
        
        # 默认参数
        params = {
            'max_position_ratio': 0.5,
            'leverage': 1,
            'stop_loss_ratio': 0.02,
            'take_profit_ratio': 0.04,
            'base_model_path': '../finetune/pretrained/Kronos-base',
            'tokenizer_model_path': '../finetune/pretrained/Kronos-Tokenizer-base',
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'ma_short_period': 40,
            'ma_long_period': 120,
            'strategy_mode': 'RSI'
        }
        
        # 如果配置文件存在，则从文件加载
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_params = json.load(f)
                    params.update(file_params)  # 使用文件中的参数更新默认参数
            except Exception as e:
                print(f"加载交易参数失败: {e}")
        
        # 设置UI控件的值
        self.max_position_slider.setValue(int(params.get('max_position_ratio', 0.5) * 100))
        self.leverage_input.setValue(params.get('leverage', 1))
        self.stop_loss_input.setValue(int(params.get('stop_loss_ratio', 0.02) * 100))
        self.take_profit_input.setValue(int(params.get('take_profit_ratio', 0.04) * 100))

        # 加载模型路径
        base_model_path = params.get('base_model_path', '../finetune/pretrained/Kronos-base')
        tokenizer_model_path = params.get('tokenizer_model_path', '../finetune/pretrained/Kronos-Tokenizer-base')
        
        self.base_model_path_input.setText(base_model_path)
        self.tokenizer_model_path_input.setText(tokenizer_model_path)
        
        # 加载RSI策略参数
        self.rsi_overbought.setValue(params.get('rsi_overbought', 70))
        self.rsi_oversold.setValue(params.get('rsi_oversold', 30))
        
        # 加载双均线策略参数
        self.ma_short_period.setValue(params.get('ma_short_period', 40))
        self.ma_long_period.setValue(params.get('ma_long_period', 120))
        
        # 加载策略组合参数
        strategy_mode = params.get('strategy_mode', 'RSI')
        if strategy_mode == 'RSI':
            self.rsi_strategy_radio.setChecked(True)
        elif strategy_mode == '双均线':
            self.ma_strategy_radio.setChecked(True)
        else:
            # 如果是其他值，默认选中RSI
            self.rsi_strategy_radio.setChecked(True)
        
        # 检查模型是否存在并更新状态
        # 对于目录路径，检查目录内是否有必要的模型文件
        if self._check_model_directory(base_model_path) and self._check_model_directory(tokenizer_model_path):
            self.model_status_label.setText("已配置")
            self.model_status_label.setStyleSheet("font-weight: bold; color: #4169E1;")
        else:
            self.model_status_label.setText("路径不存在")
            self.model_status_label.setStyleSheet("font-weight: bold; color: #DC143C;")
        
        # 触发策略参数更新信号，确保DataDisplay能接收到初始化的参数
        self.emit_strategy_params_changed()
        
    def emit_strategy_params_changed(self):
        """发射策略参数更新信号"""
        params = self.get_parameters()
        self.strategy_params_updated.emit(params)
            
    def _check_model_directory(self, model_path):
        """检查模型目录是否包含必要的模型文件"""
        if not os.path.exists(model_path) or not os.path.isdir(model_path):
            return False
            
        # 检查常见的模型文件是否存在
        common_model_files = ['config.json', 'pytorch_model.bin', 'model.pt', 'model.pth']
        
        for file in common_model_files:
            file_path = os.path.join(model_path, file)
            if os.path.exists(file_path):
                return True
                
        # 如果目录不为空，也认为可能是有效的
        try:
            files = os.listdir(model_path)
            return len(files) > 0
        except:
            return False


# 添加预测请求信号
TradeControl.prediction_requested = pyqtSignal()