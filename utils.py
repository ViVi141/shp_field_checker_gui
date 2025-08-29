#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
包含项目中使用的通用工具函数

作者: ViVi141
邮箱: 747384120@qq.com
版本: 2.1
更新时间: 2025年8月29日
"""

import os
import sys
import hashlib
import logging
import time
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import warnings

# 忽略警告
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.start_time = None
        self.memory_start = None
        self.process = psutil.Process()

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.memory_start = self.process.memory_info().rss / 1024 / 1024  # MB
        logging.info(f"性能监控开始 - 初始内存: {self.memory_start:.2f} MB")

    def stop(self) -> Dict[str, float]:
        """停止监控并返回统计信息"""
        if self.start_time is None:
            return {}

        end_time = time.time()
        memory_end = self.process.memory_info().rss / 1024 / 1024  # MB

        duration = end_time - self.start_time
        memory_used = memory_end - self.memory_start

        stats = {
            'duration': duration,
            'memory_start': self.memory_start,
            'memory_end': memory_end,
            'memory_used': memory_used,
            'cpu_percent': self.process.cpu_percent()
        }

        logging.info(f"性能监控结束 - 耗时: {duration:.2f}s, 内存使用: {memory_used:.2f} MB")
        return stats


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total
        self.current = 0
        self.callback = callback
        self.start_time = time.time()

    def update(self, increment: int = 1, message: str = ""):
        """更新进度"""
        self.current += increment
        progress = (self.current / self.total) * 100 if self.total > 0 else 0

        if self.callback:
            self.callback(self.current, self.total, message)

        # 每10%记录一次日志
        if int(progress) % 10 == 0 and progress > 0:
            elapsed = time.time() - self.start_time
            eta = (elapsed / self.current) * (self.total - self.current) if self.current > 0 else 0
            logging.info(f"进度: {progress:.1f}% ({self.current}/{self.total}) - {message} - 预计剩余: {eta:.1f}s")

    def finish(self):
        """完成进度跟踪"""
        elapsed = time.time() - self.start_time
        logging.info(f"任务完成 - 总耗时: {elapsed:.2f}s")


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """计算文件哈希值"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return ""

        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()
    except Exception as e:
        logging.error(f"计算文件哈希失败 {file_path}: {e}")
        return ""


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """格式化时间长度"""
    if seconds < 1:
        return f"{seconds * 1000:.0f} 毫秒"
    elif seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} 分钟"
    else:
        return f"{seconds / 3600:.1f} 小时"


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """安全转换为字符串"""
    try:
        return str(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def ensure_directory(path: Union[str, Path]) -> Path:
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_encoding(file_path: Union[str, Path]) -> str:
    """检测文件编码"""
    import chardet

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 读取前10KB
            result = chardet.detect(raw_data)
            return result.get('encoding', 'utf-8')
    except Exception:
        return 'utf-8'


def validate_file_path(file_path: Union[str, Path]) -> bool:
    """验证文件路径"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    try:
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
            'memory_available': psutil.virtual_memory().available / 1024 / 1024 / 1024,  # GB
            'disk_usage': psutil.disk_usage('/').percent if sys.platform != 'win32' else psutil.disk_usage('C:').percent
        }
    except Exception as e:
        logging.error(f"获取系统信息失败: {e}")
        return {}


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logging.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}, {delay}秒后重试")
                        time.sleep(delay)
                    else:
                        logging.error(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}")

            raise last_exception
        return wrapper
    return decorator


def batch_process(items: List[Any], batch_size: int, processor: Callable,
                 progress_callback: Optional[Callable] = None) -> List[Any]:
    """批量处理数据"""
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1

        if progress_callback:
            progress_callback(batch_num, total_batches, f"处理批次 {batch_num}/{total_batches}")

        try:
            batch_results = processor(batch)
            results.extend(batch_results)
        except Exception as e:
            logging.error(f"批次 {batch_num} 处理失败: {e}")
            # 可以选择跳过失败的批次或抛出异常
            continue

    return results


def create_backup(file_path: Union[str, Path], backup_suffix: str = ".backup") -> Optional[Path]:
    """创建文件备份"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

        # 如果备份文件已存在，添加时间戳
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f"{file_path.suffix}.{timestamp}{backup_suffix}")

        import shutil
        shutil.copy2(file_path, backup_path)
        logging.info(f"备份文件创建成功: {backup_path}")
        return backup_path

    except Exception as e:
        logging.error(f"创建备份失败 {file_path}: {e}")
        return None


def cleanup_temp_files(temp_dir: Union[str, Path], max_age_hours: int = 24):
    """清理临时文件"""
    try:
        temp_dir = Path(temp_dir)
        if not temp_dir.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    logging.info(f"清理临时文件: {file_path}")

    except Exception as e:
        logging.error(f"清理临时文件失败: {e}")


class MemoryManager:
    """内存管理器"""

    def __init__(self, max_memory_mb: int = 1000):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()

    def check_memory_usage(self) -> Dict[str, float]:
        """检查内存使用情况"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        return {
            'current_mb': memory_mb,
            'max_mb': self.max_memory_mb,
            'usage_percent': (memory_mb / self.max_memory_mb) * 100
        }

    def is_memory_high(self, threshold: float = 0.8) -> bool:
        """检查内存使用是否过高"""
        usage = self.check_memory_usage()
        return usage['usage_percent'] > (threshold * 100)

    def force_garbage_collection(self):
        """强制垃圾回收"""
        import gc
        gc.collect()
        logging.info("执行垃圾回收")


# 全局实例
performance_monitor = PerformanceMonitor()
memory_manager = MemoryManager()
