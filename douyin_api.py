"""
抖音 API 模块
包含解密、鉴权、分页拉取订单等核心 API 逻辑
"""
import requests
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class DouyinAPI:
    """抖音 API 客户端，处理所有与抖音平台的交互"""
    
    def __init__(self, app_id: str, app_secret: str, base_url: str, account_id: str = None):
        """
        初始化抖音 API 客户端
        
        Args:
            app_id: 抖音应用 App ID
            app_secret: 抖音应用 App Secret
            base_url: API 基础 URL
            account_id: 抖音账号 ID（可选）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url
        self.account_id = account_id
        self._access_token = None
        self._token_expire_time = None
    
    def decrypt(self, encrypted_data: str, iv: str, key: str) -> str:
        """
        解密数据（AES-GCM 算法）
        
        Args:
            encrypted_data: 加密的数据（Base64 编码）
            iv: 初始化向量（Base64 编码）
            key: 解密密钥（Base64 编码）
            
        Returns:
            str: 解密后的数据（JSON 字符串）
        """
        try:
            # Base64 解码
            encrypted_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)
            key_bytes = base64.b64decode(key)
            
            # AES-GCM 解密
            aesgcm = AESGCM(key_bytes)
            decrypted_bytes = aesgcm.decrypt(iv_bytes, encrypted_bytes, None)
            
            # 转换为字符串
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
    def get_token(self) -> str:
        """
        获取访问令牌（Access Token）
        
        Returns:
            str: 访问令牌
        """
        # 检查 token 是否过期（提前 5 分钟刷新）
        if self._access_token and self._token_expire_time:
            if datetime.now() < self._token_expire_time - timedelta(minutes=5):
                return self._access_token
        
        # 获取新 token
        # 【关键点1】URL 必须是完整的抖音 OAuth 地址
        url = "https://open.douyin.com/oauth/client_token/"
        
        # 【关键点2】Header 必须指定 json
        headers = {"Content-Type": "application/json"}
        
        # 【关键点3】参数名必须是 client_key 和 client_secret
        payload = {
            "client_key": self.app_id,      # 注意：这里对应抖音文档的 client_key
            "client_secret": self.app_secret,
            "grant_type": "client_credential"
        }
        
        logger.debug(f"发送 Token 请求到: {url}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 检查响应状态
        if data.get('code', 0) != 0:
            error_msg = data.get('message', '未知错误')
            raise ValueError(f"获取 token 失败: {error_msg}")
        
        if 'data' not in data or 'access_token' not in data['data']:
            raise ValueError(f"获取 token 失败: {data}")
        
        self._access_token = data['data']['access_token']
        expires_in = data['data'].get('expires_in', 7200)
        self._token_expire_time = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("成功获取访问令牌")
        return self._access_token
    
    def fetch_orders(self, start_time: int, end_time: int, 
                    cursor: str = "0", page_size: int = 20,
                    order_status: int = None, get_secret_number: bool = False,
                    use_create_time: bool = False) -> Dict[str, Any]:
        """
        拉取订单数据（分页）
        
        Args:
            start_time: 开始时间戳（秒）
            end_time: 结束时间戳（秒）
            cursor: 游标字符串，首页传 "0"
            page_size: 每页数量，范围 1-100，默认 20
            order_status: 订单状态筛选（可选）
            get_secret_number: 是否查询配送信息（可选，默认 False）
            use_create_time: 是否使用创单时间而非修改时间（默认 False）
            
        Returns:
            Dict[str, Any]: 包含订单列表、下一页游标和是否有更多数据的响应数据
        """
        # 验证 account_id
        if not self.account_id:
            raise ValueError("account_id 是必填参数，请在 .env 中配置 ACCOUNT_ID")
        
        # 获取访问令牌
        access_token = self.get_token()
        
        # 构建请求参数
        url = f"{self.base_url}/goodlife/v1/trade/order/query/"
        params = {
            'access_token': access_token,
            'account_id': self.account_id,
            'cursor': cursor,          
            'page_size': page_size
        }
        
        # 根据配置选择使用创单时间还是修改时间
        if use_create_time:
            params['create_order_start_time'] = start_time
            params['create_order_end_time'] = end_time
        else:
            params['update_order_start_time'] = start_time
            params['update_order_end_time'] = end_time
        
        # 可选参数
        if order_status is not None:
            params['order_status'] = order_status
        
        if get_secret_number:
            params['get_secret_number'] = 'true' if get_secret_number else 'false'
        
        logger.info(f"拉取订单: start={start_time}, end={end_time}, cursor={cursor}")
        
        response = requests.get(url, params=params, timeout=30)
        
        # === 调试日志 (保留以便出错时查看) ===
        # logger.debug(f"请求URL: {response.url}")
        
        response.raise_for_status()
        data = response.json()
        
        # 检查响应状态
        if data.get('code', 0) != 0:
            error_msg = data.get('message', '未知错误')
            raise ValueError(f"API 错误: {error_msg}")
        
        # 提取数据
        result = {
            'orders': [],
            'has_more': False,
            'next_cursor': cursor, # 默认保持当前cursor
            'total_count': 0
        }
        
        if 'data' in data and data['data']:
            orders_data = data['data']
            result['orders'] = orders_data.get('orders', [])
            result['total_count'] = orders_data.get('total_count', 0)
            
            # === 【核心修正】解析 search_after ===
            # CursorValue 藏在 search_after 字段里，而不是直接在 data 里
            search_after = orders_data.get('search_after', {})
            cursor_value_list = search_after.get('CursorValue', [])
            
            # 判断是否有更多数据：只要拿到了新的 CursorValue，就认为还有数据
            # 注意：某些情况下 orders 为空但有 cursor，也需要继续翻页
            if cursor_value_list:
                # 将数组拼接成字符串: ["123", "456"] -> "123,456"
                next_cursor = ','.join(str(x) for x in cursor_value_list)
                result['next_cursor'] = next_cursor
                result['has_more'] = True 
            else:
                result['has_more'] = False
        
        logger.info(f"拉取结果: 本页{len(result['orders'])}条, has_more={result['has_more']}")
        return result

    def fetch_all_orders_by_day(self, start_time: datetime, end_time: datetime,
                               page_size: int = 50, order_status: int = None,
                               get_secret_number: bool = False, use_create_time: bool = False,
                               check_stop_callback=None):
        """
        [生成器版] 按天切分拉取订单
        
        功能：
        每次拉取完"一整天"的数据，就通过 yield 交给外部处理。
        内存占用极低，哪怕拉取 10 年的数据也不会崩。
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            page_size: 每页数量（默认 50）
            order_status: 订单状态筛选（可选）
            get_secret_number: 是否查询配送信息（可选）
            use_create_time: 是否使用创单时间而非修改时间（可选）
            check_stop_callback: 检查是否应该停止的回调函数（可选）
                               如果返回 True，则停止拉取
        """
        current_day = start_time
        
        while current_day <= end_time:
            # 检查是否应该停止
            if check_stop_callback and check_stop_callback():
                logger.info("检测到停止信号，终止订单拉取")
                break
            
            # 计算当天的结束时间
            next_day = current_day + timedelta(days=1)
            day_end = min(next_day, end_time)
            
            start_ts = int(current_day.timestamp())
            end_ts = int(day_end.timestamp())
            
            logger.info(f"=== [生成器] 开始处理: {current_day.date()} ===")
            
            # 当天的数据容器
            day_orders = [] 
            
            # --- 内层分页循环 ---
            cursor = "0"
            page_count = 0
            max_pages = 200
            
            while page_count < max_pages:
                # 检查是否应该停止
                if check_stop_callback and check_stop_callback():
                    logger.info("检测到停止信号，终止分页拉取")
                    break
                
                page_count += 1
                try:
                    result = self.fetch_orders(
                        start_ts, end_ts, 
                        cursor=cursor, 
                        page_size=page_size,
                        order_status=order_status,
                        get_secret_number=get_secret_number,
                        use_create_time=use_create_time
                    )
                    
                    orders = result.get('orders', [])
                    # 收集这一天的数据
                    day_orders.extend(orders)
                    
                    has_more = result.get('has_more', False)
                    next_cursor = result.get('next_cursor')
                    
                    if not has_more or next_cursor == cursor:
                        break
                    cursor = next_cursor
                    
                except Exception as e:
                    logger.error(f"拉取分页失败: {e}")
                    break
            # ---------------------------
            
            logger.info(f"日期 {current_day.date()} 完成，共 {len(day_orders)} 条，准备存库...")
            
            # 【核心修改】不要存 all_orders，直接把当天的货"交"出去
            if day_orders:
                yield day_orders  # <--- 这里暂停函数，把数据扔给 main.py，等 main.py 存完库再回来
            
            current_day = next_day
    
    def _make_request(self, url: str, params: Dict[str, Any], 
                     headers: Dict[str, str]) -> Dict[str, Any]:
        """
        发起 HTTP 请求的内部方法
        
        Args:
            url: 请求 URL
            params: 请求参数
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        response = requests.get(url, params=params, headers=headers, timeout=30)
        logger.debug(f"请求URL: {response.url}")
        response.raise_for_status()
        return response.json()
