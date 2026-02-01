"""
技术指标计算模块
实现RSI、双均线等常用技术指标的计算和信号生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_sma(data: pd.Series, window: int) -> pd.Series:
        """计算简单移动平均线 (SMA)"""
        return data.rolling(window=window).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, span: int) -> pd.Series:
        """计算指数移动平均线 (EMA)"""
        return data.ewm(span=span).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2) -> Dict[str, pd.Series]:
        """计算布林带"""
        sma = TechnicalIndicators.calculate_sma(data, window)
        std = data.rolling(window=window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }


class TradingSignals:
    """交易信号生成器"""
    
    def __init__(self):
        self.last_signals = {}

    def generate_rsi_signal(self, data: List[float], params: Dict) -> Dict:
        # 1. 增强的参数验证与数据准备
        required_params = ['period', 'overbought', 'oversold']
        if not all(k in params for k in required_params):
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'RSI参数配置不完整'}

        period = params['period']
        overbought = params['overbought']
        oversold = params['oversold']

        # 验证阈值逻辑
        if overbought <= oversold:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'RSI阈值设置错误(overbought需大于oversold)'}

        # 计算RSI所需的最小数据量
        if len(data) < period + 1:  # RSI计算至少需要period+1个价格点
            return {'signal': 'hold', 'strength': 0.0,
                    'reason': f'数据不足，计算RSI({period})至少需要{period + 1}个数据点'}

        try:
            data_series = pd.Series(data)
            rsi_series = TechnicalIndicators.calculate_rsi(data_series, period=period)
        except Exception as e:
            return {'signal': 'hold', 'strength': 0.0, 'reason': f'RSI指标计算错误: {str(e)}'}

        if len(rsi_series) < 3:  # 至少需要3个点进行基本分析
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'RSI数据序列太短'}

        current_rsi = rsi_series.iloc[-1]

        # 2. 定义核心信号和强度
        primary_signal = 'hold'
        primary_strength = 0.0
        primary_reason = '无明确信号'

        # 3. 信号逻辑：优先处理超买/超卖 (更强的信号)
        # 超卖反弹信号 (BUY)
        if current_rsi <= oversold:
            primary_signal = 'buy'
            # 强度计算：结合绝对水平和相对距离
            # 当RSI越低（如10），强度越大，而不仅仅是看距离oversold(如30)的百分比
            depth_factor = (oversold - current_rsi) / oversold  # 低于阈值的深度
            level_factor = 1.0 - (current_rsi / 30.0) if current_rsi < 30 else 0.3  # 绝对水平因子
            primary_strength = min(depth_factor * level_factor * 1.5, 1.0)  # 适当放大
            primary_reason = f'RSI超卖 ({current_rsi:.1f})'

        # 超买回调信号 (SELL)
        elif current_rsi >= overbought:
            primary_signal = 'sell'
            depth_factor = (current_rsi - overbought) / (100 - overbought)
            level_factor = (current_rsi - 70.0) / 30.0 if current_rsi > 70 else 0.3
            primary_strength = min(depth_factor * level_factor * 1.5, 1.0)
            primary_reason = f'RSI超买 ({current_rsi:.1f})'

        # 4. 增强的背离信号检测（作为次要确认信号）
        divergence_signal = 'hold'
        divergence_strength = 0.0
        divergence_reason = ''
        lookback_period = min(30, len(rsi_series))  # 用于寻找极值点的回溯期

        if lookback_period >= 10:
            # 寻找价格和RSI在最近lookback_period期内的极值点（简化示例：价格与RSI的3期高点/低点）
            price_extremes = self._find_extremes(data_series.iloc[-lookback_period:], window=3)
            rsi_extremes = self._find_extremes(rsi_series.iloc[-lookback_period:], window=3)

            # 检测背离：价格新低而RSI未新低（底背离 -> 看涨）
            if len(price_extremes['lows']) >= 2 and len(rsi_extremes['lows']) >= 2:
                latest_price_low_idx = price_extremes['lows'][-1]
                prev_price_low_idx = price_extremes['lows'][-2]
                latest_rsi_low_idx = rsi_extremes['lows'][-1]
                prev_rsi_low_idx = rsi_extremes['lows'][-2]

                # 价格创新低，但RSI低点抬高
                if (data_series.iloc[latest_price_low_idx] < data_series.iloc[prev_price_low_idx] and
                        rsi_series.iloc[latest_rsi_low_idx] > rsi_series.iloc[prev_rsi_low_idx]):
                    divergence_signal = 'buy'
                    divergence_strength = 0.6  # 背离信号基础强度
                    divergence_reason = '底背离(价格新低，RSI抬高)'

            # 检测背离：价格新高而RSI未新高（顶背离 -> 看跌）
            elif len(price_extremes['highs']) >= 2 and len(rsi_extremes['highs']) >= 2:
                latest_price_high_idx = price_extremes['highs'][-1]
                prev_price_high_idx = price_extremes['highs'][-2]
                latest_rsi_high_idx = rsi_extremes['highs'][-1]
                prev_rsi_high_idx = rsi_extremes['highs'][-2]

                if (data_series.iloc[latest_price_high_idx] > data_series.iloc[prev_price_high_idx] and
                        rsi_series.iloc[latest_rsi_high_idx] < rsi_series.iloc[prev_rsi_high_idx]):
                    divergence_signal = 'sell'
                    divergence_strength = 0.6
                    divergence_reason = '顶背离(价格新高，RSI降低)'

        # 5. 信号整合逻辑：背离可强化或提供早期信号，但不与主信号冲突
        final_signal = primary_signal
        final_strength = primary_strength
        final_reason = primary_reason

        if divergence_signal != 'hold':
            if primary_signal == 'hold':
                # 仅有背离信号：作为早期预警
                final_signal = divergence_signal
                final_strength = divergence_strength * 0.8  # 纯背离信号强度打折
                final_reason = f'早期{divergence_reason}'
            elif primary_signal == divergence_signal:
                # 主信号与背离同向：强化信号
                final_strength = min(primary_strength + divergence_strength * 0.3, 1.0)
                final_reason = f'{primary_reason} 且 {divergence_reason}，信号强化'
            # 如果主信号与背离信号相反，则忽略背离（主信号优先级更高）

        return {
            'signal': final_signal,
            'strength': round(final_strength, 2),
            'reason': final_reason,
            'data': {
                'rsi': round(current_rsi, 2),
                'has_divergence': divergence_signal != 'hold',
                'divergence_type': divergence_reason
            }
        }

    def _find_extremes(self, series: pd.Series, window: int = 3):
        """辅助函数：在序列中查找局部极值点（高点/低点）"""
        highs = []
        lows = []

        for i in range(window, len(series) - window):
            if all(series.iloc[i] > series.iloc[i - j] for j in range(1, window + 1)) and \
                    all(series.iloc[i] > series.iloc[i + j] for j in range(1, window + 1)):
                highs.append(i)
            elif all(series.iloc[i] < series.iloc[i - j] for j in range(1, window + 1)) and \
                    all(series.iloc[i] < series.iloc[i + j] for j in range(1, window + 1)):
                lows.append(i)

        return {'highs': highs, 'lows': lows}

    def generate_ma_signal(self, data: List[float], params: Dict) -> Dict:
        """生成增强版双均线交易信号"""
        # 1. 参数验证与数据准备
        required_params = ['short_period', 'long_period']
        if not all(k in params for k in required_params):
            return {'signal': 'hold', 'strength': 0.0, 'reason': '参数配置不完整'}

        short_period = params['short_period']
        long_period = params['long_period']

        if len(data) < long_period:
            return {'signal': 'hold', 'strength': 0.0, 'reason': '数据长度不足'}

        try:
            data_series = pd.Series(data)
            short_ma = TechnicalIndicators.calculate_sma(data_series, short_period)
            long_ma = TechnicalIndicators.calculate_sma(data_series, long_period)
        except Exception as e:
            return {'signal': 'hold', 'strength': 0.0, 'reason': f'指标计算错误: {str(e)}'}

        # 2. 数据充足性检查
        if len(short_ma) < 2 or len(long_ma) < 2:
            return {'signal': 'hold', 'strength': 0.0, 'reason': '数据不足'}

        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]

        # 3. 计算波动率用于信号强度标准化
        recent_volatility = data_series.iloc[-short_period:].std()
        volatility_factor = 1.0
        if recent_volatility > 0:
            # 当波动率过大时，降低对单纯均线交叉的敏感度
            volatility_factor = min(1.0, 0.01 / recent_volatility)  # 假设0.01为基准波动率

        signal = 'hold'
        strength = 0.0
        reason = '无明确信号'
        crossover_threshold = current_long * 0.001  # 交叉阈值设为长均线的0.1%

        # 4. 增强版金叉/死叉判断（带阈值）
        # 金叉买入信号
        if (prev_short <= prev_long) and ((current_short - current_long) > crossover_threshold):
            signal = 'buy'
            base_strength = abs(current_short - current_long) / current_long
            strength = min(base_strength * volatility_factor, 1.0)
            reason = f'金叉买入 (短{current_short:.2f} > 长{current_long:.2f}, 强度{strength:.2f})'

        # 死叉卖出信号
        elif (prev_short >= prev_long) and ((current_long - current_short) > crossover_threshold):
            signal = 'sell'
            base_strength = abs(current_short - current_long) / current_long
            strength = min(base_strength * volatility_factor, 1.0)
            reason = f'死叉卖出 (短{current_short:.2f} < 长{current_long:.2f}, 强度{strength:.2f})'

        # 5. （可选）保留但改进的“价格偏离”逻辑，作为趋势中的回调入场信号
        # 此处以“上涨趋势中的回调买入”为例
        if signal == 'hold' and current_short > current_long:  # 处于上涨趋势
            price = data_series.iloc[-1]
            # 价格回调到短均线附近（例如，低于短均线0.5%~2%）
            if current_short * 0.98 <= price <= current_short * 0.995:
                signal = 'buy'
                strength = 0.3  # 回调入场，强度设置为中等
                reason = f'上涨趋势中价格回调至短均线附近买入'

        return {
            'signal': signal,
            'strength': round(strength, 2),
            'reason': reason,
            'data': {
                'short_ma': round(current_short, 2),
                'long_ma': round(current_long, 2),
                'volatility': round(recent_volatility, 4) if 'recent_volatility' in locals() else None
            }
        }


class StrategyEngine:
    """策略引擎 - 整合所有技术指标和信号生成"""
    
    def __init__(self):
        self.signals_generator = TradingSignals()
    
    def analyze_market(self, kline_data, strategy_params: Dict) -> Dict:
        """分析市场并生成交易信号"""
        if len(kline_data) < 16:
            return {
                'signal': 'hold',
                'strength': 0.0,
                'reason': '数据不足',
                'indicators': {},
                'individual_signals': []
            }
        
        # 使用收盘价进行技术分析
        close_prices = [record['close'] for record in kline_data]

        # RSI策略
        if strategy_params['strategy_mode'] == 'RSI':
            rsi_params = {
                'period': 20,
                'overbought': strategy_params.get('rsi_overbought', 70),
                'oversold': strategy_params.get('rsi_oversold', 30)
            }
            rsi_signal = self.signals_generator.generate_rsi_signal(close_prices[-12 * 4:], rsi_params)
            return rsi_signal
        else:
            # 双均线策略
            ma_params = {
                'short_period': strategy_params.get('ma_short_period', 40),
                'long_period': strategy_params.get('ma_long_period', 120)
            }
            ma_signal = self.signals_generator.generate_ma_signal(close_prices[-ma_params['long_period'] * 2:],
                                                                  ma_params)
            return ma_signal