#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理模块
统一管理项目中的错误处理和用户友好的错误信息

作者: ViVi141
邮箱: 747384120@qq.com
版本: 2.1
更新时间: 2025年8月29日
"""

import logging
import traceback
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"    # 严重错误，程序无法继续
    HIGH = "high"           # 高优先级错误，需要立即处理
    MEDIUM = "medium"       # 中等优先级错误，建议处理
    LOW = "low"            # 低优先级错误，可以忽略
    INFO = "info"          # 信息提示


class ErrorCategory(Enum):
    """错误类别"""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    ENCODING_ERROR = "encoding_error"
    GEOMETRY_ERROR = "geometry_error"
    TOPOLOGY_ERROR = "topology_error"
    FIELD_ERROR = "field_error"
    NETWORK_ERROR = "network_error"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """错误信息类"""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    suggestion: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorHandler:
    """错误处理器"""

    # 错误类型映射
    ERROR_TYPE_MAP = {
        'file_not_found': '文件未找到',
        'permission_denied': '权限不足',
        'encoding_error': '编码错误',
        'geometry_error': '几何错误',
        'topology_error': '拓扑错误',
        'field_error': '字段错误',
        'network_error': '网络错误',
        'memory_error': '内存错误',
        'validation_error': '验证错误',
        'unknown_error': '未知错误'
    }

    # 错误严重程度映射
    SEVERITY_MAP = {
        'critical': '严重',
        'high': '高',
        'medium': '中',
        'low': '低',
        'info': '信息'
    }

    # 常见错误模式和建议
    ERROR_PATTERNS = {
        # 文件相关错误
        r"FileNotFoundError|No such file or directory": {
            'category': ErrorCategory.FILE_NOT_FOUND,
            'severity': ErrorSeverity.HIGH,
            'suggestion': "请检查文件路径是否正确，确保文件存在"
        },
        r"PermissionError|Access is denied": {
            'category': ErrorCategory.PERMISSION_DENIED,
            'severity': ErrorSeverity.HIGH,
            'suggestion': "请检查文件权限，确保有读取/写入权限"
        },
        r"UnicodeDecodeError|encoding.*error": {
            'category': ErrorCategory.ENCODING_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "文件编码格式不支持，请尝试转换文件编码或使用UTF-8格式"
        },

        # 几何相关错误
        r"MULTIPOLYGON.*POLYGON|geometry.*type.*mismatch": {
            'category': ErrorCategory.GEOMETRY_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "几何类型不匹配，已自动转换几何类型"
        },
        r"invalid.*geometry|geometry.*validation": {
            'category': ErrorCategory.GEOMETRY_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "几何体无效，建议使用几何修复功能"
        },
        r"topology.*error|gap.*detection": {
            'category': ErrorCategory.TOPOLOGY_ERROR,
            'severity': ErrorSeverity.LOW,
            'suggestion': "拓扑错误，建议使用拓扑修复功能"
        },

        # 字段相关错误
        r"field.*not.*found|column.*not.*found": {
            'category': ErrorCategory.FIELD_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "字段不存在，请检查字段名称或添加缺失字段"
        },
        r"field.*type.*error|data.*type.*mismatch": {
            'category': ErrorCategory.FIELD_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "字段类型不匹配，请检查数据类型"
        },

        # 内存相关错误
        r"MemoryError|out.*of.*memory": {
            'category': ErrorCategory.MEMORY_ERROR,
            'severity': ErrorSeverity.HIGH,
            'suggestion': "内存不足，建议减少批处理大小或关闭其他程序"
        },

        # 网络相关错误
        r"ConnectionError|timeout|network": {
            'category': ErrorCategory.NETWORK_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'suggestion': "网络连接问题，请检查网络连接或稍后重试"
        }
    }

    @classmethod
    def classify_error(cls, error_message: str) -> ErrorInfo:
        """分类错误信息"""
        import re

        error_message = str(error_message)

        # 匹配错误模式
        for pattern, error_config in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return ErrorInfo(
                    message=error_message,
                    category=error_config['category'],
                    severity=error_config['severity'],
                    suggestion=error_config['suggestion']
                )

        # 默认错误分类
        return ErrorInfo(
            message=error_message,
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            suggestion="未知错误，请查看详细日志或联系技术支持"
        )

    @classmethod
    def get_user_friendly_message(cls, error_message: str, file_name: str = "") -> str:
        """获取用户友好的错误信息"""
        error_info = cls.classify_error(error_message)

        # 构建友好的错误信息
        friendly_message = f"❌ {cls.ERROR_TYPE_MAP.get(error_info.category.value, '错误')}\n\n"
        friendly_message += f"📝 错误描述: {error_info.message}\n\n"

        if file_name:
            friendly_message += f"📁 相关文件: {file_name}\n\n"

        friendly_message += f"💡 解决建议: {error_info.suggestion}\n\n"
        friendly_message += f"⚠️ 严重程度: {cls.SEVERITY_MAP.get(error_info.severity.value, '中')}"

        return friendly_message

    @classmethod
    def get_error_priority(cls, error_type: str) -> int:
        """获取错误优先级（数字越小优先级越高）"""
        priority_map = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4,
            'info': 5
        }
        return priority_map.get(error_type.lower(), 3)

    @classmethod
    def log_error(cls, error: Exception, context: str = "", file_name: str = ""):
        """记录错误日志"""
        error_info = cls.classify_error(str(error))

        # 构建日志消息
        log_message = f"错误发生 - 类别: {error_info.category.value}, 严重程度: {error_info.severity.value}"
        if context:
            log_message += f", 上下文: {context}"
        if file_name:
            log_message += f", 文件: {file_name}"

        log_message += f"\n错误信息: {error_info.message}"
        log_message += f"\n解决建议: {error_info.suggestion}"

        # 根据严重程度选择日志级别
        if error_info.severity == ErrorSeverity.CRITICAL:
            logging.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            logging.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logging.warning(log_message)
        else:
            logging.info(log_message)

        # 记录详细堆栈信息（仅在调试模式下）
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"详细堆栈信息:\n{traceback.format_exc()}")

    @classmethod
    def create_error_report(cls, errors: List[Exception], context: str = "") -> Dict[str, Any]:
        """创建错误报告"""
        error_summary = {
            'total_errors': len(errors),
            'error_categories': {},
            'error_severities': {},
            'errors': []
        }

        for error in errors:
            error_info = cls.classify_error(str(error))

            # 统计错误类别
            category = error_info.category.value
            error_summary['error_categories'][category] = error_summary['error_categories'].get(category, 0) + 1

            # 统计错误严重程度
            severity = error_info.severity.value
            error_summary['error_severities'][severity] = error_summary['error_severities'].get(severity, 0) + 1

            # 添加错误详情
            error_summary['errors'].append({
                'message': error_info.message,
                'category': category,
                'severity': severity,
                'suggestion': error_info.suggestion
            })

        return error_summary


class ValidationError(Exception):
    """验证错误"""
    def __init__(self, message: str, field: str = "", value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class GeometryError(Exception):
    """几何错误"""
    def __init__(self, message: str, geometry_type: str = "", feature_id: int = None):
        super().__init__(message)
        self.geometry_type = geometry_type
        self.feature_id = feature_id


class TopologyError(Exception):
    """拓扑错误"""
    def __init__(self, message: str, error_type: str = "", feature_ids: List[int] = None):
        super().__init__(message)
        self.error_type = error_type
        self.feature_ids = feature_ids or []


class FieldError(Exception):
    """字段错误"""
    def __init__(self, message: str, field_name: str = "", field_type: str = ""):
        super().__init__(message)
        self.field_name = field_name
        self.field_type = field_type


# 全局错误处理器实例
error_handler = ErrorHandler()
