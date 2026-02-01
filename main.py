"""
交易机器人桌面应用主程序
整合所有功能模块，提供完整的交易机器人界面
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(__file__))

from PyQt5.QtGui import QIcon

from exchange_config import ExchangeConfig

from PyQt5.QtWidgets import (QApplication,
                             QHBoxLayout, QAction,
                             QToolBar, QLabel, QSplitter)
from PyQt5.QtCore import Qt, QTimer

# 导入自定义模块
from data_display import DataDisplay
from trade_control import TradeControl
from okx_api import OKXAPIClient
from log_system import LogSystem
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QStatusBar, QMessageBox)
from datetime import datetime


class LogViewWindow(QMainWindow):
    """独立的日志查看窗口"""
    
    def __init__(self, log_system, parent=None):
        super().__init__(parent)
        self.log_system = log_system
        self.init_ui()
        
    def init_ui(self):
        """初始化日志窗口界面"""
        self.setWindowTitle("日志查看 - Kronos 交易机器人")
        self.setGeometry(200, 200, 800, 600)
        
        # 设置窗口图标（如果有的话）
        self.setWindowIcon(QIcon("icon.png"))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 使用传递进来的日志系统实例，而不是创建新的
        if self.log_system:
            self.log_view = self.log_system
        else:
            # 如果没有传递日志系统，创建一个新的
            self.log_view = LogSystem()
        
        layout.addWidget(self.log_view)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("日志查看窗口已打开")
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 导出交易日志
        export_trade_action = QAction('导出交易日志', self)
        export_trade_action.triggered.connect(self.export_trade_logs)
        file_menu.addAction(export_trade_action)
        
        # 导出行情日志
        export_market_action = QAction('导出行情日志', self)
        export_market_action.triggered.connect(self.export_market_logs)
        file_menu.addAction(export_market_action)
        
        file_menu.addSeparator()
        
        # 关闭
        close_action = QAction('关闭', self)
        close_action.setShortcut('Ctrl+W')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        # 清空所有日志
        clear_all_action = QAction('清空所有日志', self)
        clear_all_action.triggered.connect(self.clear_all_logs)
        view_menu.addAction(clear_all_action)
        
    def export_trade_logs(self):
        """导出交易日志"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出交易日志", 
            f"trade_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if hasattr(self.log_view, 'trade_log_panel'):
                    success = self.log_view.trade_log_panel.export_logs(file_path)
                    if success:
                        QMessageBox.information(self, "成功", "交易日志已导出")
                        self.status_bar.showMessage(f"交易日志已导出到: {file_path}", 5000)
                    else:
                        QMessageBox.warning(self, "失败", "导出交易日志失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def export_market_logs(self):
        """导出行情日志"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出行情日志",
            f"market_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if hasattr(self.log_view, 'market_log_panel'):
                    success = self.log_view.market_log_panel.export_price_data(file_path)
                    if success:
                        QMessageBox.information(self, "成功", "行情日志已导出")
                        self.status_bar.showMessage(f"行情日志已导出到: {file_path}", 5000)
                    else:
                        QMessageBox.warning(self, "失败", "导出行情日志失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def clear_all_logs(self):
        """清空所有日志"""
        reply = QMessageBox.question(
            self, '确认', '确定要清空所有日志吗？\n此操作不可撤销。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if hasattr(self.log_view, 'trade_log_panel'):
                    self.log_view.trade_log_panel.log_entries.clear()
                    self.log_view.trade_log_panel.update_table()
                
                if hasattr(self.log_view, 'market_log_panel'):
                    self.log_view.market_log_panel.price_history.clear()
                    self.log_view.market_log_panel.update_price_table()
                
                if hasattr(self.log_view, 'system_log_panel'):
                    self.log_view.system_log_panel.system_events.clear()
                    self.log_view.system_log_panel.update_system_table()
                
                QMessageBox.information(self, "成功", "所有日志已清空")
                self.status_bar.showMessage("所有日志已清空", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空日志失败: {e}")


class TradingBotMainWindow(QMainWindow):
    """交易机器人主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.exchange_config = None
        self.exchange_api = None
        self.data_display = None
        self.trade_control = None
        self.log_system = None

        # 强制设置字体
        self.force_set_font()
        
        # 初始化界面
        self.init_ui()

    
    def force_set_font(self):
        """强制设置字体以解决中文显示问题"""
        try:
            from PyQt5.QtGui import QFont

            # 强制设置中文字体
            chinese_fonts = [
                "Microsoft YaHei UI",
                "Microsoft YaHei",
                "SimHei",
                "SimSun"
            ]

            for font_name in chinese_fonts:
                font = QFont(font_name, 9)
                if font.exactMatch():
                    self.setFont(font)
                    # 递归设置所有子控件的字体
                    self.set_all_child_fonts(self, font)
                    print(f"已强制设置字体: {font_name}")
                    break
            else:
                # 如果没有找到中文字体，使用默认字体
                default_font = QFont("Arial", 9)
                self.setFont(default_font)
                self.set_all_child_fonts(self, default_font)
                print("使用系统默认字体")

        except Exception as e:
            print(f"强制字体设置失败: {e}")

    def set_all_child_fonts(self, parent, font):
        """递归设置所有子控件的字体"""
        try:
            from PyQt5.QtWidgets import QWidget

            for child in parent.findChildren(QWidget):
                child.setFont(font)
                # 继续递归设置子控件
                if hasattr(child, 'findChildren'):
                    self.set_all_child_fonts(child, font)
        except Exception as e:
            print(f"设置子控件字体失败: {e}")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Kronos 交易机器人")
        self.setMinimumSize(1200, 800)

        # 设置窗口图标（如果有的话）
        try:
            self.setWindowIcon(QIcon("assets/icon.png"))
            pass
        except:
            pass

        # 创建菜单栏
        self.create_menu_bar()

        # 创建工具栏
        self.create_tool_bar()

        # 创建状态栏
        self.create_status_bar()

        # 创建中央布局
        self.create_central_layout()

        # 创建交易控制面板
        self.create_trading_controls()

        # 设置模块间的连接
        self.setup_connections()

        # 界面初始化完成后，自动加载配置文件
        QTimer.singleShot(100, self.load_config)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')

        # 交易所配置
        config_action = QAction('交易所配置', self)
        config_action.setShortcut('Ctrl+C')
        config_action.triggered.connect(self.show_exchange_config)
        file_menu.addAction(config_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 交易菜单
        trade_menu = menubar.addMenu('交易')

        # 开始交易
        start_trade_action = QAction('开始交易', self)
        start_trade_action.setShortcut('F5')
        start_trade_action.triggered.connect(self.start_trading)
        trade_menu.addAction(start_trade_action)

        # 停止交易
        stop_trade_action = QAction('停止交易', self)
        stop_trade_action.setShortcut('F6')
        stop_trade_action.triggered.connect(self.stop_trading)
        trade_menu.addAction(stop_trade_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具')

        # 查看日志
        log_action = QAction('查看日志', self)
        log_action.setShortcut('Ctrl+L')
        log_action.triggered.connect(self.show_log_system)
        tools_menu.addAction(log_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')

        # 关于
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # 交易所配置按钮
        config_btn = QAction('配置', self)
        config_btn.triggered.connect(self.show_exchange_config)
        toolbar.addAction(config_btn)

        toolbar.addSeparator()

        # 开始交易按钮
        self.start_btn = QAction('开始交易', self)
        self.start_btn.setEnabled(False)
        self.start_btn.triggered.connect(self.start_trading)
        toolbar.addAction(self.start_btn)

        # 停止交易按钮
        self.stop_btn = QAction('停止交易', self)
        self.stop_btn.setEnabled(False)
        self.stop_btn.triggered.connect(self.stop_trading)
        toolbar.addAction(self.stop_btn)

        toolbar.addSeparator()

        # 查看日志按钮
        log_btn = QAction('日志', self)
        log_btn.triggered.connect(self.show_log_system)
        toolbar.addAction(log_btn)

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 设置状态栏样式
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #cccccc;
            }
            QStatusBar QLabel {
                margin-right: 10px;
                margin-left: 5px;
            }
        """)

        # 连接状态
        self.connection_label = QLabel("连接状态: ✗ 未连接")
        self.connection_label.setStyleSheet("color: red;")
        self.status_bar.addWidget(self.connection_label)

        # 分隔符
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #999999; margin: 0 5px;")
        self.status_bar.addWidget(separator1)

        # 交易状态
        self.trading_label = QLabel("交易状态: 未启动")
        self.trading_label.setStyleSheet("color: orange;")
        self.status_bar.addWidget(self.trading_label)

        # 分隔符
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #999999; margin: 0 5px;")
        self.status_bar.addWidget(separator2)

        # 当前价格
        self.price_label = QLabel("BTC价格: --")
        self.status_bar.addWidget(self.price_label)

        # 分隔符
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #999999; margin: 0 5px;")
        self.status_bar.addWidget(separator3)

        # 最后更新
        self.last_update_label = QLabel("最后更新: --")
        self.status_bar.addWidget(self.last_update_label)

        # 添加弹性空间，确保消息显示在右侧
        self.status_bar.addPermanentWidget(QWidget())

    def create_central_layout(self):
        """创建中央布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 数据展示
        self.data_display = DataDisplay()
        self.data_display.start_data_update(interval_ms=15000)
        
        # 右侧面板 - 交易控制（参数设置）
        self.trade_control = TradeControl()

        # 创建日志系统（不显示在界面上，只用于功能支持）
        self.log_system = LogSystem()
        
        # 将日志系统传递给数据展示模块
        self.data_display.log_system = self.log_system  # 直接设置引用
        
        # 将图标面板添加到分割器
        splitter.addWidget(self.data_display)
        
        # 为参数设置面板创建一个容器，限制其宽度
        right_container = QWidget()
        right_container.setMaximumWidth(400)  # 适当增加最大宽度
        right_container.setMinimumWidth(350)  # 增加最小宽度
        right_container.setLayout(QVBoxLayout())
        right_container.layout().addWidget(self.trade_control)
        
        splitter.addWidget(right_container)

        # 设置分割器比例 - 显著减少间隔，给参数设置更多空间
        splitter.setSizes([600, 400])

    def setup_connections(self):
        """设置模块间的连接"""
        # 连接数据更新信号
        if self.data_display:
            # pyqtSignal.connect是PyQt5的动态方法，IDE静态分析器可能无法识别
            self.data_display.data_updated.connect(self.on_data_updated)  # type: ignore
        if self.trade_control:
            # 连接交易控制面板的模型管理器到数据展示模块
            self.trade_control.model_manager_updated.connect(self.data_display.set_model_manager)  # type: ignore
            # 连接策略参数信号
            self.trade_control.strategy_params_updated.connect(self.data_display.set_strategy_params)  # type: ignore
            # 手动触发一次策略参数更新，确保DataDisplay能接收到初始参数
            QTimer.singleShot(200, self.trade_control.emit_strategy_params_changed)

    def create_trading_controls(self):
        """创建交易控制面板（如果需要的话）"""
        # 交易控制面板已经在 create_central_layout 中创建
        # 这里可以添加额外的交易控制逻辑
        pass

    def load_config(self):
        """加载配置"""
        try:
            # 初始化交易所配置
            self.exchange_config = ExchangeConfig(self)

            # 连接配置状态变化
            self.exchange_config.connection_status_changed.connect(self.on_connection_status_changed)

            # 检查是否有保存的配置
            if self.exchange_config.api_key and self.exchange_config.secret_key and self.exchange_config.passphrase:
                # 自动尝试连接
                self.status_bar.showMessage("正在加载已保存的配置...", 2000)
                QTimer.singleShot(100, self.auto_connect)
            else:
                # 没有配置，显示提示
                self.status_bar.showMessage("请配置API密钥", 3000)

            # 更新状态栏 - 使用临时消息显示配置加载完成
            self.status_bar.showMessage("配置加载完成", 3000)  # 显示3秒后自动消失

        except Exception as e:
            print(f"加载配置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载配置失败: {e}")

    def auto_connect(self):
        """自动连接已保存的配置"""
        try:
            if not self.exchange_config:
                return

            # 只有当有完整配置时才尝试连接
            if self.exchange_config.api_key and self.exchange_config.secret_key and self.exchange_config.passphrase:
                # 更新状态为测试连接
                self.exchange_config.status_label.setText("连接状态: 自动连接中...")
                self.exchange_config.status_label.setStyleSheet("color: blue; font-weight: bold;")
                self.exchange_config.connection_info.setText("正在使用已保存的配置进行自动连接...")

                # 调用测试连接方法
                self.exchange_config.test_connection()
            else:
                print("没有找到完整的保存配置")

        except Exception as e:
            print(f"自动连接失败: {e}")
            if hasattr(self, 'exchange_config') and self.exchange_config:
                self.exchange_config.status_label.setText("连接状态: ❌ 连接失败")
                self.exchange_config.status_label.setStyleSheet("color: red; font-weight: bold;")
                self.exchange_config.connection_info.setText(f"自动连接失败: {str(e)}")

    def show_exchange_config(self):
        """显示交易所配置对话框"""
        if self.exchange_config:
            self.exchange_config.exec_()

    def show_log_system(self):
        """显示日志系统"""
        # 创建独立的日志查看窗口
        log_window = LogViewWindow(self.log_system, self)
        log_window.show()
        log_window.raise_()
        log_window.activateWindow()

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 Kronos 交易机器人",
                         """
                         <h3>Kronos 交易机器人</h3>
                         <p>版本: 1.0.0</p>
                         <p>一个基于OKX API的自动化交易机器人</p>
                         <p>功能包括:</p>
                         <ul>
                         <li>实时市场数据监控</li>
                         <li>自动化交易策略</li>
                         <li>风险控制管理</li>
                         <li>详细的交易日志</li>
                         </ul>
                         <p>开发日期: 2024年</p>
                         """)

    def start_trading(self):
        """开始交易"""
        try:
            if not self.exchange_config or not self.exchange_config.is_connected:
                QMessageBox.warning(self, "警告", "请先配置并连接交易所")
                return

            # 更新状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.trading_label.setText("交易状态: 运行中")
            self.trading_label.setStyleSheet("color: green;")

            # 记录日志
            if self.log_system:
                self.log_system.add_system_event('INFO', '交易系统已启动')
            if self.data_display:
                self.data_display.trade_flag = True
            self.status_bar.showMessage("交易系统已启动", 3000)  # 显示3秒后自动消失

        except Exception as e:
            print(f"启动交易失败: {e}")
            QMessageBox.critical(self, "错误", f"启动交易失败: {e}")

    def stop_trading(self):
        """停止交易"""
        try:
            # 更新状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.trading_label.setText("交易状态: 已停止")
            self.trading_label.setStyleSheet("color: red;")

            # 记录日志
            if self.log_system:
                self.log_system.add_system_event('INFO', '交易系统已停止')
            if self.data_display:
                self.data_display.trade_flag = False
            self.status_bar.showMessage("交易系统已停止", 3000)  # 显示3秒后自动消失

        except Exception as e:
            print(f"停止交易失败: {e}")

    def on_connection_status_changed(self, connected):
        """连接状态变化回调"""
        if connected:
            self.connection_label.setText("连接状态: ✓ 已连接")
            self.connection_label.setStyleSheet("color: green;")
            self.start_btn.setEnabled(True)

            # 连接成功后，初始化 OKX API 客户端
            try:
                if self.exchange_config:
                    credentials = self.exchange_config.get_api_credentials()
                    if credentials:
                        # 创建 OKX API 客户端
                        self.exchange_api = OKXAPIClient(
                            api_key=credentials['api_key'],
                            secret_key=credentials['secret_key'],
                            passphrase=credentials['passphrase']
                        )
                        self.data_display.set_exchange_api(self.exchange_api)

                        # 测试 API 连接
                        test_result = self.exchange_api.get_account_balance()
                        if test_result and test_result.get('code') == '0':
                            # 记录日志
                            if self.log_system:
                                self.log_system.add_system_event('INFO', 'OKX API 连接成功，开始获取数据')
                        else:
                            if self.log_system:
                                self.log_system.add_system_event('ERROR', 'OKX API 连接测试失败')
                            self.exchange_api = None

            except Exception as e:
                print(f"初始化 OKX API 客户端失败: {e}")
                self.exchange_api = None

            # 记录日志
            if self.log_system:
                self.log_system.add_system_event('INFO', '交易所连接成功')

        else:
            self.connection_label.setText("连接状态: ✗ 未连接")
            self.connection_label.setStyleSheet("color: red;")
            self.start_btn.setEnabled(False)

            # 清除 API 客户端
            self.exchange_api = None

            # 停止交易
            if self.stop_btn.isEnabled():
                self.stop_trading()

    def on_data_updated(self, data):
        """数据更新回调"""
        try:
            # 更新价格标签
            if 'price' in data:
                price = data['price']
                if hasattr(self, 'price_label'):
                    self.price_label.setText(f"${float(price['last']):.2f}")
            # 更新时间戳
            if hasattr(self, 'last_update_label'):
                from datetime import datetime
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_update_label.setText(f"最后更新: {current_time}")

        except Exception as e:
            print(f"处理数据更新失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(self, '确认退出', '确定要退出交易机器人吗？',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # 关闭交易所连接
                # (如果有的话)

                event.accept()

            except Exception as e:
                print(f"关闭应用时出错: {e}")
                event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    # 在创建QApplication之前设置环境变量以强制使用中文字体
    import os
    os.environ['QT_QPA_PLATFORM'] = 'windows'
    os.environ['QT_SCALE_FACTOR'] = '1.0'

    # 导入并设置matplotlib字体（必须在创建QApplication之前）
    import matplotlib
    matplotlib.use('Qt5Agg')
    setup_matplotlib_chinese_font()

    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setApplicationName("Kronos 交易机器人")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Kronos Trading")

    # 立即设置字体 - 在创建窗口之前
    setup_chinese_font_aggressive(app)

    # 创建主窗口
    window = TradingBotMainWindow()

    # 强制设置主窗口字体
    force_set_window_font(window)

    window.show()

    # 运行应用程序
    sys.exit(app.exec_())


def setup_chinese_font_aggressive(app):
    """激进地设置中文字体支持 - 强制覆盖所有字体"""
    import platform
    import os

    try:
        from PyQt5.QtGui import QFont, QFontDatabase, QFontMetrics
        from PyQt5.QtCore import Qt

        print("开始设置中文字体...")

        # 检测系统类型并设置相应字体
        system = platform.system()

        if system == "Windows":
            # Windows系统优先字体
            preferred_fonts = [
                "Microsoft YaHei UI",
                "Microsoft YaHei",
                "SimHei",
                "SimSun",
                "Arial Unicode MS"
            ]
        elif system == "Darwin":  # macOS
            # macOS系统优先字体
            preferred_fonts = [
                "PingFang SC",
                "Hiragino Sans GB",
                "Heiti SC",
                "Songti SC",
                "Arial Unicode MS"
            ]
        else:  # Linux
            # Linux系统优先字体
            preferred_fonts = [
                "WenQuanYi Zen Hei",
                "WenQuanYi Micro Hei",
                "Noto Sans CJK SC",
                "Source Han Sans SC",
                "Arial Unicode MS"
            ]

        # 查找可用的字体
        font_database = QFontDatabase()
        available_fonts = font_database.families()

        selected_font = None
        for font_name in preferred_fonts:
            if font_name in available_fonts:
                selected_font = font_name
                break

        if selected_font:
            # 创建字体对象
            font = QFont(selected_font, 9)
            font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)

            # 激进地设置所有可能的控件类型字体
            widget_classes = [
                "QLabel", "QPushButton", "QMenu", "QMenuBar", "QStatusBar",
                "QToolBar", "QTabWidget", "QComboBox", "QGroupBox",
                "QTextEdit", "QLineEdit", "QSpinBox", "QDoubleSpinBox",
                "QCheckBox", "QRadioButton", "QProgressBar", "QSlider",
                "QTreeWidget", "QListWidget", "QTableWidget", "QTextBrowser",
                "QScrollBar", "QFrame", "QDialog", "QMainWindow"
            ]

            for widget_class in widget_classes:
                try:
                    app.setFont(font, widget_class)
                except:
                    pass

            # 全局字体设置
            app.setFont(font)

            # 强制设置默认字体（使用更直接的方法）
            app.style().unpolish(app)
            app.style().polish(app)

            print(f"✓ 已设置中文字体: {selected_font}")
            print(f"✓ 字体样式: {font.styleName()}")
            print(f"✓ 字体大小: {font.pointSize()}pt")

        else:
            # 如果没有找到中文字体，使用系统默认字体
            system_default = app.font().family()
            font = QFont(system_default, 9)
            font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
            app.setFont(font)
            print(f"⚠ 使用系统默认字体: {system_default}")
            print("⚠ 建议安装中文字体包以获得更好的显示效果")

        # 设置抗锯齿和高DPI支持
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 设置字体渲染优化
        if hasattr(QFont, 'HintingPreference'):
            font.setHintingPreference(QFont.PreferFullHinting)

        print("✓ 字体设置完成")

    except Exception as e:
        print(f"❌ 字体设置失败: {e}")
        # 即使字体设置失败，应用程序也应该能正常运行
        pass


def setup_chinese_font(app):
    """设置中文字体支持 (兼容性函数)"""
    return setup_chinese_font_aggressive(app)


def setup_matplotlib_chinese_font():
    """设置matplotlib中文字体"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import platform

        print("开始设置matplotlib中文字体...")

        # 查找中文字体
        if platform.system() == "Windows":
            # Windows系统优先字体
            chinese_fonts = [
                "Microsoft YaHei UI",
                "Microsoft YaHei",
                "SimHei",
                "SimSun",
                "Arial Unicode MS"
            ]
        elif platform.system() == "Darwin":  # macOS
            chinese_fonts = [
                "PingFang SC",
                "Hiragino Sans GB",
                "Heiti SC",
                "Songti SC"
            ]
        else:  # Linux
            chinese_fonts = [
                "WenQuanYi Zen Hei",
                "WenQuanYi Micro Hei",
                "Noto Sans CJK SC",
                "Source Han Sans SC"
            ]
        
        # 获取可用字体
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        selected_font = None
        for font_name in chinese_fonts:
            if font_name in available_fonts:
                selected_font = font_name
                break
        
        if selected_font:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
            print(f"✓ matplotlib字体已设置为: {selected_font}")
        else:
            # 如果没找到中文字体，使用系统默认字体
            system_fonts = [f.name for f in fm.fontManager.ttflist if any(keyword in f.name.lower() 
                          for keyword in ['system', 'default', 'sans'])]
            if system_fonts:
                plt.rcParams['font.sans-serif'] = [system_fonts[0]] + plt.rcParams['font.sans-serif']
                print(f"⚠ 使用系统字体: {system_fonts[0]}")
            else:
                print("⚠ 未找到合适的matplotlib字体")
                
    except Exception as e:
        print(f"matplotlib字体设置失败: {e}")


def force_set_window_font(window):
    """强制设置窗口及其所有子控件的字体"""
    try:
        from PyQt5.QtGui import QFont, QFontDatabase
        from PyQt5.QtCore import QObject
        
        print("强制设置窗口字体...")
        
        # 获取已设置的字体
        font_name = None
        font_size = 9
        
        # 查找中文字体
        font_db = QFontDatabase()
        available_fonts = font_db.families()
        
        chinese_fonts = [
            "Microsoft YaHei UI",
            "Microsoft YaHei", 
            "SimHei",
            "SimSun",
            "Arial Unicode MS"
        ]
        
        for font in chinese_fonts:
            if font in available_fonts:
                font_name = font
                break
        
        if not font_name:
            font_name = window.font().family()
            print(f"使用默认字体: {font_name}")
        
        # 创建字体对象
        font = QFont(font_name, font_size)
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        
        # 强制设置窗口字体
        window.setFont(font)
        
        # 递归设置所有子控件字体
        def set_font_recursive(widget):
            try:
                # 设置当前控件字体
                widget.setFont(font)
                
                # 递归设置子控件
                for child in widget.findChildren(QObject):
                    try:
                        if hasattr(child, 'setFont'):
                            child.setFont(font)
                    except:
                        pass
                        
            except Exception as e:
                print(f"设置字体时出错: {e}")
        
        set_font_recursive(window)
        
        print(f"✓ 窗口字体已强制设置为: {font_name}")
        
    except Exception as e:
        print(f"强制设置窗口字体失败: {e}")


if __name__ == '__main__':
    main()