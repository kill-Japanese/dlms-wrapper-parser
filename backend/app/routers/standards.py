"""
标准库 API 路由

提供 DLMS/COSEM 标准定义的查询接口：
- Class 列表和详情
- 单位编码表
- APDU 规范
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from ..services.cosem_standards import (
    get_standards_manager,
    DLMS_UNIT_CODES,
    get_unit_info,
)

router = APIRouter(prefix="/api/standards", tags=["standards"])


@router.get("/classes")
def list_classes() -> List[dict]:
    """获取所有可用的标准 Class 列表"""
    manager = get_standards_manager()
    return manager.list_available_classes()


@router.get("/class/{class_id}")
def get_class_versions(class_id: int) -> Dict[str, Any]:
    """获取指定 Class 的所有可用版本"""
    manager = get_standards_manager()
    versions = manager.list_class_versions(class_id)
    if not versions:
        raise HTTPException(status_code=404, detail=f"Class {class_id} not found")
    return {
        "class_id": class_id,
        "class_name": manager.get_class_name(class_id),
        "versions": versions,
        "latest_version": versions[-1] if versions else None,
    }


@router.get("/class/{class_id}/{version}")
def get_class_definition(class_id: int, version: int) -> Dict[str, Any]:
    """获取指定 Class 版本的完整定义"""
    manager = get_standards_manager()
    class_def = manager.load_class_definition(class_id, version)
    if not class_def:
        raise HTTPException(
            status_code=404,
            detail=f"Class {class_id} v{version} not found"
        )
    return class_def


@router.get("/class/{class_id}/{version}/attribute/{attribute_id}")
def get_attribute_definition(class_id: int, version: int, attribute_id: int) -> Dict[str, Any]:
    """获取指定属性的定义"""
    manager = get_standards_manager()
    attr_def = manager.get_attribute_definition(class_id, version, attribute_id)
    if not attr_def:
        raise HTTPException(
            status_code=404,
            detail=f"Attribute {attribute_id} not found for Class {class_id} v{version}"
        )
    return attr_def


@router.get("/class/{class_id}/{version}/method/{method_id}")
def get_method_definition(class_id: int, version: int, method_id: int) -> Dict[str, Any]:
    """获取指定方法的定义"""
    manager = get_standards_manager()
    method_def = manager.get_method_definition(class_id, version, method_id)
    if not method_def:
        raise HTTPException(
            status_code=404,
            detail=f"Method {method_id} not found for Class {class_id} v{version}"
        )
    return method_def


@router.get("/units")
def list_units(category: str = None) -> List[dict]:
    """
    获取单位编码表
    
    Args:
        category: 按分类过滤（SI / non-SI / reserved / other）
    """
    if category:
        units = [
            info.to_dict()
            for info in DLMS_UNIT_CODES.values()
            if info.category == category
        ]
    else:
        units = [info.to_dict() for info in DLMS_UNIT_CODES.values()]
    return units


@router.get("/units/{code}")
def get_unit(code: int) -> Dict[str, Any]:
    """获取指定编码的单位信息"""
    info = get_unit_info(code)
    if not info:
        raise HTTPException(status_code=404, detail=f"Unit code {code} not found")
    return info.to_dict()


@router.get("/class/{class_id}/{version}/element-structure/{attribute_id}")
def get_element_structure(class_id: int, version: int, attribute_id: int) -> Dict[str, Any]:
    """
    获取复合属性的 element_structure（数组元素结构定义）
    
    适用于 array 类型的属性，如：
    - Profile Generic 的 capture_objects (attr 3)
    - Push Setup 的 push_object_list (attr 2)
    """
    manager = get_standards_manager()
    structure = manager.get_element_structure(class_id, version, attribute_id)
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail=f"Element structure not found for Class {class_id} v{version} attr {attribute_id}"
        )
    return {
        "class_id": class_id,
        "version": version,
        "attribute_id": attribute_id,
        "element_structure": structure,
    }
