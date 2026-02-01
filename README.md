# Kronos 交易机器人

## 项目简介

Kronos 是一个基于 PyQt5 开发的比特币交易机器人桌面应用，集成了 OKX 交易所 API，提供实时市场数据监控、自动化交易策略、风险控制管理和详细的交易日志功能。

## 功能特性

### 🏢 功能模块

1. **交易所配置模块**
   - API密钥管理（OKX API Key 和 Secret Key）
   - 密钥验证和连接测试
   - 安全加密存储

2. **数据展示模块**
   - 实时BTC 15分钟K线图
   - 账户信息面板（余额、持仓、收益率、未实现盈亏）
   - 持仓详情表格
   - 价格走势图表

3. **交易控制模块**
   - 交易参数设置（止损、止盈、仓位大小）
   - 手动交易操作（买入、卖出、平仓）
   - 自动交易开关和策略选择
   - 交易状态监控

4. **日志系统**
   - 交易日志记录
   - 市场行情日志
   - 系统错误和警告日志
   - 日志过滤和导出功能

### 🎨 界面设计

- **顶部工具栏**：配置按钮、启动/停止控制
- **左侧数据面板**：账户信息、持仓详情
- **中央图表区域**：价格走势与预测对比
- **右侧控制面板**：交易参数设置、手动交易
- **底部日志区域**：实时日志显示

## 项目结构

```
AutoTradeBot/
├── assets/              # 资源文件
│   └── icon.png
├── config/              # 配置文件
│   ├── account.key      # 加密的API密钥
│   ├── exchange_config.json  # 交易所配置
│   └── trade_parameters.json  # 交易参数
├── logs/                # 日志文件
│   └── trading_bot_*.log
├── model/               # 模型文件
│   ├── __init__.py
│   ├── kronos.py
│   └── module.py
├── main.py              # 主程序入口
├── exchange_config.py   # 交易所配置模块
├── data_display.py      # 数据展示模块
├── trade_control.py     # 交易控制模块
├── log_system.py        # 日志系统模块
├── okx_api.py           # OKX API接口
├── technical_indicators.py  # 技术指标计算
├── build_exe.bat        # 构建可执行文件批处理
├── build_exe.py         # 构建可执行文件脚本
├── KronosBot.spec       # PyInstaller配置文件
├── start.bat            # 启动脚本
├── requirements.txt     # 依赖项列表
└── README.md           # 项目说明文档
```

## 安装和运行

### 环境要求

- Python 3.7+
- PyQt5
- matplotlib
- pandas
- numpy
- cryptography
- requests
- python-dateutil
- pyqt5-sip

### 安装依赖

```bash
# 使用requirements.txt安装所有依赖
pip install -r requirements.txt
```

### 运行应用

```bash
# 直接运行主程序
python main.py

# 或使用启动脚本
start.bat
```

### 构建可执行文件

```bash
# 使用批处理脚本构建
build_exe.bat

# 或使用Python脚本构建
python build_exe.py
```

## 使用指南

### 1. 交易所配置

1. 点击顶部工具栏的"配置"按钮或使用菜单 `文件 > 交易所配置`
2. 输入您的 OKX API Key 和 Secret Key
3. 点击"测试连接"验证API密钥
4. 配置会自动加密保存

### 2. 数据监控

- 应用启动后会自动加载市场数据
- 左侧面板显示账户信息
- 中央区域显示实时价格图表
- 右侧面板显示交易参数

### 3. 手动交易

1. 在交易参数面板设置止损、止盈、仓位大小
2. 点击买入/卖出按钮执行手动交易
3. 点击平仓按钮关闭当前仓位

### 4. 自动交易

1. 在交易控制面板勾选"启用自动交易"
2. 选择交易策略（RSI策略、双均线策略）
3. 点击顶部工具栏的"开始交易"按钮

### 5. 日志监控

- 底部日志区域实时显示系统日志
- 可以过滤查看不同类型的日志
- 支持日志导出功能

## 快捷键

- `Ctrl+C`：打开交易所配置
- `Ctrl+L`：查看日志
- `F5`：开始交易
- `F6`：停止交易
- `Ctrl+Q`：退出应用

## 安全提醒

⚠️ **重要提醒**：
- 请妥善保管您的API密钥
- 建议在测试环境中先验证功能
- 交易有风险，请谨慎使用
- 建议设置合理的止损和仓位大小

## 技术架构

- **前端框架**：PyQt5
- **图表绘制**：matplotlib
- **数据处理**：pandas, numpy
- **API集成**：OKX API
- **加密存储**：cryptography
- **多线程**：QThread

## 开发者信息

- 应用名称：Kronos 交易机器人
- 版本：1.0.0
- 开发时间：2024年
- 基于：OKX 交易所 API

## 许可证

本项目仅供学习和研究使用。实际交易请谨慎操作，交易风险由用户自行承担。

---

**免责声明**：本软件仅供学习和研究目的。使用本软件进行真实交易的风险完全由用户承担。开发者不对任何交易损失承担责任。