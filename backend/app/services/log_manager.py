"""
日志管理模块

提供帧解析过程的日志记录功能，支持按帧ID查询解析步骤。
"""
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock


class ParseLogEntry:
    """日志条目"""

    def __init__(self, level: str, step: str, message: str, timestamp: Optional[str] = None):
        self.level = level
        self.step = step
        self.message = message
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "step": self.step,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class LogManager:
    """
    日志管理器 - 单例模式

    管理所有帧的解析日志，支持:
    - 添加日志条目
    - 按帧ID查询日志
    - 日志级别过滤
    - 自动清理旧日志
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 日志存储: frame_id -> list of ParseLogEntry
        self._logs: Dict[str, List[ParseLogEntry]] = {}
        self._lock = Lock()

        # 最大保留帧数
        self._max_frames = 1000

        # 日志级别定义
        self.LEVELS = {
            "debug": 10,
            "info": 20,
            "warn": 30,
            "error": 40,
        }

    def add_log(self, frame_id: str, level: str, step: str, message: str) -> None:
        """
        添加一条日志

        Args:
            frame_id: 帧ID
            level: 日志级别 (debug/info/warn/error)
            step: 解析步骤 (wrapper/ciphering/compression/apdu/datamodel)
            message: 日志消息
        """
        with self._lock:
            if frame_id not in self._logs:
                self._logs[frame_id] = []
                self._cleanup_old()

            entry = ParseLogEntry(level=level, step=step, message=message)
            self._logs[frame_id].append(entry)

    def get_logs(self, frame_id: str, min_level: str = "debug") -> List[dict]:
        """
        获取指定帧的所有日志

        Args:
            frame_id: 帧ID
            min_level: 最低日志级别

        Returns:
            日志条目字典列表
        """
        with self._lock:
            entries = self._logs.get(frame_id, [])
            min_level_val = self.LEVELS.get(min_level, 0)
            return [
                e.to_dict()
                for e in entries
                if self.LEVELS.get(e.level, 0) >= min_level_val
            ]

    def get_log_entries(self, frame_id: str) -> List[ParseLogEntry]:
        """获取日志条目对象列表"""
        with self._lock:
            return list(self._logs.get(frame_id, []))

    def clear_logs(self, frame_id: Optional[str] = None) -> None:
        """
        清除日志

        Args:
            frame_id: 帧ID，None表示清除所有
        """
        with self._lock:
            if frame_id is None:
                self._logs.clear()
            else:
                self._logs.pop(frame_id, None)

    def new_frame_id(self) -> str:
        """生成新的帧ID"""
        return str(uuid.uuid4())[:8]

    def _cleanup_old(self) -> None:
        """清理超出数量限制的旧日志（内部调用，调用方需持锁）"""
        if len(self._logs) > self._max_frames:
            # 移除最早的条目
            oldest_keys = sorted(self._logs.keys())[:len(self._logs) - self._max_frames]
            for key in oldest_keys:
                del self._logs[key]

    def get_stats(self) -> dict:
        """获取日志统计信息"""
        with self._lock:
            total_entries = sum(len(v) for v in self._logs.values())
            return {
                "frame_count": len(self._logs),
                "total_entries": total_entries,
                "max_frames": self._max_frames,
            }

    def debug(self, frame_id: str, step: str, message: str) -> None:
        """便捷方法 - debug级别"""
        self.add_log(frame_id, "debug", step, message)

    def info(self, frame_id: str, step: str, message: str) -> None:
        """便捷方法 - info级别"""
        self.add_log(frame_id, "info", step, message)

    def warn(self, frame_id: str, step: str, message: str) -> None:
        """便捷方法 - warn级别"""
        self.add_log(frame_id, "warn", step, message)

    def error(self, frame_id: str, step: str, message: str) -> None:
        """便捷方法 - error级别"""
        self.add_log(frame_id, "error", step, message)


# 全局单例实例
log_manager = LogManager()
