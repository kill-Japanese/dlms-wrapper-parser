"""
Profile Capture API 路由

提供 Profile Generic capture_objects 手动配置的管理接口：
- CRUD 操作
- 导入导出
- 使用配置解析 buffer
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..services.profile_capture_store import (
    get_profile_capture_store,
    ProfileCaptureConfig,
    CaptureObject,
)

router = APIRouter(prefix="/api/profile-capture", tags=["profile-capture"])


class CaptureObjectItem(BaseModel):
    class_id: int
    instance_id: str
    attribute_id: int
    data_index: int = 0
    remark: str = ""


class ProfileCaptureSaveRequest(BaseModel):
    profile_obis: str
    profile_name: str = ""
    capture_objects: List[CaptureObjectItem]
    source: str = "manual"


class ProfileImportRequest(BaseModel):
    configs: Dict[str, Any]
    overwrite: bool = True


@router.get("/list")
def list_configs() -> List[dict]:
    """获取所有已保存的 capture_objects 配置列表"""
    store = get_profile_capture_store()
    return store.list_configs()


@router.get("/{profile_obis}")
def get_config(profile_obis: str) -> Dict[str, Any]:
    """获取指定 Profile 的配置详情"""
    store = get_profile_capture_store()
    config = store.get_config_detail(profile_obis)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No config found for profile OBIS: {profile_obis}"
        )
    return config


@router.post("/")
def save_config(request: ProfileCaptureSaveRequest) -> Dict[str, Any]:
    """保存/更新 Profile 的 capture_objects 配置"""
    store = get_profile_capture_store()
    config = store.save_config(
        profile_obis=request.profile_obis,
        capture_objects=[co.dict() for co in request.capture_objects],
        profile_name=request.profile_name,
        source=request.source,
    )
    return {
        "status": "success",
        "profile_obis": request.profile_obis,
        "capture_object_count": len(request.capture_objects),
    }


@router.delete("/{profile_obis}")
def delete_config(profile_obis: str) -> Dict[str, Any]:
    """删除指定 Profile 的配置"""
    store = get_profile_capture_store()
    success = store.delete_config(profile_obis)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No config found for profile OBIS: {profile_obis}"
        )
    return {"status": "success", "profile_obis": profile_obis}


@router.get("/capture-objects/{profile_obis}")
def get_capture_objects(profile_obis: str) -> Dict[str, Any]:
    """获取指定 Profile 的 capture_objects 列表"""
    store = get_profile_capture_store()
    cap_objs = store.get_capture_objects(profile_obis)
    if cap_objs is None:
        raise HTTPException(
            status_code=404,
            detail=f"No config found for profile OBIS: {profile_obis}"
        )
    return {
        "profile_obis": profile_obis,
        "capture_objects": cap_objs,
        "count": len(cap_objs),
    }


@router.post("/import")
def import_configs(request: ProfileImportRequest) -> Dict[str, Any]:
    """批量导入配置"""
    store = get_profile_capture_store()
    count = store.import_configs(request.configs, overwrite=request.overwrite)
    return {
        "status": "success",
        "imported_count": count,
    }


@router.get("/export/all")
def export_all_configs() -> Dict[str, Any]:
    """导出所有配置"""
    store = get_profile_capture_store()
    return store.export_configs()


@router.get("/has/{profile_obis}")
def has_config(profile_obis: str) -> Dict[str, Any]:
    """检查是否有指定 Profile 的配置"""
    store = get_profile_capture_store()
    return {
        "profile_obis": profile_obis,
        "has_config": store.has_config(profile_obis),
    }


@router.post("/resolve-buffer")
def resolve_buffer_with_capture(
    profile_obis: str,
    buffer_data: List[Any],
) -> Dict[str, Any]:
    """
    使用指定 Profile 的 capture_objects 配置解析 buffer 数据
    
    Args:
        profile_obis: Profile Generic 对象的 OBIS
        buffer_data: buffer 数据（一个条目的 structure 列表）
    
    Returns:
        解析后的字段列表
    """
    from ..services.push_data_resolver import PushDataResolver
    from ..services.cosem_standards import get_standards_manager

    store = get_profile_capture_store()
    standards_manager = get_standards_manager()

    # 直接调用 resolver 的 buffer 解析方法
    result = PushDataResolver._resolve_profile_buffer(
        buffer_data,
        class_id=7,
        obis=profile_obis,
        attribute_id=2,
        data_index=0,
        data_model=None,
        standards_manager=standards_manager,
        profile_capture_store=store,
        warnings=[],
    )

    return result
