"""
数据库模块
负责数据库连接初始化、Order 模型定义、以及订单数据的 Upsert 逻辑
"""
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, update, insert, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert as pg_insert, JSONB
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import logging
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

Base = declarative_base()


class Order(Base):
    """订单模型，使用 Iceberg Model 模式存储"""
    
    __tablename__ = 'orders'
    
    # 主键和唯一标识
    order_id = Column(String(64), primary_key=True, comment='订单ID')
    
    # 提取的关键字段，用于搜索和报表
    order_status = Column(String(32), index=True, comment='订单状态')
    sku_id = Column(String(64), comment='商品SKU ID')
    sku_name = Column(String(255), comment='商品名称（交易快照）')
    pay_amount = Column(Float, comment='支付金额')
    count = Column(Integer, default=1, comment='订单数量')
    pay_time = Column(DateTime, comment='支付时间')
    create_time = Column(DateTime, index=True, comment='订单创建时间')
    update_time = Column(DateTime, comment='订单更新时间')
    source_order_id = Column(String(64), comment='来源订单ID')
    phone = Column(String(20), index=True, comment='手机号（解密后）')
    
    # 原始 JSON 数据，用于容错和回溯
    raw_data = Column(JSONB, comment='API 返回的完整原始 JSON 数据')
    
    # 记录创建和更新时间
    sync_time = Column(DateTime, default=datetime.now, comment='同步时间')


class TaskMonitor(Base):
    """任务监控模型，用于存储任务状态和心跳信息"""
    
    __tablename__ = 'task_monitor'
    
    task_id = Column(String(64), primary_key=True, comment='任务ID')
    status = Column(String(32), comment='任务状态（RUNNING, STOPPED, ERROR）')
    last_sync_time = Column(DateTime, comment='最后同步时间')
    last_heartbeat = Column(DateTime, comment='最后心跳时间')
    target_command = Column(String(32), comment='目标控制指令（STOP, START）')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class DatabaseManager:
    """数据库管理器，负责连接和数据操作"""
    
    @staticmethod
    def _normalize_secret(secret: str) -> str:
        """
        标准化Secret到32位
        
        如果小于32位，使用#补齐（左->右->左...）
        如果大于32位，裁剪（左->右->左...）
        
        Args:
            secret: 原始Secret
            
        Returns:
            str: 32位的Secret
        """
        # 去除前后空格
        secret = secret.strip()
        
        if len(secret) == 32:
            return secret
        
        if len(secret) < 32:
            # 补齐到32位
            pad_char = '#'
            while len(secret) < 32:
                secret = pad_char + secret  # 补左侧
                if len(secret) < 32:
                    secret = secret + pad_char  # 补右侧
        else:
            # 裁剪到32位
            while len(secret) > 32:
                secret = secret[1:]  # 裁剪左侧
                if len(secret) > 32:
                    secret = secret[:-1]  # 裁剪右侧
        
        return secret
    
    @staticmethod
    def _decrypt_phone(phone_encrypt: str, app_secret: str) -> str:
        """
        解密手机号
        
        解密步骤：
        1. 将ClientSecret标准化到32位
           - 如果小于32位，使用#补齐（左->右->左...）
           - 如果大于32位，裁剪（左->右->左...）
        2. 提取Key（前32位）和IV（右侧16位）
        3. Base64解码密文
        4. AES-256-CBC解密，去除PKCS5Padding
        
        Args:
            phone_encrypt: 加密的手机号（Base64编码）
            app_secret: 应用的ClientSecret
            
        Returns:
            str: 解密后的手机号（11位）
        """
        try:
            # 步骤1：标准化ClientSecret到32位
            secret = DatabaseManager._normalize_secret(app_secret)
            
            # 步骤2：提取Key和IV
            key = secret[:32].encode('utf-8')  # 前32位作为Key
            iv = secret[16:32].encode('utf-8')  # 右侧16位作为IV（实际是第17-32位）
            
            # 步骤3：Base64解码密文
            encrypted_bytes = base64.b64decode(phone_encrypt)
            
            # 步骤4：AES-256-CBC解密
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # 解密
            decrypted_bytes = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            # 去除PKCS5Padding
            pad_length = decrypted_bytes[-1]
            decrypted_bytes = decrypted_bytes[:-pad_length]
            
            # 转换为字符串
            phone = decrypted_bytes.decode('utf-8')
            
            return phone
            
        except Exception as e:
            logger.error(f"解密手机号失败: {e}")
            raise
    
    def __init__(self, db_url: str, app_secret: str = None):
        """
        初始化数据库连接
        
        如果数据库不存在，会自动创建
        
        Args:
            db_url: 数据库连接字符串
            app_secret: 抖音应用Secret（用于解密手机号）
        """
        self.db_url = db_url
        self.app_secret = app_secret
        
        # 提取数据库名称
        self.db_name = self._extract_db_name(db_url)
        
        # 尝试连接，如果数据库不存在则创建
        self._ensure_database_exists()
        
        # 创建引擎
        self.engine = create_engine(db_url, pool_pre_ping=True, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _extract_db_name(self, db_url: str) -> str:
        """
        从数据库 URL 中提取数据库名称
        
        Args:
            db_url: 数据库连接字符串
            
        Returns:
            str: 数据库名称
        """
        # 解析 URL，格式如: postgresql+psycopg2://user:pass@host:port/dbname
        match = re.search(r'/([^/?]+)$', db_url)
        if match:
            return match.group(1)
        raise ValueError(f"无法从 URL 中提取数据库名称: {db_url}")
    
    def _ensure_database_exists(self):
        """
        确保数据库存在，如果不存在则创建
        
        连接到 postgres 默认数据库，检查目标数据库是否存在，
        不存在则创建
        """
        # 构建连接到 postgres 数据库的 URL
        postgres_url = re.sub(r'/[^/?]+$', '/postgres', self.db_url)
        
        try:
            # 尝试直接连接到目标数据库
            test_engine = create_engine(self.db_url, pool_pre_ping=True, echo=False)
            conn = test_engine.connect()
            conn.close()
            test_engine.dispose()
            logger.info(f"数据库 {self.db_name} 已存在")
        except Exception as e:
            # 如果连接失败，可能是数据库不存在
            logger.info(f"尝试连接数据库 {self.db_name} 失败: {e}")
            logger.info(f"尝试创建数据库 {self.db_name}")
            
            try:
                # 连接到 postgres 数据库
                postgres_engine = create_engine(postgres_url, pool_pre_ping=True, echo=False)
                conn = postgres_engine.connect()
                
                # 设置为自动提交模式，以便执行 CREATE DATABASE
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                
                # 检查数据库是否存在
                result = conn.execute(text(
                    f"SELECT 1 FROM pg_database WHERE datname = '{self.db_name}'"
                ))
                
                if not result.fetchone():
                    # 数据库不存在，创建它
                    logger.info(f"创建数据库 {self.db_name}")
                    conn.execute(text(f"CREATE DATABASE {self.db_name}"))
                    logger.info(f"数据库 {self.db_name} 创建成功")
                else:
                    logger.info(f"数据库 {self.db_name} 已存在")
                
                conn.close()
                postgres_engine.dispose()
            except Exception as create_error:
                logger.error(f"创建数据库失败: {create_error}")
                raise
    
    def create_tables(self):
        """创建所有必要的数据表"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """
        获取数据库会话
        
        Returns:
            SQLAlchemy Session 对象
        """
        return self.SessionLocal()
    
    def save_orders(self, orders_data):
        """
        保存订单数据（Upsert 逻辑）
        
        如果订单已存在则更新，不存在则插入
        使用 PostgreSQL 专用的 ON CONFLICT DO UPDATE 语法
        
        Args:
            orders_data: 订单数据列表，支持 list 或 generator
            
        Returns:
            int: 成功保存的订单数量
        """
        # 转换为 list（处理 generator 的情况）
        if not orders_data:
            return 0
        
        orders_list = list(orders_data) if not isinstance(orders_data, list) else orders_data
        
        # === 🚑 核心修复: 自动拆包逻辑 START ===
        # 检查列表里的第一项是不是也是个列表？如果是，说明被"套娃"了
        if orders_list and isinstance(orders_list[0], list):
            logger.warning("检测到嵌套列表，正在自动拆包...")
            # 扁平化处理: [[o1, o2], [o3]] -> [o1, o2, o3]
            flat_orders = []
            for item in orders_list:
                if isinstance(item, list):
                    flat_orders.extend(item)
                else:
                    flat_orders.append(item)
            orders_list = flat_orders
        # === 核心修复 END ===

        # 去重逻辑
        unique_orders_map = {}
        for order in orders_list:
            # 加一个保险：万一这里还是不对，打印出来看看是什么
            if not isinstance(order, dict):
                logger.error(f"数据格式错误，跳过: {type(order)} - {str(order)[:100]}")
                continue
                
            order_id = order.get('order_id')
            if order_id:
                unique_orders_map[order_id] = order
        
        clean_orders_list = list(unique_orders_map.values())

        if not clean_orders_list:
            return 0

        session = self.get_session()
        try:
            # 构建订单列表
            order_list = []
            for order_data in clean_orders_list:
                # 解密手机号
                phone = None
                contacts = order_data.get('contacts', [])
                phone_encrypt = contacts[0].get('phone_encrypt') if contacts else None
                if phone_encrypt and self.app_secret:
                    try:
                        phone = DatabaseManager._decrypt_phone(phone_encrypt, self.app_secret)
                    except Exception as e:
                        logger.error(f"解密手机号失败 (订单ID: {order_data.get('order_id')}): {e}")
                        phone = None
                
                # 提取时间字段（Unix时间戳转datetime）
                pay_time_ts = order_data.get('pay_time')
                create_order_time = order_data.get('create_order_time')
                update_order_time = order_data.get('update_order_time')
                
                pay_time = datetime.fromtimestamp(pay_time_ts) if pay_time_ts else None
                create_time = datetime.fromtimestamp(create_order_time) if create_order_time else None
                update_time = datetime.fromtimestamp(update_order_time) if update_order_time else None
                
                # 提取sku_id（优先从根级别获取，不存在则从products数组获取）
                sku_id = order_data.get('sku_id')
                if not sku_id:
                    products = order_data.get('products', [])
                    if products:
                        sku_id = products[0].get('sku_id')
                
                order_list.append({
                    'order_id': order_data.get('order_id'),
                    'order_status': order_data.get('order_status'),
                    'sku_id': sku_id,
                    'sku_name': order_data.get('sku_name'),
                    'pay_amount': order_data.get('pay_amount'),
                    'count': order_data.get('count', 1),
                    'pay_time': pay_time,
                    'create_time': create_time,
                    'update_time': update_time,
                    'source_order_id': order_data.get('source_order_id'),
                    'phone': phone,
                    'raw_data': order_data,
                    'sync_time': datetime.now()
                })
            
            # 使用 PostgreSQL 的 ON CONFLICT 实现 Upsert
            stmt = pg_insert(Order).values(order_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=['order_id'],
                set_={
                    'order_status': stmt.excluded.order_status,
                    'sku_id': stmt.excluded.sku_id,
                    'sku_name': stmt.excluded.sku_name,
                    'pay_amount': stmt.excluded.pay_amount,
                    'count': stmt.excluded.count,
                    'pay_time': stmt.excluded.pay_time,
                    'update_time': stmt.excluded.update_time,
                    'source_order_id': stmt.excluded.source_order_id,
                    'phone': stmt.excluded.phone,
                    'raw_data': stmt.excluded.raw_data,
                    'sync_time': stmt.excluded.sync_time
                }
            )
            
            result = session.execute(stmt)
            session.commit()
            
            return result.rowcount
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def upsert_task_status(self, task_id: str, status: str, 
                          last_sync_time: str = None, 
                          error_message: str = None):
        """
        更新或插入任务状态
        
        Args:
            task_id: 任务 ID
            status: 任务状态（RUNNING, STOPPED, ERROR）
            last_sync_time: 最后同步时间（可选）
            error_message: 错误信息（可选）
        """
        session = self.get_session()
        
        try:
            # 检查任务是否存在
            task = session.query(TaskMonitor).filter_by(task_id=task_id).first()
            
            if task:
                # 更新现有任务
                task.status = status
                if last_sync_time:
                    task.last_sync_time = last_sync_time
                if error_message:
                    task.error_message = error_message
                task.updated_at = datetime.now()
            else:
                # 插入新任务
                new_task = TaskMonitor(
                    task_id=task_id,
                    status=status,
                    last_sync_time=last_sync_time,
                    last_heartbeat=datetime.now(),
                    error_message=error_message
                )
                session.add(new_task)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            包含任务状态的字典
        """
        session = self.get_session()
        
        try:
            task = session.query(TaskMonitor).filter_by(task_id=task_id).first()
            
            if task:
                return {
                    'task_id': task.task_id,
                    'status': task.status,
                    'last_sync_time': task.last_sync_time.isoformat() if task.last_sync_time else None,
                    'last_heartbeat': task.last_heartbeat.isoformat() if task.last_heartbeat else None,
                    'target_command': task.target_command,
                    'error_message': task.error_message
                }
            else:
                return {}
        finally:
            session.close()
    
    def update_heartbeat(self, task_id: str):
        """
        更新心跳时间
        
        Args:
            task_id: 任务 ID
        """
        session = self.get_session()
        
        try:
            stmt = update(TaskMonitor).where(TaskMonitor.task_id == task_id).values(
                last_heartbeat=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_control_command(self, task_id: str) -> str:
        """
        获取控制指令
        
        Args:
            task_id: 任务 ID
            
        Returns:
            str: 控制指令（如 'STOP', 'START'），如果没有指令则返回 None
        """
        task_status = self.get_task_status(task_id)
        return task_status.get('target_command')
    
    def clear_control_command(self, task_id: str):
        """
        清除控制指令
        
        Args:
            task_id: 任务 ID
        """
        session = self.get_session()
        
        try:
            stmt = update(TaskMonitor).where(TaskMonitor.task_id == task_id).values(
                target_command=None
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def ensure_columns(self, model_class):
        """
        通用字段迁移：确保模型的所有字段都存在于数据库中
        
        自动对比模型定义和实际表结构，添加缺失的字段
        
        Args:
            model_class: SQLAlchemy模型类（如Order、TaskMonitor）
        """
        try:
            table_name = model_class.__tablename__
            logger.info(f"检查表 {table_name} 的字段...")
            
            session = self.get_session()
            
            # 获取模型中定义的所有列
            model_columns = {c.name: c for c in model_class.__table__.columns}
            
            # 获取数据库中实际存在的列
            result = session.execute(text(f"""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """))
            db_columns = {row[0]: row for row in result.fetchall()}
            
            # 找出缺失的字段
            missing_columns = set(model_columns.keys()) - set(db_columns.keys())
            
            if missing_columns:
                logger.info(f"检测到表 {table_name} 缺少 {len(missing_columns)} 个字段: {missing_columns}")
                
                # 为每个缺失的字段生成ALTER TABLE语句
                for col_name in missing_columns:
                    column = model_columns[col_name]
                    
                    # 构建列定义
                    col_type = str(column.type)
                    
                    # 处理默认值
                    default_value = ""
                    if column.default is not None:
                        if hasattr(column.default, 'arg'):
                            default_val = column.default.arg
                            if isinstance(default_val, str):
                                default_value = f" DEFAULT '{default_val}'"
                            else:
                                default_value = f" DEFAULT {default_val}"
                    
                    # 处理nullable
                    nullable = "" if column.nullable else " NOT NULL"
                    
                    # 生成ALTER TABLE语句
                    alter_sql = f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type}{nullable}{default_value}
                    """
                    
                    logger.info(f"  添加字段: {col_name} ({col_type})")
                    session.execute(text(alter_sql))
                    
                    # 添加注释（如果有）
                    if column.comment:
                        session.execute(text(f"""
                            COMMENT ON COLUMN {table_name}.{col_name} IS '{column.comment}'
                        """))
                
                session.commit()
                logger.info(f"✓ 表 {table_name} 字段迁移完成")
            else:
                logger.info(f"✓ 表 {table_name} 字段完整")
            
            session.close()
            
        except Exception as e:
            logger.error(f"表 {model_class.__tablename__} 字段迁移失败: {e}")
            raise
    
    def migrate_all_models(self):
        """
        迁移所有模型的字段
        
        一次性检查所有定义的模型，确保表结构一致
        """
        logger.info("开始数据库模型迁移...")
        
        # 遍历所有注册的模型
        for table_name, table_class in Base._decl_class_registry.items():
            if hasattr(table_class, '__tablename__'):
                self.ensure_columns(table_class)
        
        logger.info("数据库模型迁移完成")
