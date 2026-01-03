#!/usr/bin/env python3
"""
执行删除order_details_aggregated视图
"""
import psycopg2
from dotenv import load_dotenv
import os
import logging

# 加载环境变量
load_dotenv('.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def execute_sql_file(db_url: str, file_path: str, description: str) -> bool:
    """
    执行SQL文件
    
    Args:
        db_url: 数据库连接URL
        file_path: SQL文件路径
        description: 操作描述
        
    Returns:
        bool: 执行是否成功
    """
    try:
        # 读取SQL文件
        with open(file_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # 解析数据库连接参数
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', '')
        
        parts = db_url.split('@')
        user_password, host_db = parts
        user, password = user_password.split(':', 1)
        
        host_port, database = host_db.split('/', 1)
        
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 5432
        
        # 连接数据库
        logger.info(f"连接数据库: {host}:{port}/{database}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 执行SQL
        logger.info(f"执行SQL: {description}")
        cursor.execute(sql)
        
        # 获取结果
        if cursor.description:
            results = cursor.fetchall()
            for row in results:
                logger.info(f"  {row}")
        
        conn.commit()
        logger.info(f"✅ 执行成功: {description}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 执行失败: {description}")
        logger.error(f"错误信息: {e}")
        return False


def main():
    """主函数"""
    db_url = os.getenv('DB_URL')
    
    if not db_url:
        logger.error("❌ 数据库URL未配置，请检查.env文件中的DB_URL")
        return
    
    logger.info("=" * 60)
    logger.info("删除order_details_aggregated视图")
    logger.info("=" * 60)
    
    success = execute_sql_file(
        db_url,
        'drop_aggregated_view.sql',
        "删除order_details_aggregated视图"
    )
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 视图删除成功！")
    else:
        logger.error("❌ 视图删除失败！")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
