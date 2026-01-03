#!/usr/bin/env python3
"""
验证视图创建是否成功
"""
import psycopg2
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv('.env')


def connect_database():
    """连接数据库"""
    db_url = os.getenv('DB_URL')
    
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
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    return cursor, conn


def verify_view(cursor, view_name: str):
    """验证视图"""
    print(f"\n{'=' * 60}")
    print(f"验证视图: {view_name}")
    print('=' * 60)
    
    try:
        # 查询视图总数
        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]
        print(f"✅ 记录总数: {count}")
        
        # 查询视图前5条记录
        cursor.execute(f"SELECT * FROM {view_name} ORDER BY pay_time DESC LIMIT 5")
        rows = cursor.fetchall()
        
        # 获取列名
        column_names = [desc[0] for desc in cursor.description]
        
        print(f"\n📊 最新5条记录:")
        print("-" * 120)
        print(f"{'序号':<4} | {column_names[0]:<25} | {column_names[1]:<15} | {column_names[2]:<20}")
        print("-" * 120)
        
        for i, row in enumerate(rows, 1):
            order_id = row[0]
            count = row[1]
            pay_time = str(row[2])
            print(f"{i:<4} | {order_id:<25} | {str(count):<15} | {pay_time:<20}")
        
        print(f"\n✅ 视图 {view_name} 验证成功！")
        return True
        
    except Exception as e:
        print(f"❌ 视图 {view_name} 验证失败: {e}")
        return False



def main():
    """主函数"""
    cursor, conn = connect_database()
    
    try:
        print("\n" + "=" * 60)
        print("开始验证视图")
        print("=" * 60)
        
        # 验证valid_orders视图
        success = verify_view(cursor, 'valid_orders')
        
        # 总结
        print("\n" + "=" * 60)
        if success:
            print("🎉 视图验证成功！")
        else:
            print("❌ 视图验证失败")
        print("=" * 60)
        
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
