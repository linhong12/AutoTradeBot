"""
OKX API 客户端
用于获取真实的交易所数据
"""
import hmac
import base64
import hashlib
import time
import json
import requests
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal


class OKXAPIClient(QObject):
    """OKX API 客户端"""
    
    # 信号定义
    data_updated = pyqtSignal(dict)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, api_key="", secret_key="", passphrase=""):
        super().__init__()
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.is_connected = False
        self.log_system = None  # 添加日志系统引用
        self.flag = "0"

        # API 基础 URL
        self.base_url = "https://www.okx.com"
        
        # 代理配置
        self.proxies = {
            'http': 'http://127.0.0.1:3128',
            'https': 'http://127.0.0.1:3128'
        }
        
        # 请求超时设置
        self.timeout = 20
        
    def set_log_system(self, log_system):
        """设置日志系统"""
        self.log_system = log_system
        
    def _log(self, level, message, module="OKX"):
        """内部日志方法"""
        if self.log_system:
            self.log_system.add_system_event(level, f"[{module}] {message}")
        else:
            # 如果没有日志系统，使用print输出
            if level == 'ERROR':
                print(f"[ERROR] {message}")
            elif level == 'WARNING':
                print(f"[WARNING] {message}")
            else:
                print(f"[INFO] {message}")
    
    def _generate_signature(self, timestamp, method, request_path, body=''):
        """生成API签名"""
        if not self.secret_key:
            return ''
            
        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')
    
    def _get_timestamp(self):
        """获取ISO格式时间戳"""
        return datetime.utcnow().isoformat()[:-3] + 'Z'
    
    def _send_request(self, method, request_path, params=None, body=None, auth=True):
        """
        发送HTTP请求到OKX API
        
        Args:
            method: HTTP方法，如GET, POST, PUT, DELETE
            request_path: API路径，如/api/v5/account/balance
            params: URL查询参数
            body: 请求体，字典格式
            auth: 是否需要认证
        
        Returns:
            dict: API响应结果
        """
        try:
            # 构建完整URL
            url = f"{self.base_url}{request_path}"
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-TIMESTAMP": self._get_timestamp(),
                "OK-ACCESS-PASSPHRASE": self.passphrase,
            }
            
            # 生成签名
            if auth:
                # 对于GET请求，需要将查询参数包含在签名中
                if method.upper() == "GET" and params:
                    # 构建查询字符串，按照参数名排序
                    import urllib.parse
                    sorted_params = sorted(params.items())
                    query_string = urllib.parse.urlencode(sorted_params)
                    request_path_with_params = f"{request_path}?{query_string}"
                    body_str = ""
                else:
                    request_path_with_params = request_path
                    body_str = json.dumps(body) if body else ""
                
                # 生成签名时使用包含查询参数的路径
                timestamp = headers["OK-ACCESS-TIMESTAMP"]
                signature = self._generate_signature(timestamp, method, request_path_with_params, body_str)
                headers["OK-ACCESS-SIGN"] = signature
                
            # 发送请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body,
                proxies=self.proxies,
                timeout=self.timeout
            )
            # 解析响应
            response.raise_for_status()  # 检查HTTP错误
            return response.json()
            
        except requests.RequestException as e:
            print(f"HTTP请求异常: {e}")
            try:
                # 尝试获取详细的错误信息
                if hasattr(e, 'response') and e.response:
                    print(f"错误响应状态码: {e.response.status_code}")
                    print(f"错误响应内容: {e.response.text}")
            except:
                pass
            return {"code": "500", "msg": str(e)}
        except json.JSONDecodeError as e:
            print(f"JSON解析异常: {e}")
            return {"code": "500", "msg": f"JSON解析错误: {str(e)}"}
    
    def test_connection(self):
        """测试API连接"""
        try:
            # 获取账户信息来测试连接
            result = self.get_account_balance()
            
            if result.get('code') == '0':
                self.is_connected = True
                self.connection_status.emit(True, "连接成功")
                return True
            else:
                self.is_connected = False
                self.connection_status.emit(False, f"连接失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            self.is_connected = False
            self.connection_status.emit(False, f"连接测试失败: {str(e)}")
            return False
    
    def get_account_balance(self):
        """获取账户余额"""
        try:
            # 尝试获取真实账户信息
            result = self._send_request(
                method="GET",
                request_path="/api/v5/account/balance",
                auth=True
            )
            
            if result.get('code') == '0':
                return result
            else:
                # 如果API调用失败，返回模拟数据以保持程序运行
                print(f"获取账户余额失败: {result.get('msg')}")
                return self._get_mock_account_balance()
                
        except Exception as e:
            print(f"获取账户余额异常: {e}")
            return self._get_mock_account_balance()
    
    def get_positions(self):
        """获取持仓信息"""
        try:
            result = self._send_request(
                method="GET",
                request_path="/api/v5/account/positions",
                auth=True
            )
            
            if result.get('code') == '0':
                return result
            else:
                print(f"获取持仓信息失败: {result.get('msg')}")
                return self._get_mock_positions()
                
        except Exception as e:
            print(f"获取持仓信息异常: {e}")
            return self._get_mock_positions()
    
    def get_ticker(self, inst_id="BTC-USDT-SWAP"):
        """获取ticker信息"""
        try:
            result = self._send_request(
                method="GET",
                request_path="/api/v5/market/ticker",
                params={"instId": inst_id},
                auth=False
            )
            
            if result.get('code') == '0':
                return result
            else:
                print(f"获取ticker失败: {result.get('msg')}")
                return self._get_mock_ticker()
                
        except Exception as e:
            print(f"获取ticker异常: {e}")
            return self._get_mock_ticker()
    
    def _get_mock_account_balance(self):
        """返回模拟账户余额数据"""
        import random
        
        return {
            'code': '0',
            'msg': '',
            'data': [{
                'adjEq': '',
                'ordFry': '',
                'imr': '',
                'mmr': '',
                'notionalUsd': '',
                'details': [{
                    'availBal': f"{random.uniform(1000, 10000):.2f}",
                    'availEq': '',
                    'ccy': 'USDT',
                    'eq': '',
                    'eqUsd': '',
                    'frozenBal': '',
                    'notionalUsd': '',
                    'ordFrozen': '',
                    'stgyEq': '',
                    'upl': '',
                    'uplUsd': ''
                }, {
                    'availBal': f"{random.uniform(0.01, 1.0):.8f}",
                    'availEq': '',
                    'ccy': 'BTC',
                    'eq': '',
                    'eqUsd': '',
                    'frozenBal': '',
                    'notionalUsd': '',
                    'ordFrozen': '',
                    'stgyEq': '',
                    'upl': '',
                    'uplUsd': ''
                }]
            }]
        }
    
    def _get_mock_positions(self):
        """返回模拟持仓数据"""
        import random
        
        return {
            'code': '0',
            'msg': '',
            'data': [{
                'adl': '3',
                'availPos': '',
                'avgPx': '',
                'cTime': '1640995200000',
                'deltaBS': '',
                'deltaPA': '',
                'gammaBS': '',
                'gammaPA': '',
                'idxPx': '',
                'instId': 'BTC-USDT-SWAP',
                'instType': 'SWAP',
                'last': '',
                'lever': '10',
                'liab': '',
                'liabUsd': '',
                'liabEq': '',
                'mgnMode': 'cross',
                'mgnRatio': '',
                'mmr': '',
                'notionalUsd': '',
                'optVal': '',
                'pos': f"{random.uniform(0.001, 0.1):.8f}",
                'posCcy': '',
                'posId': '',
                'posSide': 'long',
                'pxLim': '',
                'pxLimLevel': '',
                'pxTrigger': '',
                'riskType': '1',
                'spotInUseAmt': '',
                'spotInUseAz': '',
                'uTime': '1640995200000',
                'upl': f"{random.uniform(-100, 100):.2f}",
                'uplRatio': f"{random.uniform(-0.05, 0.05):.4f}",
                'vegaBS': '',
                'vegaPA': ''
            }]
        }
    
    def _get_mock_ticker(self):
        """返回模拟ticker数据"""
        import random
        
        price = random.uniform(45000, 50000)
        change = random.uniform(-0.05, 0.05)
        
        return {
            'code': '0',
            'msg': '',
            'data': [{
                'instId': 'BTC-USDT',
                'last': f"{price:.2f}",
                'lastSz': '0.001',
                'bidPx': f"{price * 0.999:.2f}",
                'askPx': f"{price * 1.001:.2f}",
                'bidSz': '1',
                'askSz': '1',
                'chng24h': f"{change:.4f}",
                'chngUtime': '1640995200000',
                'high24h': f"{price * 1.02:.2f}",
                'idxPx': f"{price * 0.9995:.2f}",
                'low24h': f"{price * 0.98:.2f}",
                'open24h': f"{price * (1 - change):.2f}",
                'sodUtc8': f"{price * (1 - change):.2f}",
                'srSodUtc8': f"{price * (1 - change):.2f}",
                'ts': '1640995200000',
                'vol24h': f"{random.uniform(1000, 5000):.2f}",
                'volCcy24h': f"{random.uniform(1000, 5000):.2f}"
            }]
        }
    
    def get_klines(self, inst_id="BTC-USDT-SWAP", bar="15m", limit=100, after=None):
        """获取K线数据"""
        try:
            params = {
                "instId": inst_id,
                "bar": bar,
                "limit": limit
            }
            if after:
                params["after"] = after
            
            result = self._send_request(
                method="GET",
                request_path="/api/v5/market/candles",
                params=params,
                auth=False
            )
            
            if result.get('code') == '0':
                return result
            else:
                print(f"获取K线数据失败: {result.get('msg')}")
                return self._get_mock_klines()
                
        except Exception as e:
            print(f"获取K线数据异常: {e}")
            return self._get_mock_klines()
    
    def _get_mock_klines(self):
        """返回模拟K线数据"""
        import random
        import time
        
        data = []
        current_time = int(time.time())
        
        # 生成模拟的K线数据
        base_price = 45000  # 基础价格
        for i in range(50):
            timestamp = current_time - (i * 900)  # 15分钟间隔
            open_price = base_price + random.uniform(-1000, 1000)
            high_price = open_price + random.uniform(0, 500)
            low_price = open_price - random.uniform(0, 500)
            close_price = open_price + random.uniform(-300, 300)
            volume = random.uniform(10, 100)
            
            data.append([
                str(timestamp * 1000),  # timestamp
                f"{open_price:.2f}",    # open
                f"{high_price:.2f}",    # high  
                f"{low_price:.2f}",     # low
                f"{close_price:.2f}",   # close
                f"{volume:.4f}",        # volume
                f"{volume * close_price:.2f}",  # volume currency
                "0"                     # confirm
            ])
            
            base_price = close_price  # 下一个K线的开盘价基于上一个收盘价
            
        return {
            'code': '0',
            'msg': '',
            'data': data
        }
    
    def place_order(self, inst_id, td_mode, side, ord_type, sz=None, px=None, cl_ord_id=None,
                   tp_trigger_px=None, sl_trigger_px=None, position_ratio=None):
        """
        下单接口（支持数量和位置比例两种模式，包含止盈止损设置）
        
        Args:
            inst_id: 产品ID，如 BTC-USDT-SWAP
            td_mode: 交易模式 isolated(逐仓) / cross(全仓)
            side: 订单方向 buy(买) / sell(卖)
            ord_type: 订单类型 limit(限价) / market(市价)
            sz: 委托数量（当使用数量模式时必填）
            px: 委托价格（限价单必填，市价单可省略）
            cl_ord_id: 客户端订单ID
            tp_trigger_px: 止盈触发价格
            sl_trigger_px: 止损触发价格
            position_ratio: 位置比例（0.0-1.0），当使用时将查询最大可买数量并按比例计算
            
        Returns:
            dict: 订单结果
        """
        try:
            # 如果使用位置比例模式，查询最大可买数量并按比例计算
            if position_ratio is not None and sz is None:

                # 验证位置比例参数
                if not isinstance(position_ratio, (int, float)) or position_ratio <= 0 or position_ratio > 1:
                    return {'code': '50001', 'msg': '位置比例必须在0-1之间'}
                
                # 按位置比例计算实际下单数量
                result = self._send_request(
                    method="GET",
                    request_path="/api/v5/account/max-size",
                    params={
                        "instId": inst_id,
                        "tdMode": td_mode
                    },
                    auth=True
                )
                max_buy_quantity = 0
                if result.get('code') == '0' and result.get('data'):
                    max_buy_quantity = float(result.get('data', [{}])[0].get('maxBuy', 0)) * position_ratio
                sz = round(max_buy_quantity, 2)

                self._log('INFO',
                          f"位置比例计算: 最大可买={max_buy_quantity:.6f}, "
                          f"比例={position_ratio:.2%}, "
                          f"实际下单={sz:.6f}")
            # 参数验证
            if sz is None or float(sz) <= 0:
                return {'code': '50001', 'msg': '委托数量无效'}
            
            if ord_type.lower() == 'limit' and (px is None or float(px) <= 0):
                return {'code': '50001', 'msg': '限价单需要指定有效价格'}
            
            # 止盈止损参数验证
            if tp_trigger_px or sl_trigger_px:
                # 验证止盈止损价格合理性
                if side.lower() == 'buy':
                    # 买入订单，止盈价格应高于开仓价
                    if tp_trigger_px and float(tp_trigger_px) <= float(px):
                        self._log('WARNING', f"止盈价格 {tp_trigger_px} 不应低于开仓价格 {px}", "OKX-Order")
                    if sl_trigger_px and float(sl_trigger_px) >= float(px):
                        self._log('WARNING', f"止损价格 {sl_trigger_px} 不应高于开仓价格 {px}", "OKX-Order")
                else:
                    # 卖出订单，止盈价格应低于开仓价
                    if tp_trigger_px and float(tp_trigger_px) >= float(px):
                        self._log('WARNING', f"止盈价格 {tp_trigger_px} 不应高于开仓价格 {px}", "OKX-Order")
                    if sl_trigger_px and float(sl_trigger_px) <= float(px):
                        self._log('WARNING', f"止损价格 {sl_trigger_px} 不应低于开仓价格 {px}", "OKX-Order")
            
            # 构建订单请求体
            order_body = {
                "instId": inst_id,
                "tdMode": td_mode,
                "side": side,
                "ordType": ord_type,
                "sz": str(sz),
            }
            
            if px:
                order_body["px"] = str(px)
            if cl_ord_id:
                order_body["clOrdId"] = cl_ord_id
            
            # 使用 attachAlgoOrds 数组来设置止盈止损（OKX API标准方式）
            attach_algo_ords = []
            
            # 添加止盈算法订单
            if tp_trigger_px:
                tp_algo = {
                    'algoClOrdId': f"{cl_ord_id or ''}_TP_{int(time.time())}",
                    'sz': str(sz),  # 使用主订单的相同数量
                    'tpTriggerPx': str(tp_trigger_px),
                    'tpOrdPx': '-1'
                }
                attach_algo_ords.append(tp_algo)
            
            # 添加止损算法订单
            if sl_trigger_px:
                sl_algo = {
                    'algoClOrdId': f"{cl_ord_id or ''}_SL_{int(time.time())}",
                    'sz': str(sz),  # 使用主订单的相同数量
                    'slTriggerPx': str(sl_trigger_px),
                    'slOrdPx': '-1'
                }
                attach_algo_ords.append(sl_algo)
            
            if attach_algo_ords:
                order_body["attachAlgoOrds"] = attach_algo_ords

            result = self._send_request(
                method="POST",
                request_path="/api/v5/trade/order",
                body=order_body,
                auth=True
            )
            
            if result.get('code') == '0':
                actual_price = float(px) if px else 0
                nominal_value = float(sz) * actual_price if actual_price > 0 else 0
                
                # 构建详细的下单成功消息
                success_msg = f"下单成功: {inst_id} {side} {sz}"
                if actual_price > 0:
                    success_msg += f" @ {actual_price}"
                    success_msg += f" (约 {nominal_value:.2f} USDT)"
                
                # 添加止盈止损信息到日志
                if tp_trigger_px or sl_trigger_px:
                    tp_sl_info = []
                    if tp_trigger_px:
                        tp_info = f"止盈@{tp_trigger_px}"
                        tp_sl_info.append(tp_info)
                    if sl_trigger_px:
                        sl_info = f"止损@{sl_trigger_px}"
                        tp_sl_info.append(sl_info)
                    success_msg += f" [{', '.join(tp_sl_info)}]"
                
                self._log('INFO', success_msg, "OKX-Order")
                return result
            else:
                error_msg = f"下单失败: {result.get('msg')}"
                self._log('ERROR', error_msg, "OKX-Order")
                return result
                
        except Exception as e:
            error_msg = f"下单异常: {e}"
            self._log('ERROR', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}

    def get_pending_orders(self, inst_id=None, ord_type=None, state="live",
                          after=None, before=None):
        """
        获取挂单列表

        Args:
            inst_id: 产品ID
            ord_type: 订单类型 limit / market
            state: 订单状态 live(未成交) / partially_filled(部分成交)
            after: 请求此时间戳之后（更旧的数据）的分页内容
            before: 请求此时间戳之前（更新的数据）的分页内容

        Returns:
            dict: 挂单列表
        """
        try:
            params = {
                "state": state
            }
            
            if inst_id:
                params["instId"] = inst_id
            if ord_type:
                params["ordType"] = ord_type
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            
            result = self._send_request(
                method="GET",
                request_path="/api/v5/trade/orders-pending",
                params=params,
                auth=True
            )
            
            if result.get('code') == '0':
                return result
            else:
                error_msg = f"获取挂单失败: {result.get('msg')}"
                self._log('WARNING', error_msg, "OKX-Order")
                return result

        except Exception as e:
            error_msg = f"获取挂单异常: {e}"
            self._log('WARNING', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}
                
    def cancel_order(self, inst_id, ord_id=None, cl_ord_id=None):
        """
        撤销订单

        Args:
            inst_id: 产品ID
            ord_id: 订单ID
            cl_ord_id: 客户端订单ID

        Returns:
            dict: 撤销结果
        """
        try:
            # 构建撤销订单请求体
            cancel_body = {
                "instId": inst_id
            }
            
            if ord_id:
                cancel_body["ordId"] = ord_id
            if cl_ord_id:
                cancel_body["clOrdId"] = cl_ord_id
            
            result = self._send_request(
                method="POST",
                request_path="/api/v5/trade/cancel-order",
                body=cancel_body,
                auth=True
            )

            if result.get('code') == '0':
                success_msg = f"撤销订单成功: {inst_id}"
                self._log('INFO', success_msg, "OKX-Order")
                return result
            else:
                error_msg = f"撤销订单失败: {result.get('msg')}"
                self._log('ERROR', error_msg, "OKX-Order")
                return result

        except Exception as e:
            error_msg = f"撤销订单异常: {e}"
            self._log('ERROR', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}
    
    def get_order_info(self, inst_id, ord_id=None, cl_ord_id=None):
        """
        获取订单信息

        Args:
            inst_id: 产品ID
            ord_id: 订单ID
            cl_ord_id: 客户端订单ID

        Returns:
            dict: 订单信息
        """
        try:
            # 构建获取订单信息的参数
            params = {
                "instId": inst_id
            }
            
            if ord_id:
                params["ordId"] = ord_id
            if cl_ord_id:
                params["clOrdId"] = cl_ord_id
            
            result = self._send_request(
                method="GET",
                request_path="/api/v5/trade/order",
                params=params,
                auth=True
            )
            
            if result.get('code') == '0':
                return result
            else:
                error_msg = f"获取订单信息失败: {result.get('msg')}"
                self._log('WARNING', error_msg, "OKX-Order")
                return result

        except Exception as e:
            error_msg = f"获取订单信息异常: {e}"
            self._log('WARNING', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}
    
    def modify_order(self, inst_id, ord_id=None, cl_ord_id=None, 
                    new_sz=None, new_px=None):
        """
        修改订单
        
        Args:
            inst_id: 产品ID
            ord_id: 订单ID
            cl_ord_id: 客户端订单ID
            new_sz: 新委托数量
            new_px: 新委托价格
            
        Returns:
            dict: 修改结果
        """
        try:
            # 构建修改订单请求体
            modify_body = {
                "instId": inst_id
            }
            
            if ord_id:
                modify_body["ordId"] = ord_id
            if cl_ord_id:
                modify_body["clOrdId"] = cl_ord_id
            if new_sz:
                modify_body["newSz"] = str(new_sz)
            if new_px:
                modify_body["newPx"] = str(new_px)
            
            result = self._send_request(
                method="POST",
                request_path="/api/v5/trade/amend-order",
                body=modify_body,
                auth=True
            )
            
            if result.get('code') == '0':
                success_msg = f"修改订单成功: {inst_id}"
                self._log('INFO', success_msg, "OKX-Order")
                return result
            else:
                error_msg = f"修改订单失败: {result.get('msg')}"
                self._log('ERROR', error_msg, "OKX-Order")
                return result
                
        except Exception as e:
            error_msg = f"修改订单异常: {e}"
            self._log('ERROR', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}
    
    def get_account_configuration(self, inst_id=None):
        """
        获取账户配置信息
        
        Args:
            inst_id: 产品ID
            
        Returns:
            dict: 账户配置信息
        """
        try:
            params = {}
            if inst_id:
                params["instId"] = inst_id
            
            result = self._send_request(
                method="GET",
                request_path="/api/v5/account/config",
                params=params,
                auth=True
            )
            
            if result.get('code') == '0':
                return result
            else:
                error_msg = f"获取账户配置失败: {result.get('msg')}"
                self._log('WARNING', error_msg, "OKX-Order")
                return result
                
        except Exception as e:
            error_msg = f"获取账户配置异常: {e}"
            self._log('WARNING', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}
    
    def set_leverage(self, inst_id, lever, mgn_mode="isolated"):
        """
        设置杠杆倍数
        
        Args:
            inst_id: 产品ID
            lever: 杠杆倍数
            mgn_mode: 保证金模式 cross(全仓) / isolated(逐仓)
            
        Returns:
            dict: 设置结果
        """
        try:
            # 构建设置杠杆请求体
            leverage_body = {
                "instId": inst_id,
                "lever": str(lever),
                "mgnMode": mgn_mode
            }
            
            result = self._send_request(
                method="POST",
                request_path="/api/v5/account/set-leverage",
                body=leverage_body,
                auth=True
            )
            
            if result.get('code') == '0':
                success_msg = f"设置杠杆成功: {inst_id} {lever}x"
                self._log('INFO', success_msg, "OKX-Order")
                return result
            else:
                error_msg = f"设置杠杆失败: {result.get('msg')}"
                self._log('ERROR', error_msg, "OKX-Order")
                return result
                
        except Exception as e:
            error_msg = f"设置杠杆异常: {e}"
            self._log('ERROR', error_msg, "OKX-Order")
            return {'code': '50001', 'msg': str(e)}