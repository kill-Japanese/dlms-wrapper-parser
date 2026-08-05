"""
DLMS Model Parser 适配器

封装 dlms-model-parser skill 的解析能力，提供统一的调用接口。
如果 skill 不可用，则返回 None，由调用方回退到原有解析逻辑。
"""
import sys
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# dlms-model-parser skill 脚本路径
PARSER_SCRIPT_PATH = "/data/user/skills/dlms-model-parser/scripts"

_parse_excel_func = None
_import_error = None


def _ensure_parser_loaded() -> bool:
    """
    懒加载 dlms-model-parser 解析函数

    Returns:
        bool: 是否成功加载
    """
    global _parse_excel_func, _import_error

    if _parse_excel_func is not None:
        return True

    if _import_error is not None:
        return False

    try:
        # 将脚本目录添加到 Python 路径
        if PARSER_SCRIPT_PATH not in sys.path:
            sys.path.insert(0, PARSER_SCRIPT_PATH)

        from parse_dlms_model import parse_excel
        _parse_excel_func = parse_excel
        logger.info("dlms-model-parser 加载成功")
        return True
    except Exception as e:
        _import_error = str(e)
        logger.warning(f"dlms-model-parser 加载失败: {e}")
        return False


def is_parser_available() -> bool:
    """检查 dlms-model-parser 是否可用"""
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
        logger.warning(f"dlms-model-parser 解析失败: {e}")
        return None
