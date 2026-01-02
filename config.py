"""
配置管理模块
负责从 .env 文件读取环境变量，提供统一的配置访问接口
"""
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件
load_dotenv(os.path.join(BASE_DIR, '.env'))

logger = logging.getLogger(__name__)


class Config:
    """配置类，封装所有环境变量"""
    
    def __init__(self):
        """初始化配置，从环境变量中读取所有必要配置项"""
        self._app_id = os.getenv('APPID')
        self._app_secret = os.getenv('AppSecret')
        self._account_id = os.getenv('ACCOUNT_ID')
        
        # 数据库配置
        self._db_url = os.getenv('DB_URL')
        
        # API 配置
        self._api_base_url = os.getenv('API_BASE_URL', 'https://open.douyin.com')
        
        # 任务配置
        self._task_id = os.getenv('TASK_ID', 'douyin_order_sync')
        self._sync_interval = int(os.getenv('SYNC_INTERVAL', '3600'))
        
        # 订单查询参数配置
        # 时间范围配置（天）
        self._sync_days = int(os.getenv('SYNC_DAYS', '1'))
        
        # 自定义时间范围（可选）
        # 方式1：使用自然日期格式（推荐）
        # 格式：YYYY-MM-DD HH:MM:SS，例如：2024-01-01 00:00:00
        self._start_date_str = os.getenv('START_DATE')
        self._end_date_str = os.getenv('END_DATE')
        
        # 方式2：使用时间戳（向后兼容）
        # 如果配置了 START_TIME，则使用它作为开始时间（秒时间戳）
        # 如果配置了 END_TIME，则使用它作为结束时间（秒时间戳）
        self._start_time_str = os.getenv('START_TIME')
        self._end_time_str = os.getenv('END_TIME')
        
        # 订单状态筛选（可选）
        self._order_status = os.getenv('ORDER_STATUS')
        
        # 每页数量
        self._page_size = int(os.getenv('PAGE_SIZE', '50'))
        
        # 是否查询配送信息
        self._get_secret_number = os.getenv('GET_SECRET_NUMBER', 'false').lower() == 'true'
        
        # 是否使用创单时间而非修改时间
        self._use_create_time = os.getenv('USE_CREATE_TIME', 'false').lower() == 'true'
    
    @property
    def app_id(self) -> str:
        """
        获取抖音应用 App ID
        
        Returns:
            str: 抖音应用的 App ID
        """
        return self._app_id
    
    @property
    def app_secret(self) -> str:
        """
        获取抖音应用 App Secret
        
        Returns:
            str: 抖音应用的 App Secret
        """
        return self._app_secret
    
    @property
    def account_id(self) -> str:
        """
        获取抖音账号 ID
        
        Returns:
            str: 抖音账号 ID
        """
        return self._account_id
    
    @property
    def db_url(self) -> str:
        """
        获取数据库连接 URL
        
        Returns:
            str: 数据库连接字符串
        """
        # 将 postgresql:// 转换为 postgresql+psycopg2:// 以使用 psycopg2 驱动
        if self._db_url and self._db_url.startswith('postgresql://'):
            return self._db_url.replace('postgresql://', 'postgresql+psycopg2://')
        return self._db_url
    
    @property
    def api_base_url(self) -> str:
        """
        获取抖音 API 基础 URL
        
        Returns:
            str: API 基础 URL
        """
        return self._api_base_url
    
    @property
    def task_id(self) -> str:
        """
        获取任务 ID
        
        Returns:
            str: 任务 ID
        """
        return self._task_id
    
    @property
    def sync_interval(self) -> int:
        """
        获取同步间隔（秒）
        
        Returns:
            int: 同步间隔秒数
        """
        return self._sync_interval
    
    @property
    def sync_days(self) -> int:
        """
        获取同步时间范围（天）
        
        Returns:
            int: 同步天数
        """
        return self._sync_days
    
    @property
    def order_status(self) -> str:
        """
        获取订单状态筛选条件
        
        Returns:
            str: 订单状态，未配置则返回 None
        """
        return self._order_status
    
    @property
    def page_size(self) -> int:
        """
        获取每页订单数量
        
        Returns:
            int: 每页数量（1-100）
        """
        return max(1, min(100, self._page_size))
    
    @property
    def get_secret_number(self) -> bool:
        """
        是否查询配送信息
        
        Returns:
            bool: 是否查询配送信息
        """
        return self._get_secret_number
    
    @property
    def use_create_time(self) -> bool:
        """
        是否使用创单时间而非修改时间
        
        Returns:
            bool: True 使用创单时间，False 使用修改时间
        """
        return self._use_create_time
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串，支持多种格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            datetime: 解析后的 datetime 对象
            
        Raises:
            ValueError: 日期格式错误
        """
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d %H:%M:%S',  # 2024-01-01 00:00:00
            '%Y-%m-%d',           # 2024-01-01
            '%Y/%m/%d %H:%M:%S',  # 2024/01/01 00:00:00
            '%Y/%m/%d',           # 2024/01/01
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # 所有格式都失败
        raise ValueError(f"无法解析日期: {date_str}，支持的格式: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS")
    
    @property
    def start_time(self) -> int:
        """
        获取开始时间戳（秒）
        
        优先使用日期格式，其次使用时间戳
        
        Returns:
            int: 开始时间戳，未配置则返回 None
        """
        # 优先使用日期格式
        if self._start_date_str:
            try:
                # 解析日期字符串：支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
                dt = self._parse_date(self._start_date_str)
                
                # 如果只有日期没有时间，默认使用 00:00:00
                if ' ' not in self._start_date_str:
                    dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                return int(dt.timestamp())
            except ValueError as e:
                logger.error(f"START_DATE 格式错误: {self._start_date_str}, {str(e)}")
                raise
        
        # 向后兼容：使用时间戳格式
        if self._start_time_str:
            return int(self._start_time_str)
        
        return None
    
    @property
    def end_time(self) -> int:
        """
        获取结束时间戳（秒）
        
        优先使用日期格式，其次使用时间戳
        
        Returns:
            int: 结束时间戳，未配置则返回 None
        """
        # 优先使用日期格式
        if self._end_date_str:
            try:
                # 解析日期字符串：支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
                dt = self._parse_date(self._end_date_str)
                
                # 如果只有日期没有时间，默认使用 23:59:59
                if ' ' not in self._end_date_str:
                    dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                return int(dt.timestamp())
            except ValueError as e:
                logger.error(f"END_DATE 格式错误: {self._end_date_str}, {str(e)}")
                raise
        
        # 向后兼容：使用时间戳格式
        if self._end_time_str:
            return int(self._end_time_str)
        
        return None
    
    def validate(self) -> bool:
        """
        验证所有必要的配置项是否完整
        
        Returns:
            bool: 如果所有必要配置项都存在且有效，返回 True；否则返回 False
        """
        required_fields = [
            self._app_id,
            self._app_secret,
            self._db_url
        ]
        return all(field is not None for field in required_fields)


# 全局配置实例
config = Config()
