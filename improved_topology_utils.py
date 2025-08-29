#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的拓扑检查工具
包含优化的面缝隙检测算法和自动修复功能
"""

import logging
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union, snap
from shapely.strtree import STRtree
from shapely.validation import make_valid
import geopandas as gpd
from typing import List, Dict, Tuple, Optional
import math

logger = logging.getLogger(__name__)

class ImprovedTopologyChecker:
    """改进的拓扑检查器"""

    def __init__(self, tolerance=0.001):
        """
        初始化拓扑检查器

        Args:
            tolerance: 容差参数，用于缝隙检测和修复
        """
        self.tolerance = tolerance
        self.spatial_index = None
        self.geometries = []

    def build_spatial_index(self, geometries: List):
        """构建空间索引"""
        try:
            # 过滤空几何
            valid_geometries = [geom for geom in geometries if geom is not None and not geom.is_empty]
            self.geometries = valid_geometries
            self.spatial_index = STRtree(valid_geometries)
            logger.info(f"构建空间索引完成，包含 {len(valid_geometries)} 个几何体")
        except Exception as e:
            logger.error(f"构建空间索引失败: {e}")
            self.spatial_index = None

    def check_topology_gaps_optimized(self, geometries: List, tolerance: Optional[float] = None,
                                     batch_size: int = 1000) -> List[Dict]:
        """
        优化的面缝隙检测算法

        Args:
            geometries: 几何体列表
            tolerance: 容差参数，如果为None则使用实例默认值
            batch_size: 批处理大小，用于大规模数据

        Returns:
            缝隙信息列表
        """
        if tolerance is None:
            tolerance = self.tolerance

        gaps = []

        try:
            # 检查是否需要分批处理
            if len(geometries) > batch_size:
                logger.info(f"数据量较大({len(geometries)}个几何体)，使用分批处理，批次大小: {batch_size}")
                return self._check_gaps_batch_processing(geometries, tolerance, batch_size)

            # 构建空间索引
            self.build_spatial_index(geometries)
            if self.spatial_index is None:
                logger.warning("空间索引构建失败，使用原始算法")
                return self._check_gaps_brute_force(geometries, tolerance)

            logger.info(f"开始优化缝隙检测，容差: {tolerance}")

            for i, geom1 in enumerate(self.geometries):
                if geom1 is None or geom1.is_empty:
                    continue

                # 创建缓冲区，只检查缓冲区内的几何体
                buffer_geom = geom1.buffer(tolerance * 2)  # 扩大缓冲区确保不遗漏
                candidates = self.spatial_index.query(buffer_geom)

                for geom2 in candidates:
                    # 获取几何体在原始列表中的索引
                    try:
                        j = self.geometries.index(geom2)
                    except ValueError:
                        continue

                    # 避免重复检查和自检查
                    if j <= i or geom2 is None or geom2.is_empty:
                        continue

                    try:
                        # 计算距离
                        distance = geom1.distance(geom2)

                        # 检查是否在容差范围内
                        if 0 < distance < tolerance:
                            # 检查是否真正相邻（共享边界）
                            if self._are_adjacent(geom1, geom2, tolerance):
                                gap_info = {
                                    'feature1': i,
                                    'feature2': j,
                                    'distance': distance,
                                    'type': '面缝隙',
                                    'geometry1': geom1,
                                    'geometry2': geom2,
                                    'gap_geometry': self._create_gap_geometry(geom1, geom2, distance)
                                }
                                gaps.append(gap_info)
                                logger.debug(f"发现缝隙: 要素{i}和{j}, 距离: {distance:.6f}")

                    except Exception as e:
                        logger.warning(f"检查几何体 {i} 和 {j} 时出错: {e}")
                        continue

            logger.info(f"缝隙检测完成，发现 {len(gaps)} 个缝隙")
            return gaps

        except Exception as e:
            logger.error(f"优化缝隙检测失败: {e}")
            # 回退到原始算法
            return self._check_gaps_brute_force(geometries, tolerance)

    def _check_gaps_batch_processing(self, geometries: List, tolerance: float, batch_size: int) -> List[Dict]:
        """分批处理大规模数据的缝隙检测"""
        gaps = []
        total_batches = (len(geometries) + batch_size - 1) // batch_size

        logger.info(f"开始分批处理，总共 {total_batches} 个批次")

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(geometries))
            batch_geometries = geometries[start_idx:end_idx]

            logger.info(f"处理批次 {batch_idx + 1}/{total_batches}，几何体范围: {start_idx}-{end_idx-1}")

            # 处理当前批次
            batch_gaps = self._check_gaps_brute_force(batch_geometries, tolerance)

            # 调整索引以匹配原始几何体列表
            for gap in batch_gaps:
                gap['feature1'] += start_idx
                gap['feature2'] += start_idx

            gaps.extend(batch_gaps)

        logger.info(f"分批处理完成，总共发现 {len(gaps)} 个缝隙")
        return gaps

    def _check_gaps_brute_force(self, geometries: List, tolerance: float) -> List[Dict]:
        """原始暴力算法（备用）"""
        gaps = []
        for i, geom1 in enumerate(geometries):
            if geom1 is None or geom1.is_empty:
                continue
            for j, geom2 in enumerate(geometries[i+1:], i+1):
                if geom2 is None or geom2.is_empty:
                    continue
                try:
                    distance = geom1.distance(geom2)
                    if 0 < distance < tolerance:
                        gaps.append({
                            'feature1': i,
                            'feature2': j,
                            'distance': distance,
                            'type': '面缝隙',
                            'geometry1': geom1,
                            'geometry2': geom2
                        })
                except Exception as e:
                    continue
        return gaps

    def _are_adjacent(self, geom1, geom2, tolerance: float) -> bool:
        """
        判断两个几何体是否相邻

        Args:
            geom1: 第一个几何体
            geom2: 第二个几何体
            tolerance: 容差

        Returns:
            是否相邻
        """
        try:
            # 方法1: 检查是否接触
            if geom1.touches(geom2):
                return True

            # 方法2: 检查缓冲区是否相交
            buffer1 = geom1.buffer(tolerance)
            buffer2 = geom2.buffer(tolerance)
            if buffer1.intersects(buffer2):
                # 进一步检查边界是否接近
                boundary1 = geom1.boundary
                boundary2 = geom2.boundary
                if boundary1.distance(boundary2) < tolerance:
                    return True

            # 方法3: 检查边界线是否接近
            if hasattr(geom1, 'exterior') and hasattr(geom2, 'exterior'):
                if geom1.exterior.distance(geom2.exterior) < tolerance:
                    return True

            return False

        except Exception as e:
            logger.warning(f"相邻性判断失败: {e}")
            return True  # 默认认为相邻，避免遗漏

    def _create_gap_geometry(self, geom1, geom2, distance: float):
        """创建缝隙几何体用于可视化"""
        try:
            # 计算两个几何体的最近点
            nearest_points = geom1.exterior.interpolate(geom1.exterior.project(geom2.exterior.interpolate(0)))
            point2 = geom2.exterior.interpolate(geom2.exterior.project(geom1.exterior.interpolate(0)))

            # 创建缝隙线
            gap_line = LineString([nearest_points, point2])
            return gap_line
        except Exception as e:
            logger.warning(f"创建缝隙几何体失败: {e}")
            return None

    def repair_topology_gaps(self, geometries: List, gaps: List[Dict],
                           repair_method: str = 'buffer_merge') -> Tuple[List, Dict]:
        """
        修复面缝隙

        Args:
            geometries: 原始几何体列表
            gaps: 缝隙信息列表
            repair_method: 修复方法 ('buffer_merge', 'snap_vertices', 'extend_boundary')

        Returns:
            (修复后的几何体列表, 修复统计信息)
        """
        if not gaps:
            return geometries, {'repaired_count': 0, 'failed_count': 0, 'method': repair_method}

        logger.info(f"开始修复 {len(gaps)} 个缝隙，使用方法: {repair_method}")

        repaired_geometries = geometries.copy()
        repair_stats = {
            'repaired_count': 0,
            'failed_count': 0,
            'method': repair_method,
            'details': []
        }

        try:
            if repair_method == 'buffer_merge':
                repaired_geometries, stats = self._repair_by_buffer_merge(repaired_geometries, gaps)
            elif repair_method == 'snap_vertices':
                repaired_geometries, stats = self._repair_by_snap_vertices(repaired_geometries, gaps)
            elif repair_method == 'extend_boundary':
                repaired_geometries, stats = self._repair_by_extend_boundary(repaired_geometries, gaps)
            else:
                raise ValueError(f"不支持的修复方法: {repair_method}")

            repair_stats.update(stats)
            logger.info(f"缝隙修复完成: 成功 {repair_stats['repaired_count']} 个, 失败 {repair_stats['failed_count']} 个")

        except Exception as e:
            logger.error(f"缝隙修复失败: {e}")
            repair_stats['failed_count'] = len(gaps)
            repair_stats['error'] = str(e)

        return repaired_geometries, repair_stats

    def _repair_by_buffer_merge(self, geometries: List, gaps: List[Dict]) -> Tuple[List, Dict]:
        """通过缓冲区合并修复缝隙"""
        stats = {'repaired_count': 0, 'failed_count': 0, 'details': []}

        for gap in gaps:
            try:
                idx1, idx2 = gap['feature1'], gap['feature2']
                geom1, geom2 = geometries[idx1], geometries[idx2]

                # 创建缓冲区并合并
                buffer1 = geom1.buffer(self.tolerance / 2)
                buffer2 = geom2.buffer(self.tolerance / 2)

                # 合并缓冲区
                merged = unary_union([buffer1, buffer2])

                # 简化合并后的几何体
                if merged.geom_type == 'Polygon':
                    repaired_geom = merged.simplify(self.tolerance / 10)
                elif merged.geom_type == 'MultiPolygon':
                    # 选择最大的多边形
                    largest = max(merged.geoms, key=lambda g: g.area)
                    repaired_geom = largest.simplify(self.tolerance / 10)
                else:
                    repaired_geom = merged

                # 更新几何体
                geometries[idx1] = repaired_geom
                geometries[idx2] = None  # 标记为已合并

                stats['repaired_count'] += 1
                stats['details'].append({
                    'gap': gap,
                    'method': 'buffer_merge',
                    'success': True
                })

                logger.debug(f"成功修复缝隙: 要素{idx1}和{idx2}")

            except Exception as e:
                stats['failed_count'] += 1
                stats['details'].append({
                    'gap': gap,
                    'method': 'buffer_merge',
                    'success': False,
                    'error': str(e)
                })
                logger.warning(f"修复缝隙失败: {e}")

        return geometries, stats

    def _repair_by_snap_vertices(self, geometries: List, gaps: List[Dict]) -> Tuple[List, Dict]:
        """通过顶点捕捉修复缝隙"""
        stats = {'repaired_count': 0, 'failed_count': 0, 'details': []}

        for gap in gaps:
            try:
                idx1, idx2 = gap['feature1'], gap['feature2']
                geom1, geom2 = geometries[idx1], geometries[idx2]

                # 使用snap函数捕捉顶点
                snapped_geom1 = snap(geom1, geom2, self.tolerance)
                snapped_geom2 = snap(geom2, geom1, self.tolerance)

                # 验证修复结果
                if snapped_geom1.is_valid and snapped_geom2.is_valid:
                    geometries[idx1] = snapped_geom1
                    geometries[idx2] = snapped_geom2

                    stats['repaired_count'] += 1
                    stats['details'].append({
                        'gap': gap,
                        'method': 'snap_vertices',
                        'success': True
                    })
                else:
                    # 如果捕捉失败，尝试修复
                    fixed_geom1 = make_valid(snapped_geom1)
                    fixed_geom2 = make_valid(snapped_geom2)

                    if fixed_geom1.is_valid and fixed_geom2.is_valid:
                        geometries[idx1] = fixed_geom1
                        geometries[idx2] = fixed_geom2
                        stats['repaired_count'] += 1
                    else:
                        stats['failed_count'] += 1

                logger.debug(f"顶点捕捉修复: 要素{idx1}和{idx2}")

            except Exception as e:
                stats['failed_count'] += 1
                stats['details'].append({
                    'gap': gap,
                    'method': 'snap_vertices',
                    'success': False,
                    'error': str(e)
                })
                logger.warning(f"顶点捕捉修复失败: {e}")

        return geometries, stats

    def _repair_by_extend_boundary(self, geometries: List, gaps: List[Dict]) -> Tuple[List, Dict]:
        """通过边界扩展修复缝隙"""
        stats = {'repaired_count': 0, 'failed_count': 0, 'details': []}

        for gap in gaps:
            try:
                idx1, idx2 = gap['feature1'], gap['feature2']
                geom1, geom2 = geometries[idx1], geometries[idx2]

                # 计算缝隙方向
                distance = gap['distance']
                extension_distance = distance / 2 + self.tolerance / 2

                # 扩展边界
                extended_geom1 = geom1.buffer(extension_distance)
                extended_geom2 = geom2.buffer(extension_distance)

                # 合并扩展后的几何体
                merged = unary_union([extended_geom1, extended_geom2])

                # 简化结果
                if merged.geom_type == 'Polygon':
                    repaired_geom = merged.simplify(self.tolerance / 10)
                elif merged.geom_type == 'MultiPolygon':
                    largest = max(merged.geoms, key=lambda g: g.area)
                    repaired_geom = largest.simplify(self.tolerance / 10)
                else:
                    repaired_geom = merged

                # 更新几何体
                geometries[idx1] = repaired_geom
                geometries[idx2] = None

                stats['repaired_count'] += 1
                stats['details'].append({
                    'gap': gap,
                    'method': 'extend_boundary',
                    'success': True
                })

                logger.debug(f"边界扩展修复: 要素{idx1}和{idx2}")

            except Exception as e:
                stats['failed_count'] += 1
                stats['details'].append({
                    'gap': gap,
                    'method': 'extend_boundary',
                    'success': False,
                    'error': str(e)
                })
                logger.warning(f"边界扩展修复失败: {e}")

        return geometries, stats

    def visualize_gaps(self, gaps: List[Dict], output_file: Optional[str] = None):
        """可视化缝隙"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import Polygon as MplPolygon
            from matplotlib.collections import PatchCollection

            fig, ax = plt.subplots(1, 1, figsize=(12, 8))

            # 绘制几何体
            patches = []
            colors = []

            for i, geom in enumerate(self.geometries):
                if geom is not None and not geom.is_empty:
                    if geom.geom_type == 'Polygon':
                        coords = list(geom.exterior.coords)
                        patch = MplPolygon(coords, alpha=0.7)
                        patches.append(patch)
                        colors.append('lightblue')
                    elif geom.geom_type == 'MultiPolygon':
                        for poly in geom.geoms:
                            coords = list(poly.exterior.coords)
                            patch = MplPolygon(coords, alpha=0.7)
                            patches.append(patch)
                            colors.append('lightblue')

            # 添加几何体
            collection = PatchCollection(patches, facecolors=colors, edgecolors='black', linewidths=0.5)
            ax.add_collection(collection)

            # 绘制缝隙
            for gap in gaps:
                if gap.get('gap_geometry'):
                    gap_line = gap['gap_geometry']
                    if gap_line and not gap_line.is_empty:
                        x, y = gap_line.xy
                        ax.plot(x, y, 'r-', linewidth=3, alpha=0.8, label='缝隙' if gap == gaps[0] else "")

            # 设置图形属性
            ax.set_aspect('equal')
            ax.set_title(f'面缝隙检测结果 (发现 {len(gaps)} 个缝隙)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                logger.info(f"缝隙可视化结果已保存到: {output_file}")

            plt.show()

        except ImportError:
            logger.warning("matplotlib未安装，无法进行可视化")
        except Exception as e:
            logger.error(f"可视化失败: {e}")


def convert_geometry_types(gdf):
    """转换几何类型以解决兼容性问题"""
    try:
        # 检查几何类型
        geom_types = gdf.geometry.geom_type.unique()
        logger.info(f"检测到几何类型: {geom_types}")

        # 转换MULTIPOLYGON为POLYGON
        def convert_multipolygon(geom):
            if geom is None or geom.is_empty:
                return geom
            if geom.geom_type == 'MultiPolygon':
                # 选择最大的多边形
                if len(geom.geoms) > 0:
                    largest = max(geom.geoms, key=lambda g: g.area)
                    logger.debug(f"转换MultiPolygon为Polygon，选择最大多边形，面积: {largest.area}")
                    return largest
            return geom

        # 应用转换
        original_count = len(gdf)
        gdf.geometry = gdf.geometry.apply(convert_multipolygon)

        # 移除转换后为空的几何体
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]

        converted_count = len(gdf)
        if original_count != converted_count:
            logger.info(f"几何类型转换完成: 原始{original_count}个，转换后{converted_count}个")

        return gdf

    except Exception as e:
        logger.error(f"几何类型转换失败: {e}")
        return gdf

def check_and_repair_gaps_in_file(file_path: str, tolerance: float = 0.001,
                                 repair_method: str = 'buffer_merge',
                                 output_path: Optional[str] = None) -> Dict:
    """
    检查并修复文件中的面缝隙

    Args:
        file_path: 输入文件路径
        tolerance: 容差参数
        repair_method: 修复方法
        output_path: 输出文件路径，如果为None则覆盖原文件

    Returns:
        处理结果统计
    """
    try:
        logger.info(f"开始处理文件: {file_path}")

        # 读取文件
        try:
            gdf = gpd.read_file(file_path)
            if gdf.empty:
                return {'success': False, 'error': '文件为空'}
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return {'success': False, 'error': f'读取文件失败: {str(e)}'}

        # 转换几何类型以解决兼容性问题
        gdf = convert_geometry_types(gdf)

        # 创建拓扑检查器
        checker = ImprovedTopologyChecker(tolerance)

        # 检测缝隙
        geometries = gdf.geometry.tolist()
        gaps = checker.check_topology_gaps_optimized(geometries, tolerance)

        result = {
            'file_path': file_path,
            'total_features': len(geometries),
            'gaps_found': len(gaps),
            'tolerance': tolerance,
            'repair_method': repair_method
        }

        if gaps:
            logger.info(f"发现 {len(gaps)} 个缝隙，开始修复")

            # 修复缝隙
            repaired_geometries, repair_stats = checker.repair_topology_gaps(
                geometries, gaps, repair_method
            )

            # 更新GeoDataFrame
            gdf.geometry = repaired_geometries

            # 移除已合并的几何体
            gdf = gdf[gdf.geometry.notna()]

            result.update(repair_stats)
            result['success'] = True

            # 保存文件
            output_file = output_path or file_path
            gdf.to_file(output_file)
            logger.info(f"修复后的文件已保存到: {output_file}")

        else:
            logger.info("未发现缝隙")
            result['success'] = True
            result['repaired_count'] = 0
            result['failed_count'] = 0

        return result

    except Exception as e:
        error_msg = f"处理文件失败: {str(e)}"
        logger.error(error_msg)

        # 提供更详细的错误信息
        if "MULTIPOLYGON" in str(e) and "POLYGON" in str(e):
            error_msg += "\n建议: 文件包含MULTIPOLYGON几何体，但Shapefile定义为POLYGON类型。已自动转换几何类型。"
        elif "encoding" in str(e).lower():
            error_msg += "\n建议: 文件编码问题，请检查文件编码格式。"
        elif "permission" in str(e).lower():
            error_msg += "\n建议: 文件权限问题，请检查文件是否被其他程序占用。"

        return {'success': False, 'error': error_msg}


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 创建测试几何体
    test_geometries = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1.001, 0), (2, 0), (2, 1), (1.001, 1)]),  # 有缝隙
        Polygon([(0, 1.001), (1, 1.001), (1, 2), (0, 2)]),  # 有缝隙
    ]

    # 测试改进的检测算法
    checker = ImprovedTopologyChecker(tolerance=0.001)
    gaps = checker.check_topology_gaps_optimized(test_geometries)

    print(f"发现 {len(gaps)} 个缝隙")
    for gap in gaps:
        print(f"缝隙: 要素{gap['feature1']}和{gap['feature2']}, 距离: {gap['distance']:.6f}")

    # 测试修复功能
    if gaps:
        repaired_geometries, stats = checker.repair_topology_gaps(test_geometries, gaps, 'buffer_merge')
        print(f"修复统计: {stats}")
