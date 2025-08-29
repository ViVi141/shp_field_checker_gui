#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
统一管理项目的所有配置项

作者: ViVi141
邮箱: 747384120@qq.com
版本: 2.1
更新时间: 2025年8月29日
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """应用程序配置类"""

    # 应用程序信息
    app_name: str = "地理数据质检工具"
    app_version: str = "2.1"
    author: str = "ViVi141"
    email: str = "747384120@qq.com"

    # 文件处理配置
    max_file_size_mb: int = 500  # 最大文件大小(MB)
    batch_size: int = 1000  # 批处理大小
    max_workers: int = 4  # 最大工作线程数

    # 几何处理配置
    default_tolerance: float = 0.001  # 默认容差
    min_tolerance: float = 0.0001  # 最小容差
    max_tolerance: float = 1.0  # 最大容差

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "shp_checker.log"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    # UI配置
    window_width: int = 1200
    window_height: int = 800
    font_family: str = "Microsoft YaHei UI"
    font_size: int = 9

    # 性能配置
    enable_progress_bar: bool = True
    enable_memory_monitoring: bool = True
    cache_size_mb: int = 100

    # 输出配置
    default_output_format: str = "json"
    auto_backup: bool = True
    backup_suffix: str = ".backup"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建配置"""
        return cls(**data)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = Path(config_file)
        self.config = AppConfig()
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = AppConfig.from_dict(data)
                logging.info(f"配置文件加载成功: {self.config_file}")
            else:
                self._save_config()  # 创建默认配置文件
                logging.info(f"创建默认配置文件: {self.config_file}")
        except Exception as e:
            logging.error(f"配置文件加载失败: {e}")
            self.config = AppConfig()  # 使用默认配置

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
            logging.info(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            logging.error(f"配置文件保存失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        """设置配置项"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self._save_config()
        else:
            logging.warning(f"未知的配置项: {key}")

    def update(self, **kwargs):
        """批量更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                logging.warning(f"未知的配置项: {key}")
        self._save_config()

    def reset_to_default(self):
        """重置为默认配置"""
        self.config = AppConfig()
        self._save_config()
        logging.info("配置已重置为默认值")


# 错误级别配置
ERROR_LEVELS = {
    'CRITICAL': 'critical',
    'HIGH': 'high',
    'MEDIUM': 'medium',
    'LOW': 'low',
    'INFO': 'info'
}

# 支持的文件格式
SUPPORTED_FORMATS = {
    'vector': ['.shp', '.gdb', '.gpkg', '.geojson'],
    'raster': ['.tif', '.tiff', '.img', '.hdf'],
    'table': ['.dbf', '.csv', '.xlsx', '.xls']
}

# 几何类型映射
GEOMETRY_TYPE_MAP = {
    'Point': '点',
    'LineString': '线',
    'Polygon': '面',
    'MultiPoint': '多点',
    'MultiLineString': '多线',
    'MultiPolygon': '多面',
    'GeometryCollection': '几何集合'
}

# 字段类型映射
FIELD_TYPE_MAP = {
    'object': '文本',
    'int64': '整数',
    'float64': '浮点数',
    'bool': '布尔',
    'datetime64': '日期时间',
    'geometry': '几何'
}

# 默认字段标准
DEFAULT_FIELD_STANDARDS = {
    "required_fields": [
        {"name": "OBJECTID", "type": "int64", "description": "对象ID"},
        {"name": "SHAPE", "type": "geometry", "description": "几何形状"}
    ],
    "field_rules": {
        "max_length": 254,
        "min_length": 1,
        "allow_null": False,
        "allow_duplicate": False
    }
}

# 全局配置实例
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取全局配置"""
    return config_manager.config


def update_config(**kwargs):
    """更新全局配置"""
    config_manager.update(**kwargs)


def get_error_level(level_name: str) -> str:
    """获取错误级别"""
    return ERROR_LEVELS.get(level_name.upper(), ERROR_LEVELS['MEDIUM'])


def is_supported_format(file_path: str, format_type: str = 'vector') -> bool:
    """检查文件格式是否支持"""
    file_ext = Path(file_path).suffix.lower()
    return file_ext in SUPPORTED_FORMATS.get(format_type, [])


def get_geometry_type_name(geom_type: str) -> str:
    """获取几何类型的中文名称"""
    return GEOMETRY_TYPE_MAP.get(geom_type, geom_type)


def get_field_type_name(field_type: str) -> str:
    """获取字段类型的中文名称"""
    return FIELD_TYPE_MAP.get(field_type, field_type)
