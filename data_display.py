"""
数据展示模块
显示实时价格、图表和账户信息
"""

from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QTableWidget, QTableWidgetItem, QFrame)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont

import pandas as pd


# 导入技术指标模块
from technical_indicators import StrategyEngine
from operator import itemgetter


class DataUpdateThread(QThread):
    """后台数据更新线程"""
    
    # 信号定义
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    log_event = pyqtSignal(str, str)
    
    def __init__(self, exchange_api, strategy_params=None, log_system=None):
        super().__init__()
        self.exchange_api = exchange_api
        self.strategy_params = strategy_params
        self.log_system = log_system
        self.strategy_engine = StrategyEngine()
        self.running = False
        
    def run(self):
        """线程运行方法"""
        self.running = True
        try:
            self._update_data()
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
    
    def _update_data(self):
        """更新数据"""
        if not self.exchange_api:
            return
        
        try:
            # 存储所有数据的字典
            all_data = {
                'account': {},
                'price': {},
                'positions': [],
                'chart_data': [],
                'trade_signals': None,
                'pred_data': None
            }
            
            # 获取账户信息
            account_result = self.exchange_api.get_account_balance()
            if account_result.get('code') == '0':
                all_data['account'] = {
                    'balances': account_result.get('data', [{}])[0].get('details', [])
                }
            
            # 获取价格信息
            ticker_result = self.exchange_api.get_ticker(inst_id='BTC-USDT-SWAP')
            if ticker_result.get('code') == '0':
                ticker_data = ticker_result.get('data', [{}])[0]
                all_data['price'] = {
                    'last': ticker_data.get('last', 0),
                    'change24h': round((float(ticker_data.get('last', 0)) - float(ticker_data.get('sodUtc8', 0))) /
                                 float(ticker_data.get('sodUtc8', 0)) * 100, 2),
                    'high_24h': ticker_data.get('high24h', 0),
                    'low_24h': ticker_data.get('low24h', 0),
                    'vol24h': ticker_data.get('vol24h', 0)
                }
            
            # 获取K线数据
            request_count = 2
            klines_data = []
            after = None
            while request_count > 0:
                klines_result = self.exchange_api.get_klines(
                    inst_id='BTC-USDT-SWAP', 
                    bar='15m', 
                    limit=300, 
                    after=after
                )
                if klines_result.get('code') == '0':
                    klines_data_tmp = klines_result.get('data', [])
                    klines_data += klines_data_tmp
                    after = klines_data_tmp[-1][0]
                    request_count -= 1
            
            # 转换K线数据
            if klines_data:
                for kline in klines_data:
                    try:
                        timestamp = int(kline[0]) / 1000
                        all_data['chart_data'].append({
                            'timestamp': timestamp,
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    except (ValueError, IndexError):
                        continue
                
                # 排序
                all_data['chart_data'].sort(key=lambda x: x['timestamp'])

            # 如果有策略参数，进行技术分析
            if self.strategy_params and all_data['chart_data']:
                # 取最近8小时数据进行指标计算
                analysis_result = self.strategy_engine.analyze_market(all_data['chart_data'], self.strategy_params)
                # 通过信号发送日志事件到主线程处理
                self.log_event.emit('INFO', f"[信号检测]: {analysis_result}")
                # 生成交易信号
                if analysis_result['signal'] in ['buy', 'sell']:
                    all_data['price']['signal'] = analysis_result['signal']
                    current_price = float(all_data['price'].get('last', 0))
                    all_data['trade_signals'] = [{
                        'timestamp': datetime.now().timestamp(),
                        'price': current_price,
                        'signal': analysis_result['signal'],
                        'strength': analysis_result['strength'],
                        'reason': analysis_result['reason']
                    }]
            
            # 获取持仓信息
            positions_result = self.exchange_api.get_positions()
            if positions_result.get('code') == '0':
                all_data['positions'] = positions_result.get('data', [])
            
            # 发送数据就绪信号
            self.data_ready.emit(all_data)
            
        except Exception as e:
            error_msg = f"数据更新失败: {str(e)}"
            self.error_occurred.emit(error_msg)
            if self.log_system:
                self.log_system.add_system_event('ERROR', error_msg)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()


class PriceChart(QWidget):
    """价格图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.predictions = []
        self.trade_signals = []
        self.init_ui()
        
    def init_ui(self):
        """初始化图表界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建matplotlib图形
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 初始化图表
        self.ax = self.figure.add_subplot(111)
        self.setup_chart()
        
    def setup_chart(self):
        """设置图表样式"""
        self.ax.set_title('BTC-USDT-SWAP 15分钟K线图', fontsize=14, fontweight='bold')
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel('价格 (USDT)')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(['实际价格', '预测价格', '买入信号', '卖出信号'])
        
    def update_chart(self, data, predictions=None, trade_signals=None):
        """更新图表数据"""
        if not data:
            return
        
        # 只在数据变化较大时才全量更新
        data_changed = False
        if len(data) != len(self.data):
            data_changed = True
        else:
            # 检查最后几个数据点是否变化
            for i in range(max(1, min(5, len(data)))):
                if abs(data[-i]['close'] - self.data[-i]['close']) > 0.01:
                    data_changed = True
                    break
        
        if not data_changed and not predictions and not trade_signals:
            return  # 数据没有显著变化，跳过更新
        
        # 更新数据
        self.data = data
        self.predictions = predictions or []
        self.trade_signals = trade_signals or []
        
        # 清除之前的图形
        self.ax.clear()
        self.setup_chart()
        
        try:
            # 绘制实际价格
            timestamps = [datetime.fromtimestamp(d['timestamp']) for d in data]
            prices = [d['close'] for d in data]
            
            # 限制数据点数量，提高渲染性能
            max_points = 100
            if len(timestamps) > max_points:
                step = len(timestamps) // max_points
                timestamps = timestamps[::step]
                prices = prices[::step]
            
            self.ax.plot(timestamps, prices, 'b-', linewidth=1, label='实际价格')
            
            # 绘制预测价格（使用红色虚线）
            if self.predictions:
                pred_timestamps = [datetime.fromtimestamp(p['timestamp']) for p in self.predictions]
                pred_prices = [p['predicted_close'] for p in self.predictions]  # 修正字段名
                
                # 限制预测点数量
                if len(pred_timestamps) > 50:
                    step = len(pred_timestamps) // 50
                    pred_timestamps = pred_timestamps[::step]
                    pred_prices = pred_prices[::step]
                
                self.ax.plot(pred_timestamps, pred_prices, 'r-', linewidth=1, label='预测价格')
                
                # 在预测线两端添加标记
                if len(pred_timestamps) > 0 and len(timestamps) > 0:
                    # 在实际价格最后一点到预测价格第一点之间画连接线
                    last_actual_time = timestamps[-1]
                    last_actual_price = prices[-1]
                    first_pred_time = pred_timestamps[0]
                    first_pred_price = pred_prices[0]
                    
                    # 添加连接线
                    self.ax.plot([last_actual_time, first_pred_time], 
                               [last_actual_price, first_pred_price], 
                               color='#FF6600', linestyle=':', alpha=0.5, linewidth=1)
                            
            # 绘制交易信号
            if self.trade_signals:
                # 只显示最近的交易信号，最多10个
                recent_signals = self.trade_signals[-10:]
                buy_signals = [s for s in recent_signals if s['signal'] == 'buy']
                sell_signals = [s for s in recent_signals if s['signal'] == 'sell']
                
                if buy_signals:
                    buy_times = [datetime.fromtimestamp(s['timestamp']) for s in buy_signals]
                    buy_prices = [s['price'] for s in buy_signals]
                    self.ax.scatter(buy_times, buy_prices, color='green', marker='^', s=80, label='买入信号')
                    
                if sell_signals:
                    sell_times = [datetime.fromtimestamp(s['timestamp']) for s in sell_signals]
                    sell_prices = [s['price'] for s in sell_signals]
                    self.ax.scatter(sell_times, sell_prices, color='red', marker='v', s=80, label='卖出信号')
            
            # 设置时间轴格式
            if timestamps:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
                plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45)
                
            # 自动调整y轴范围
            if prices:
                price_min = min(prices)
                price_max = max(prices)
                price_range = price_max - price_min
                self.ax.set_ylim(price_min - price_range * 0.05, price_max + price_range * 0.05)
                
            # 使用blit技术提高渲染性能
            self.figure.canvas.draw_idle()
        except Exception as e:
            # self.log_system.add_system_event('ERROR', f"[数据更新] 更新图表失败: {e}")
            # 发生错误时仍尝试绘制，确保界面不会崩溃
            self.canvas.draw()
        
    def add_data_point(self, data_point):
        """添加新的数据点"""
        self.data.append(data_point)
        if len(self.data) > 200:  # 保持最近200个数据点
            self.data.pop(0)
        self.update_chart(self.data, self.predictions, self.trade_signals)
        

class AccountPanel(QWidget):
    """账户信息面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化账户面板界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("账户信息")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 账户余额
        balance_layout = QHBoxLayout()
        balance_layout.addWidget(QLabel("总资产:"))
        self.total_balance_label = QLabel("0.00 USDT")
        self.total_balance_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        balance_layout.addWidget(self.total_balance_label)
        layout.addLayout(balance_layout)
        
        # 可用余额
        available_layout = QHBoxLayout()
        available_layout.addWidget(QLabel("可用余额:"))
        self.available_balance_label = QLabel("0.00 USDT")
        available_layout.addWidget(self.available_balance_label)
        layout.addLayout(available_layout)
        
        # BTC持仓
        btc_layout = QHBoxLayout()
        btc_layout.addWidget(QLabel("BTC余额:"))
        self.btc_balance_label = QLabel("0.00000000 BTC")
        btc_layout.addWidget(self.btc_balance_label)
        layout.addLayout(btc_layout)
        
        # 分割线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # 当前价格
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("BTC价格:"))
        self.btc_price_label = QLabel("0.00 USDT")
        self.btc_price_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        price_layout.addWidget(self.btc_price_label)
        layout.addLayout(price_layout)
        
        # 24小时变化
        change_layout = QHBoxLayout()
        change_layout.addWidget(QLabel("24h变化:"))
        self.price_change_label = QLabel("0.00%")
        self.price_change_label.setStyleSheet("font-weight: bold;")
        change_layout.addWidget(self.price_change_label)
        layout.addLayout(change_layout)
        
        # 分割线
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line3)
        
        # 收益率
        pnl_layout = QHBoxLayout()
        pnl_layout.addWidget(QLabel("当天总收益率:"))
        self.pnl_label = QLabel("0.00%")
        self.pnl_label.setStyleSheet("font-weight: bold;")
        pnl_layout.addWidget(self.pnl_label)
        layout.addLayout(pnl_layout)
        
        # 未实现盈亏
        unrealized_layout = QHBoxLayout()
        unrealized_layout.addWidget(QLabel("未实现收益率:"))
        self.unrealized_pnl_label = QLabel("0.00 USDT")
        unrealized_layout.addWidget(self.unrealized_pnl_label)
        layout.addLayout(unrealized_layout)
        
        layout.addStretch()

    def update_account_info(self, account_info, price_info=None):
        """更新账户信息"""
        try:
            # 更新余额信息
            available_btc = 0
            available_usdt = 0
            
            if 'balances' in account_info:
                for balance in account_info['balances']:
                    if balance['ccy'] == 'USDT':
                        available_usdt = float(balance['availBal'])
                    elif balance['ccy'] == 'BTC':
                        available_btc = float(balance['availBal'])
                        
                self.total_balance_label.setText(f"{available_usdt:.2f} USDT")
                self.available_balance_label.setText(f"{available_usdt:.2f} USDT")
                self.btc_balance_label.setText(f"{available_btc:.8f} BTC")
            
            # 更新价格信息并计算当天总收益率
            if price_info:
                price = float(price_info.get('last', 0))
                change_24h = float(price_info.get('change24h', 0))

                self.btc_price_label.setText(f"{price:.2f} USDT")
                
                if change_24h >= 0:
                    self.price_change_label.setText(f"+{change_24h:.2f}%")
                    self.price_change_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
                else:
                    self.price_change_label.setText(f"{change_24h:.2f}%")
                    self.price_change_label.setStyleSheet("font-weight: bold; color: #DC143C;")
                    
        except Exception as e:
            print(f"更新账户信息失败: {e}")


class PositionTable(QWidget):
    """持仓表格"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化持仓表格界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("当前持仓")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "交易对", "方向", "数量", "入场价", "当前价", "盈亏", "盈亏率"
        ])
        
        # 设置表格样式
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
    def update_positions(self, positions):
        """更新持仓信息"""
        try:
            self.table.setRowCount(len(positions))
            
            for row, position in enumerate(positions):
                self.table.setItem(row, 0, QTableWidgetItem(position.get('instId', '')))
                self.table.setItem(row, 1, QTableWidgetItem(position.get('posSide', '')))
                self.table.setItem(row, 2, QTableWidgetItem(f"{float(position.get('pos', 0)):.8f}"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{float(position.get('avgPx', 0)):.2f}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{float(position.get('markPx', 0)):.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(f"{float(position.get('upl', 0)):.2f}"))
                self.table.setItem(row, 6, QTableWidgetItem(f"{float(position.get('uplRatio', 0)) * 100:.2f}%"))
        except Exception as e:
            print(f"更新持仓信息失败: {e}")


class DataDisplay(QWidget):
    """数据展示主窗口"""

    # 信号定义
    data_updated = pyqtSignal(dict)
    prediction_requested = pyqtSignal(dict)  # 添加预测请求信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.exchange_api = None
        self.model_manager = None  # 添加模型管理器引用
        self.pred_data = None
        self.log_system = None
        self.trade_flag = False
        self.strategy_engine = StrategyEngine()  # 初始化策略引擎
        self.strategy_params = {}  # 存储策略参数
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data)
        
        # 初始化后台数据更新线程
        self.data_thread = None
        self.thread_lock = False  # 防止线程并发执行
        
        self.init_ui()

    def init_ui(self):
        """初始化主界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 左侧账户信息面板
        left_panel = QVBoxLayout()

        self.account_panel = AccountPanel()
        left_panel.addWidget(self.account_panel)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(300)

        layout.addWidget(left_widget)

        # 右侧垂直布局（图表在上，持仓表格在下）
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        # 价格图表
        self.price_chart = PriceChart()
        right_layout.addWidget(self.price_chart, 3)  # 图表占3份
        
        # 持仓表格
        self.position_table = PositionTable()
        right_layout.addWidget(self.position_table, 1)  # 持仓表格占1份
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        layout.addWidget(right_widget)

        # 设置布局比例
        layout.setStretch(0, 0)  # 左侧面板不拉伸
        layout.setStretch(1, 1)  # 右侧区域拉伸

    def set_exchange_api(self, exchange_api):
        """设置交易所API实例"""
        self.exchange_api = exchange_api

    def set_model_manager(self, model_manager):
        """设置模型管理器实例"""
        self.model_manager = model_manager
        
    def set_log_system(self, log_system):
        """设置日志系统实例"""
        self.log_system = log_system
        
    def set_strategy_params(self, strategy_params):
        """设置策略参数"""
        self.strategy_params = strategy_params

    def start_data_update(self, interval_ms=15000):
        """开始数据更新"""
        self.data_timer.start(interval_ms)

    def update_data(self):
        """更新数据显示"""
        if not self.exchange_api or self.thread_lock:
            return
        
        # 设置线程锁，防止并发执行
        self.thread_lock = True
        
        try:
            # 创建并启动后台数据更新线程
            self.data_thread = DataUpdateThread(
                exchange_api=self.exchange_api,
                strategy_params=self.strategy_params,
                log_system=self.log_system
            )
            
            # 连接信号
            self.data_thread.data_ready.connect(self.on_data_ready)
            self.data_thread.error_occurred.connect(self.on_thread_error)
            self.data_thread.log_event.connect(self.on_log_event)
            
            # 启动线程
            self.data_thread.start()
        except Exception as e:
            if self.log_system:
                self.log_system.add_system_event('ERROR', f'启动数据更新线程失败: {str(e)}')
            self.thread_lock = False
    
    def on_data_ready(self, all_data):
        """后台线程数据准备就绪回调"""
        try:
            # 获取数据
            account_data = all_data['account']
            price_info = all_data['price']
            positions_data = all_data['positions']
            chart_data = all_data['chart_data']
            trade_signals = all_data['trade_signals']

            # 更新账户信息
            if account_data:
                self.account_panel.update_account_info(account_data, price_info)
            
            # 更新持仓表格
            if positions_data:
                # 筛选活跃持仓（非零持仓）
                active_positions = [pos for pos in positions_data if float(pos.get('pos', 0)) != 0]
                self.position_table.update_positions(active_positions)
                if not self.pred_data:
                    self._model_predict(chart_data)
            else:
                # 当没有持仓数据时，清空持仓表格
                self.position_table.update_positions([])
            
            # 模型预测和交易信号处理
            if trade_signals and self.trade_flag:
                # 模型预测(第一次或上一个订单已结束)
                if not self.pred_data or not positions_data:
                    self._model_predict(chart_data)
                # 判断当前是否存在挂单及持仓
                pend_result = self.exchange_api.get_pending_orders()
                if not pend_result.get('data') and not positions_data:
                    # 根据策略参数和预测结果下单交易
                    self.trade(price_info, trade_signals)
                elif pend_result.get('data'):
                    if not pend_result.get('data')[0]['side'] == trade_signals[0]['signal']:
                        self.exchange_api.cancel_order(inst_id='BTC-USDT-SWAP',
                                                       ord_id=pend_result.get('data')[0]['ordId'])
                        if self.log_system:
                            self.log_system.add_system_event('INFO', f"[下单交易] 已取消当前挂单，{pend_result.get('data')[0]['ordId']}！")
                    if self.log_system:
                        self.log_system.add_system_event('INFO', f"[下单交易] 当前已存在挂单，不予下单！")
            # 更新图表
            self.update_chart(chart_data, self.pred_data, trade_signals)
            
            # 记录行情日志
            self._record_market_log(price_info)
            
            # 发射数据更新信号
            self.data_updated.emit({
                'account': account_data,
                'price': price_info,
                'positions': positions_data
            })
        except Exception as e:
            if self.log_system:
                self.log_system.add_system_event('ERROR', f'处理后台数据失败: {str(e)}')
        finally:
            # 释放线程锁
            self.thread_lock = False
    
    def on_thread_error(self, error_msg):
        """后台线程错误回调"""
        if self.log_system:
            self.log_system.add_system_event('ERROR', f'后台线程错误: {error_msg}')
        # 释放线程锁
        self.thread_lock = False
    
    def on_log_event(self, level, message):
        """后台线程日志事件回调"""
        if self.log_system:
            self.log_system.add_system_event(level, message)

    def _model_predict(self, klines_data, pred_len=120):
        df_data = []
        # 转换K线数据为DataFrame格式
        if klines_data:
            for kline in klines_data:
                # 转换时间戳为可读格式
                readable_time = datetime.fromtimestamp(kline['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                # 提取所需字段，保留原始时间戳用于排序
                df_data.append([
                    readable_time,  # timestamps
                    kline['open'],  # open
                    kline['close'],  # close
                    kline['high'],  # high
                    kline['low'],  # low
                    kline['volume'],  # volume
                    0  # amount (volumeCcyQuote)
                ])
        # 模型预测（如果有模型管理器）
        if self.model_manager and df_data:

            df = pd.DataFrame(df_data[-500:],
                              columns=['timestamps', 'open', 'close', 'high', 'low', 'volume', 'amount'])
            df['timestamps'] = pd.to_datetime(df['timestamps'])
            x_timestamp = df['timestamps']
            y_timestamp = x_timestamp.iloc[-30:len(df)]
            last_timestamp = y_timestamp.iloc[-1]
            x_df = df[['open', 'close', 'high', 'low', 'volume', 'amount']]

            additional_timestamps = pd.date_range(
                start=last_timestamp + pd.Timedelta(minutes=15),
                periods=pred_len - 30,
                freq='15min'
            )
            extended_y_timestamp = pd.concat([
                pd.Series(y_timestamp),
                pd.Series(additional_timestamps)
            ], ignore_index=True)
            self.pred_data = self.model_manager.predict(x_df, x_timestamp, extended_y_timestamp, pred_len)

    def predict_analysis(self, ped_data) -> dict:
        result = {
            'direction': None,
            'maxPrice': 0,
            'minPrice': 0,
            'startPrice': 0,
            'endPrice': 0,
        }
        if ped_data:
            max_record = max(self.pred_data, key=itemgetter('predicted_close'))
            min_record = min(self.pred_data, key=itemgetter('predicted_close'))
            start_record = self.pred_data[0]
            end_record = self.pred_data[-1]
            if (max_record['predicted_close'] - min_record['predicted_close']) / max_record['predicted_close'] < 0.02:
                result['direction'] = "flat"
            else:
                if max_record['timestamp'] > min_record['timestamp']:
                    result['direction'] = "buy"
                else:
                    result['direction'] = "sell"
            result['maxPrice'] = max_record['predicted_close']
            result['minPrice'] = min_record['predicted_close']
            result['startPrice'] = start_record['predicted_close']
            result['endPrice'] = end_record['predicted_close']
        return result

    def trade(self, price_info, trade_signals):
        predict_analysis_data = self.predict_analysis(self.pred_data)
        if predict_analysis_data['direction'] == trade_signals[0]['signal']:
            # 设置杠杆
            self.exchange_api.set_leverage(lever=self.strategy_params['leverage'], inst_id='BTC-USDT-SWAP')
            # 使用位置比例模式，不再计算order_value
            position_ratio = self.strategy_params['max_position_ratio']
            side = ''
            px = ''
            tp_trigger_px = None
            sl_trigger_px = None

            if predict_analysis_data['direction'] == 'buy':
                side = 'buy'
                if float(price_info['last']) < predict_analysis_data['minPrice']:
                    px = price_info['last']
                else:
                    px = str(predict_analysis_data['minPrice'])
                
                # 期货交易支持完整的止盈止损功能
                if self.strategy_params['take_profit_ratio'] > 0:
                    tp_trigger_px = float(px) * (1 + self.strategy_params['take_profit_ratio'])
                    if predict_analysis_data['maxPrice'] < tp_trigger_px:
                        tp_trigger_px = str(predict_analysis_data['maxPrice'])
                    else:
                        tp_trigger_px = str(tp_trigger_px)
                if self.strategy_params['stop_loss_ratio'] > 0:
                    sl_trigger_px = str(float(px) * (1 - self.strategy_params['stop_loss_ratio']))

            elif predict_analysis_data['direction'] == 'sell':
                side = 'sell'
                if float(price_info['last']) > predict_analysis_data['maxPrice']:
                    px = price_info['last']
                else:
                    px = str(predict_analysis_data['maxPrice'])
                
                # 期货交易支持完整的止盈止损功能
                if self.strategy_params['take_profit_ratio'] > 0:
                    tp_trigger_px = float(px) * (1 - self.strategy_params['take_profit_ratio'])
                    if predict_analysis_data['minPrice'] > tp_trigger_px:
                        tp_trigger_px = str(predict_analysis_data['minPrice'])
                    else:
                        tp_trigger_px = str(tp_trigger_px)

                if self.strategy_params['stop_loss_ratio'] > 0:
                    sl_trigger_px = str(float(px) * (1 + self.strategy_params['stop_loss_ratio']))

            # 期货交易下单（使用位置比例模式，支持完整止盈止损功能）
            result = self.exchange_api.place_order(
                inst_id='BTC-USDT-SWAP',
                td_mode='isolated',  # 期货交易使用isolated模式
                side=side,
                ord_type='limit', 
                px=px,
                tp_trigger_px=tp_trigger_px,
                sl_trigger_px=sl_trigger_px,
                position_ratio=position_ratio  # 使用位置比例模式
            )
            self.log_event.emit('INFO', f"[下单交易] 下单结果: {result}")

        else:
            self.log_event.emit('INFO', "[下单交易] 交易信号与模型预测不一致，不予交易！")

    def _record_market_log(self, price_info):
        """记录行情日志"""
        # 构建行情数据，确保字段名与MarketLog.add_price_data一致
        market_data = {
            'price': float(price_info.get('last', 0)),
            'change_24h': price_info.get('change24h', 0),
            'volume_24h': float(price_info.get('vol24h', 0)),
            'signal': price_info.get('signal', 'hold'),
        }
        # 调用日志系统的行情日志记录方法
        self.log_system.add_market_log(market_data)

    def _convert_klines_to_chart_data(self, klines_data):
        """将OKX K线数据转换为图表数据格式"""
        chart_data = []
        
        for kline in klines_data:
            try:
                # OKX K线数据格式: [timestamp, open, high, low, close, volume, volume_currency, confirm]
                timestamp = int(kline[0]) / 1000  # 转换为秒
                chart_data.append({
                    'timestamp': timestamp,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            except (ValueError, IndexError) as e:
                self.log_event.emit('ERROR', f"转换K线数据失败: {e}")
                continue
                
        # 按时间戳排序，确保数据按时间顺序显示
        chart_data.sort(key=lambda x: x['timestamp'])
        
        return chart_data

    def update_chart(self, data, predictions=None, trade_signals=None):
        """更新图表"""
        self.price_chart.update_chart(data, predictions, trade_signals)
        
    def update_chart_with_predictions(self, predictions):
        """使用预测数据更新图表"""
        # 获取当前实际数据
        current_data = self.price_chart.data
        if current_data:
            self.update_chart(current_data, predictions, self.price_chart.trade_signals)
        
    def update_display_data(self, data):
        """统一数据更新接口"""
        try:
            # 更新账户信息
            if 'account' in data:
                self.account_panel.update_account_info(data['account'], data.get('price'))
            
            # 更新图表数据
            if 'chart_data' in data:
                self.update_chart(data['chart_data'])
                
        except Exception as e:
            self.log_event.emit('ERROR', f"转换K线数据失败: {e}")

        
    def get_current_chart_data(self):
        """获取当前图表数据"""
        return self.price_chart.data