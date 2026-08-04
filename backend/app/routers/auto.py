"""
自动处理路由 - 管理DataNotification自动处理配置和触发
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List

from app.services.auto_handler import auto_handler
from app.services.tcp_server import tcp_server


router = APIRouter(prefix="/api/auto", tags=["AutoHandler"])


# ---------- 请求/响应模型 ----------

class PullOperationItem(BaseModel):
    """Pull操作项"""
    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    attribute_id: int = Field(default=2, description="属性ID")
    description: str = Field(default="", description="描述")


class AutoHandlerConfigUpdate(BaseModel):
    """自动处理配置更新"""
    enabled: Optional[bool] = Field(default=None, description="是否启用自动处理")
    send_confirm: Optional[bool] = Field(default=None, description="是否发送Confirm")
    pull_operations: Optional[List[PullOperationItem]] = Field(default=None, description="Pull操作列表")
    pull_timeout: Optional[float] = Field(default=None, description="Pull超时时间(秒)")
    operation_order: Optional[str] = Field(
        default=None,
        description="操作顺序: pull_then_confirm / confirm_then_pull / pull_only / confirm_only"
    )


class AutoTriggerRequest(BaseModel):
    """手动触发请求"""
    connection_id: str = Field(description="TCP连接ID")
    device_id: Optional[str] = Field(default=None, description="设备ID (可选)")


# ---------- 路由 ----------

@router.get("/config", summary="获取自动处理配置")
async def get_config(
    device_id: Optional[str] = Query(None, description="设备ID，不传则返回默认配置"),
):
    """
    获取自动处理配置

    - **device_id**: 可选，按设备ID获取特定配置
    """
    try:
        config = auto_handler.get_config(device_id)
        return {
            "success": True,
            "device_id": device_id,
            "config": config,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e}")


@router.put("/config", summary="更新自动处理配置")
async def update_config(
    config_update: AutoHandlerConfigUpdate,
    device_id: Optional[str] = Query(None, description="设备ID，不传则更新默认配置"),
):
    """
    更新自动处理配置

    - **device_id**: 可选，按设备ID更新特定配置
    - 只更新提供的字段，未提供的字段保持不变
    """
    try:
        # 获取当前配置作为基础
        current_config = auto_handler.get_config(device_id)

        # 合并更新
        update_data = config_update.model_dump(exclude_none=True)
        merged_config = {**current_config, **update_data}

        # 应用更新
        result = auto_handler.set_config(merged_config, device_id)

        return {
            "success": True,
            "device_id": device_id,
            "config": result,
            "message": "配置已更新",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")


@router.post("/trigger", summary="手动触发自动处理流程")
async def trigger_auto_flow(
    request: AutoTriggerRequest,
):
    """
    手动触发自动处理流程（用于测试）

    即使配置中enabled为false，手动触发也会执行。
    """
    try:
        # 检查连接是否存在
        conn = tcp_server.get_connection(request.connection_id)
        if not conn:
            raise HTTPException(status_code=404, detail=f"连接 {request.connection_id} 不存在")

        # 执行自动处理
        result = await auto_handler.trigger_manual(
            connection_id=request.connection_id,
            device_id=request.device_id,
        )

        return {
            "success": True,
            "triggered": True,
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {e}")


@router.get("/devices", summary="获取所有设备配置列表")
async def list_device_configs():
    """获取所有设备的自动处理配置"""
    try:
        configs = auto_handler.list_device_configs()
        return {
            "success": True,
            "devices": configs,
            "total": len(configs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备配置失败: {e}")


@router.delete("/config/{device_id}", summary="删除设备配置")
async def delete_device_config(device_id: str):
    """
    删除指定设备的自动处理配置

    删除后该设备将使用默认配置。
    """
    try:
        deleted = auto_handler.delete_device_config(device_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"设备 {device_id} 的配置不存在")
        return {
            "success": True,
            "device_id": device_id,
            "message": "配置已删除",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {e}")


@router.get("/status", summary="自动处理状态")
async def get_auto_status():
    """获取自动处理模块的状态信息"""
    try:
        default_config = auto_handler.get_config()
        device_configs = auto_handler.list_device_configs()
        return {
            "success": True,
            "default_enabled": default_config["enabled"],
            "device_count": len(device_configs),
            "operation_order": default_config["operation_order"],
            "send_confirm": default_config["send_confirm"],
            "pull_operations_count": len(default_config["pull_operations"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {e}")
