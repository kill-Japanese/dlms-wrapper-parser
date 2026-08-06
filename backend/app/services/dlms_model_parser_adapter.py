"""
DLMS Model Parser 适配器

封装 DLMS 数模解析能力，提供统一的调用接口。
优先使用项目内打包的 parse_dlms_model.py，
如果不可用则尝试外部 skill 路径，都不可用则返回 None。
"""
import sys
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 1. 项目内打包的解析器路径（优先使用，确保 Render 等部署环境可用）
LOCAL_PARSER_PATH = os.path.join(os.path.dirname(__file__), "..", "utils")

# 2. 外部 dlms-model-parser skill 路径（TRAE 环境可用）
EXTERNAL_PARSER_PATH = "/data/user/skills/dlms-model-parser/scripts"

_parse_excel_func = None
_import_error = None


def _ensure_parser_loaded() -> bool:
    """
    懒加载解析函数（优先本地，其次外部 skill）

    Returns:
        bool: 是否成功加载
    """
    global _parse_excel_func, _import_error

    if _parse_excel_func is not None:
        return True

    if _import_error is not None:
        return False

    # 按优先级尝试加载
    search_paths = [LOCAL_PARSER_PATH, EXTERNAL_PARSER_PATH]
    
    for parser_path in search_paths:
        if not os.path.exists(os.path.join(parser_path, "parse_dlms_model.py")):
            continue
            
        try:
            if parser_path not in sys.path:
                sys.path.insert(0, parser_path)

            from parse_dlms_model import parse_excel
            _parse_excel_func = parse_excel
            logger.info(f"DLMS 数模解析器加载成功 (路径: {parser_path})")
            return True
        except Exception as e:
            logger.warning(f"解析器加载失败 ({parser_path}): {e}")
            continue

    _import_error = "所有解析器路径均不可用"
    logger.warning(f"DLMS 数模解析器不可用: {_import_error}")
    return False


def is_parser_available() -> bool:
    """检查解析器是否可用"""
    return _ensure_parser_loaded()


def parse_object_model_sheet(file_path: str, sheet_name: str) -> Optional[Dict[str, Any]]:
    """
    解析 object model sheet

    Args:
        file_path: Excel 文件路径
        sheet_name: sheet 名称

    Returns:
        解析结果字典，失败返回 None
    """
    if not _ensure_parser_loaded():
        return None

    try:
        result = _parse_excel_func(file_path, sheet_name=sheet_name)
        return result
    except Exception as e:
        logger.warning(f"数模解析失败: {e}")
        return None
