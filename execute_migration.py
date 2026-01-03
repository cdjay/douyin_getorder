#!/usr/bin/env python3
"""
执行orders_excel表迁移脚本
"""
import logging
import psycopg2
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv('.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_sql_file(file_path: str) -> str:
    """
    读取SQL文件内容
    
    Args:
        file_path: SQL文件路径
        
    Returns:
        str: SQL内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取SQL文件失败 {file_path}: {e}")
        raise


def execute_sql(db_url: str, sql: str, description: str) -> bool:
    """
    执行SQL语句
    
    Args:
        db_url: 数据库连接URL
        sql: SQL语句
        description: 操作描述
        
    Returns:
        bool: 执行是否成功
    """
    try:
        # 解析数据库连接参数
        # 格式：postgresql://username:password@host:port/database
        if db_url.startswith('postgresql://'):
            # 移除 postgresql:// 前缀
            db_url = db_url.replace('postgresql://', '')
        
        # 解析连接参数
        parts = db_url.split('@')
        if len(parts) != 2:
            raise ValueError(f"数据库URL格式错误: {db_url}")
        
        user_password, host_db = parts
        user, password = user_password.split(':', 1)
        
        # 解析主机和端口
        host_port, database = host_db.split('/', 1)
        
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 5432  # 默认端口
        
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
        
        # 提交事务
        conn.commit()
        logger.info(f"✅ 执行成功: {description}")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 执行失败: {description}")
        logger.error(f"错误信息: {e}")
        return False


def main():
    """主函数"""
    # 读取数据库URL
    db_url = os.getenv('DB_URL')
    
    if not db_url:
        logger.error("❌ 数据库URL未配置，请检查.env文件中的DB_URL")
        return
    
    logger.info("=" * 60)
    logger.info("开始orders_excel表迁移")
    logger.info("=" * 60)
    
    # 读取迁移SQL
    sql_migration = read_sql_file('migrate_orders_excel.sql')
    success = execute_sql(
        db_url,
        sql_migration,
        "orders_excel表迁移：清空数据并添加唯一约束"
    )
    
    # 总结
    logger.info("=" * 60)
    if success:
        logger.info("🎉 迁移完成！现在可以重新导入Excel数据了。")
    else:
        logger.error("❌ 迁移失败！")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
