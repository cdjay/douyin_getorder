"""
Excel数据导入独立程序
监控data文件夹中的Excel文件并导入到数据库
"""
import os
import time
import signal
import sys
import logging
from datetime import datetime
from config import config
from database import DatabaseManager
from excel_importer import ExcelImporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ExcelImportLoop:
    """Excel导入循环程序"""
    
    def __init__(self):
        """初始化组件"""
        # 验证配置
        if not config.validate():
            logger.error("配置验证失败，请检查 .env 文件")
            sys.exit(1)
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(config.db_url, config.app_secret)
        
        # 通用迁移：自动检查并添加缺失字段
        self.db_manager.migrate_all_models()
        
        # 创建数据表
        self.db_manager.create_tables()
        logger.info("数据库表创建完成")
        
        # 初始化Excel导入器
        self.excel_importer = ExcelImporter(self.db_manager)
        
        # 运行标志
        self._running = False
        
        # 设置信号处理器
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        logger.info("信号处理器已设置")
    
    def signal_handler(self, signum, frame):
        """信号处理函数"""
        signal_name = signal.Signals(signum).name
        logger.info(f"收到信号 {signal_name} ({signum})，准备优雅退出...")
        self._running = False
    
    def run_once(self):
        """
        执行一次Excel扫描和导入
        
        Returns:
            int: 导入的记录数
        """
        try:
            # 扫描data文件夹
            data_dir = 'data'
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.info(f"创建data目录: {data_dir}")
            
            # 导入Excel文件
            imported_count = self.excel_importer.scan_and_import(data_dir)
            
            return imported_count
            
        except Exception as e:
            logger.error(f"导入失败: {e}", exc_info=True)
            return 0
    
    def smart_wait(self, seconds: int):
        """
        智能等待：支持中途被信号中断
        
        Args:
            seconds: 等待的总秒数
        """
        logger.info(f"进入待机模式，等待 {seconds} 秒...")
        
        step = 1  # 每次睡 1 秒
        for _ in range(0, seconds, step):
            # 每秒醒来检查一次退出信号
            if not self._running:
                logger.info("检测到退出信号，终止等待，准备关闭...")
                return
            
            time.sleep(step)
        
        logger.info("等待结束，准备进行下一轮导入")
    
    def run(self):
        """
        主循环
        
        监控data文件夹，定期扫描并导入Excel文件
        """
        logger.info("启动Excel导入程序")
        self._running = True
        
        try:
            while self._running:
                logger.info("开始新一轮扫描")
                
                # 扫描并导入Excel文件
                try:
                    imported_count = self.run_once()
                    if imported_count > 0:
                        logger.info(f"✅ 导入完成: {imported_count} 条记录")
                    else:
                        logger.info("没有新的Excel文件")
                except Exception as e:
                    logger.error(f"扫描过程出错: {e}", exc_info=True)
                
                # 休息10秒（快速扫描）
                wait_time = 10
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
        """
        logger.info("停止程序，执行清理工作...")
        logger.info("程序已停止")


def main():
    """程序入口函数"""
    try:
        importer = ExcelImportLoop()
        importer.run()
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
