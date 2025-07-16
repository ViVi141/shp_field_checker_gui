#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码修复工具函数
专门处理乱码和编码转换问题
"""

import logging

logger = logging.getLogger(__name__)

def fix_garbled_text(text):
    """
    修复乱码文本
    
    Args:
        text: 可能包含乱码的文本
        
    Returns:
        修复后的文本
    """
    if not isinstance(text, str):
        return str(text)
    
    # 如果文本为空或太短，直接返回
    if not text or len(text) < 2:
        return text
    
    # 检查是否包含乱码字符（高字节字符）
    if any(ord(c) > 127 for c in text[:min(10, len(text))]):
        # 尝试修复乱码
        try:
            # 方法1：尝试从latin1重新解码
            for encoding in ['gbk', 'gb2312', 'utf-8']:
                try:
                    # 先编码为latin1，再解码为目标编码
                    encoded = text.encode('latin1')
                    decoded = encoded.decode(encoding)
                    logger.info(f"成功修复乱码: {text[:20]}... -> {decoded[:20]}...")
                    return decoded
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
            
            # 方法2：直接尝试不同编码
            for encoding in ['gbk', 'gb2312', 'utf-8']:
                try:
                    decoded = text.encode('latin1').decode(encoding)
                    if decoded != text:  # 确保有变化
                        logger.info(f"成功修复乱码: {text[:20]}... -> {decoded[:20]}...")
                        return decoded
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
                    
        except Exception as e:
            logger.warning(f"修复乱码失败: {e}")
    
    return text

def fix_special_chars_for_display(text):
    """
    修复特殊字符用于显示，特别是书名号等Unicode字符
    
    Args:
        text: 原始文本
        
    Returns:
        修复后的文本
    """
    if not isinstance(text, str):
        return str(text)
    
    # 常见的书名号和其他特殊字符映射
    char_mapping = {
        # 书名号
        '\u300a': '《',  # 左书名号
        '\u300b': '》',  # 右书名号
        # 引号
        '\u201c': '"',   # 左双引号
        '\u201d': '"',   # 右双引号
        '\u2018': "'",   # 左单引号
        '\u2019': "'",   # 右单引号
        # 破折号
        '\u2014': '—',   # 长破折号
        '\u2013': '–',   # 短破折号
        # 省略号
        '\u2026': '...', # 省略号
        # 其他常见符号
        '\u00a0': ' ',   # 不间断空格
        '\u200b': '',    # 零宽空格
        '\u200c': '',    # 零宽非连接符
        '\u200d': '',    # 零宽连接符
    }
    
    # 应用字符映射
    for unicode_char, replacement in char_mapping.items():
        text = text.replace(unicode_char, replacement)
    
    return text

def safe_decode_bytes(data):
    """
    安全解码字节数据
    
    Args:
        data: 字节数据
        
    Returns:
        解码后的字符串
    """
    if isinstance(data, bytes):
        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                decoded = data.decode(encoding)
                return decoded
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用错误替换
        return data.decode('utf-8', errors='replace')
    
    return str(data)

def safe_encode_text(text, target_encoding='utf-8'):
    """
    安全编码文本
    
    Args:
        text: 要编码的文本
        target_encoding: 目标编码
        
    Returns:
        编码后的字节数据
    """
    if isinstance(text, str):
        try:
            return text.encode(target_encoding)
        except UnicodeEncodeError:
            # 如果编码失败，尝试修复乱码后再编码
            fixed_text = fix_garbled_text(text)
            try:
                return fixed_text.encode(target_encoding)
            except UnicodeEncodeError:
                return fixed_text.encode(target_encoding, errors='replace')
    
    return str(text).encode(target_encoding, errors='replace')

def detect_encoding(data):
    """
    检测数据编码
    
    Args:
        data: 要检测的数据
        
    Returns:
        最可能的编码
    """
    if isinstance(data, bytes):
        # 简单的编码检测
        try:
            data.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            try:
                data.decode('gbk')
                return 'gbk'
            except UnicodeDecodeError:
                return 'latin1'
    
    return 'utf-8'

def clean_text_for_display(text, max_length=100):
    """
    清理文本用于显示
    
    Args:
        text: 原始文本
        max_length: 最大显示长度
        
    Returns:
        清理后的显示文本
    """
    if text is None:
        return "(空值)"
    
    # 修复乱码
    cleaned_text = fix_garbled_text(str(text))
    
    # 修复特殊字符（包括书名号）
    cleaned_text = fix_special_chars_for_display(cleaned_text)
    
    # 限制长度
    if len(cleaned_text) > max_length:
        cleaned_text = cleaned_text[:max_length-3] + "..."
    
    return cleaned_text 