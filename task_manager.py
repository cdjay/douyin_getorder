"""
任务管理模块
负责向数据库汇报心跳，并读取后台控制指令（STOP/START）
实现监控与通信的解耦
"""
from datetime import datetime
from typing import Optional
from database import DatabaseManager


class TaskManager:
    """任务管理器，处理心跳汇报和控制指令读取"""
    
    def __init__(self, db_manager: DatabaseManager, task_id: str):
        """
        初始化任务管理器
        
        Args:
            db_manager: 数据库管理器实例
            task_id: 任务唯一标识
        """
        self.db_manager = db_manager
        self.task_id = task_id
    
    def update_heartbeat(self):
        """
        更新心跳时间到数据库
        
        用于监控系统判断任务是否存活
        """
        self.db_manager.update_heartbeat(self.task_id)
    
    def get_control_command(self) -> Optional[str]:
        """
        获取后台控制指令
        
        Returns:
            Optional[str]: 返回控制指令（如 'STOP', 'START'），如果没有指令则返回 None
        """
        return self.db_manager.get_control_command(self.task_id)
    
    def clear_control_command(self):
        """
        清除已执行的控制指令
        """
        self.db_manager.clear_control_command(self.task_id)
    
    def set_task_status(self, status: str, last_sync_time: str = None, 
                       error_message: str = None):
        """
        设置任务状态
        
        Args:
            status: 任务状态（RUNNING, STOPPED, ERROR）
            last_sync_time: 最后同步时间（可选）
            error_message: 错误信息（可选）
        """
        self.db_manager.upsert_task_status(
            task_id=self.task_id,
            status=status,
            last_sync_time=last_sync_time,
            error_message=error_message
        )
    
    def get_task_status(self) -> dict:
        """
        获取当前任务状态
        
        Returns:
            dict: 包含任务状态信息的字典
        """
        return self.db_manager.get_task_status(self.task_id)
    
    def should_stop(self) -> bool:
        """
        检查是否应该停止任务
        
        Returns:
            bool: 如果收到 STOP 指令，返回 True；否则返回 False
        """
        command = self.get_control_command()
        return command == 'STOP'
