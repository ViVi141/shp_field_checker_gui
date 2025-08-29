#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
统一管理项目的日志记录

作者: ViVi141
邮箱: 747384120@qq.com
版本: 2.1
更新时间: 2025年8月29日
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        # 添加颜色
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


class LoggerManager:
    """日志管理器"""

    def __init__(self,
                 log_file: str = "shp_checker.log",
                 log_level: str = "INFO",
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_colors: bool = True):

        self.log_file = Path(log_file)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # 转换为字节
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_colors = enable_colors and sys.stdout.isatty()

        self._setup_logger()

    def _setup_logger(self):
        """设置日志器"""
        # 获取根日志器
        self.logger = logging.getLogger()
        self.logger.setLevel(self.log_level)

        # 清除现有的处理器
        self.logger.handlers.clear()

        # 设置日志格式
        if self.enable_colors:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        # 控制台处理器
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # 文件处理器
        if self.enable_file:
            # 确保日志目录存在
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            # 使用轮转文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # 记录日志系统启动信息
        self.logger.info("=" * 60)
        self.logger.info("日志系统启动")
        self.logger.info(f"日志级别: {logging.getLevelName(self.log_level)}")
        self.logger.info(f"日志文件: {self.log_file}")
        self.logger.info(f"控制台输出: {'启用' if self.enable_console else '禁用'}")
        self.logger.info(f"文件输出: {'启用' if self.enable_file else '禁用'}")
        self.logger.info(f"彩色输出: {'启用' if self.enable_colors else '禁用'}")
        self.logger.info("=" * 60)

    def set_level(self, level: str):
        """设置日志级别"""
        new_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(new_level)

        # 更新所有处理器的级别
        for handler in self.logger.handlers:
            handler.setLevel(new_level)

        self.logger.info(f"日志级别已更改为: {level.upper()}")

    def add_file_handler(self, log_file: str, level: Optional[str] = None):
        """添加额外的文件处理器"""
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )

        if level:
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        else:
            handler.setLevel(self.log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.info(f"添加文件处理器: {log_file}")

    def get_log_stats(self) -> dict:
        """获取日志统计信息"""
        stats = {
            'log_file': str(self.log_file),
            'log_file_exists': self.log_file.exists(),
            'log_file_size': 0,
            'backup_files': [],
            'handlers_count': len(self.logger.handlers)
        }

        if self.log_file.exists():
            stats['log_file_size'] = self.log_file.stat().st_size

        # 查找备份文件
        for i in range(1, self.backup_count + 1):
            backup_file = self.log_file.with_suffix(f"{self.log_file.suffix}.{i}")
            if backup_file.exists():
                stats['backup_files'].append({
                    'file': str(backup_file),
                    'size': backup_file.stat().st_size
                })

        return stats

    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        import time

        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 3600)

        cleaned_files = []

        # 清理主日志文件
        if self.log_file.exists():
            file_time = self.log_file.stat().st_mtime
            if file_time < cutoff_time:
                self.log_file.unlink()
                cleaned_files.append(str(self.log_file))

        # 清理备份文件
        for i in range(1, self.backup_count + 1):
            backup_file = self.log_file.with_suffix(f"{self.log_file.suffix}.{i}")
            if backup_file.exists():
                file_time = backup_file.stat().st_mtime
                if file_time < cutoff_time:
                    backup_file.unlink()
                    cleaned_files.append(str(backup_file))

        if cleaned_files:
            self.logger.info(f"清理了 {len(cleaned_files)} 个旧日志文件")
            for file_path in cleaned_files:
                self.logger.info(f"已删除: {file_path}")
        else:
            self.logger.info("没有需要清理的旧日志文件")


def setup_logging(log_file: str = "shp_checker.log",
                  log_level: str = "INFO",
                  max_file_size_mb: int = 10,
                  backup_count: int = 5,
                  enable_console: bool = True,
                  enable_file: bool = True,
                  enable_colors: bool = True) -> LoggerManager:
    """设置日志系统"""
    return LoggerManager(
        log_file=log_file,
        log_level=log_level,
        max_file_size_mb=max_file_size_mb,
        backup_count=backup_count,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_colors=enable_colors
    )


def get_logger(name: str = None) -> logging.Logger:
    """获取日志器"""
    if name:
        return logging.getLogger(name)
    return logging.getLogger()


# 性能日志装饰器
def log_performance(func):
    """性能日志装饰器"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = datetime.now()

        logger.debug(f"开始执行函数: {func.__name__}")

        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.debug(f"函数 {func.__name__} 执行完成，耗时: {duration:.3f}秒")
            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"函数 {func.__name__} 执行失败，耗时: {duration:.3f}秒，错误: {e}")
            raise

    return wrapper


# 全局日志管理器实例
logger_manager = None


def init_logging(**kwargs) -> LoggerManager:
    """初始化日志系统"""
    global logger_manager
    logger_manager = setup_logging(**kwargs)
    return logger_manager


def get_logger_manager() -> Optional[LoggerManager]:
    """获取日志管理器"""
    return logger_manager
