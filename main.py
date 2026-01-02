"""
主程序入口
负责启动死循环、捕捉 Docker 退出信号、调用 TaskManager 和 API
"""
import signal
import sys
import time
import logging
from datetime import datetime, timedelta
from config import config
from database import DatabaseManager
from task_manager import TaskManager
from douyin_api import DouyinAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DouyinOrderSync:
    """抖音订单同步主程序"""
    
    def __init__(self):
        """初始化所有组件"""
        # 验证配置
        if not config.validate():
            logger.error("配置验证失败，请检查 .env 文件")
            sys.exit(1)
        
        # 初始化数据库管理器（传入app_secret用于解密手机号）
        self.db_manager = DatabaseManager(config.db_url, config.app_secret)
        
        # 通用迁移：自动检查并添加缺失字段
        self.db_manager.migrate_all_models()
        
        # 创建数据表
        self.db_manager.create_tables()
        logger.info("数据库表创建完成")
        
        # 初始化任务管理器
        self.task_manager = TaskManager(self.db_manager, config.task_id)
        
        # 初始化 API 客户端
        self.api = DouyinAPI(
            app_id=config.app_id,
            app_secret=config.app_secret,
            base_url=config.api_base_url,
            account_id=config.account_id
        )
        
        # 运行标志
        self._running = False
        
        # 设置信号处理器
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """
        设置信号处理器
        
        注册 SIGTERM 和 SIGINT 信号，支持 Docker 的优雅退出
        """
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        logger.info("信号处理器已设置")
    
    def signal_handler(self, signum, frame):
        """
        信号处理函数
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"收到信号 {signal_name} ({signum})，准备优雅退出...")
        self._running = False
    
    def run_once(self):
        """
        执行一次订单同步任务
        
        Returns:
            int: 同步的订单数量
        """
        try:
            # 设置任务状态为 RUNNING
            self.task_manager.set_task_status('RUNNING')
            
            # 计算同步时间范围
            # 优先使用自定义时间范围（START_TIME 和 END_TIME），否则使用 SYNC_DAYS 计算
            if config.start_time is not None and config.end_time is not None:
                # 使用自定义时间范围
                start_timestamp = config.start_time
                end_timestamp = config.end_time
                logger.info("使用自定义时间范围配置")
            else:
                # 使用天数计算时间范围
                end_timestamp = int(datetime.now().timestamp())
                start_timestamp = end_timestamp - (config.sync_days * 86400)  # 每天 86400 秒
                logger.info(f"使用天数计算时间范围: 最近 {config.sync_days} 天")
            
            # 转换为 datetime 对象用于日志显示
            end_time = datetime.fromtimestamp(end_timestamp)
            start_time = datetime.fromtimestamp(start_timestamp)
            
            logger.info(f"开始同步订单数据: {start_time} 到 {end_time}")
            logger.info(f"时间戳范围: {start_timestamp} 到 {end_timestamp} (秒)")
            
            # 定义停止检查回调函数
            def check_stop():
                return not self._running
            
            # 拉取订单数据（使用配置参数，传递停止回调）
            orders = self.api.fetch_all_orders_by_day(
                start_time=start_time,
                end_time=end_time,
                page_size=config.page_size,
                order_status=config.order_status,
                get_secret_number=config.get_secret_number,
                use_create_time=config.use_create_time,
                check_stop_callback=check_stop
            )
            
            # 记录配置信息
            logger.info(f"同步配置: 天数={config.sync_days}, 每页数量={config.page_size}, "
                       f"订单状态={config.order_status or '全部'}, "
                       f"查询配送={config.get_secret_number}, "
                       f"使用创单时间={config.use_create_time}")
            
            # 转换为 list（因为 orders 可能是 generator）
            orders_list = list(orders) if not isinstance(orders, list) else orders
            
            if not orders_list:
                logger.info("没有新的订单数据")
                return 0
            
            # 保存订单到数据库
            saved_count = self.db_manager.save_orders(orders_list)
            
            # 更新任务状态
            self.task_manager.set_task_status(
                'RUNNING',
                last_sync_time=end_time.isoformat()
            )
            
            logger.info(f"同步完成: 拉取 {len(orders_list)} 条订单，保存 {saved_count} 条")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"同步失败: {e}", exc_info=True)
            
            # 更新任务状态为 ERROR
            self.task_manager.set_task_status('ERROR', error_message=str(e))
            
            raise
    
    def smart_wait(self, seconds: int):
        """
        智能等待：支持中途被信号中断
        
        每秒醒来检查一次退出信号和数据库指令
        
        Args:
            seconds: 等待的总秒数
        """
        logger.info(f"进入待机模式，等待 {seconds} 秒...")
        
        step = 1  # 每次睡 1 秒
        for _ in range(0, seconds, step):
            # 【关键】每秒醒来检查一次：是否收到退出信号？
            if not self._running:
                logger.info("检测到退出信号，终止等待，准备关闭...")
                return
            
            # 检查数据库指令（比如后台发了 STOP）
            if self.task_manager.should_stop():
                logger.info("检测到停止指令，终止等待...")
                return
            
            time.sleep(step)
        
        logger.info("等待结束，准备进行下一轮同步")
    
    def run(self):
        """
        主循环
        
        采用 while True 循环运行，支持 Docker 驻守模式
        定期检查控制指令并执行同步任务
        
        逻辑：检查指令 -> (暂停/继续) -> 拉取数据 -> 存入数据库 -> 休息 -> 循环
        """
        logger.info("启动抖音订单同步程序")
        self._running = True
        
        try:
            while self._running:
                # 1. 检查控制指令
                if self.task_manager.should_stop():
                    logger.info("收到停止指令，暂停同步")
                    self.task_manager.set_task_status('STOPPED')
                    self.smart_wait(10)  # 每 10 秒检查一次指令
                    continue
                
                logger.info("开始新一轮同步")
                
                # 2. 更新心跳
                self.task_manager.update_heartbeat()
                
                # 3. 拉取数据并存入数据库
                try:
                    self.run_once()
                except Exception as e:
                    logger.error(f"同步过程出错: {e}", exc_info=True)
                    # 出错后短时间等待
                    self.smart_wait(60)
                    continue
                
                # 4. 休息
                wait_time = config.sync_interval
                self.smart_wait(wait_time)
                        
        except KeyboardInterrupt:
            logger.info("接收到键盘中断")
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """
        停止程序，执行清理工作
        
        更新任务状态为 STOPPED，关闭数据库连接等
        """
        logger.info("停止程序，执行清理工作...")
        
        try:
            # 更新任务状态为 STOPPED
            self.task_manager.set_task_status('STOPPED')
            logger.info("任务状态已更新为 STOPPED")
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
        
        logger.info("程序已停止")


def main():
    """程序入口函数"""
    try:
        sync = DouyinOrderSync()
        sync.run()
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
