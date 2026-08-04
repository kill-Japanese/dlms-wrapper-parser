"""
TCP流路由 - 管理TCP/UDP服务器和设备连接
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List

from app.models.tcp_server import (
    TcpServerStatus,
    TcpConnection,
    TcpSendRequest,
    TcpServerConfig,
    DeviceRenameRequest,
)
from app.services.tcp_server import tcp_server
from app.utils.hex_utils import hex_to_bytes


router = APIRouter(prefix="/api/tcp", tags=["TCP Stream"])


@router.get("/status", response_model=TcpServerStatus, summary="获取TCP服务器状态")
async def get_tcp_status():
    """
    获取TCP/UDP服务器运行状态

    返回服务器是否运行、监听地址端口、客户端数量等信息。
    """
    try:
        status = tcp_server.get_status()
        return TcpServerStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {e}")


@router.get("/config", summary="获取TCP服务器配置")
async def get_tcp_config():
    """
    获取TCP/UDP服务器配置（端口、协议类型、自动启动等）。
    """
    try:
        config = tcp_server.get_config()
        return {
            "success": True,
            "config": config,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e}")


@router.put("/config", summary="更新TCP服务器配置")
async def update_tcp_config(config: TcpServerConfig = Body(...)):
    """
    更新TCP/UDP服务器配置。

    配置变更需要重启服务器生效。
    """
    try:
        # 验证端口
        if config.port < 1 or config.port > 65535:
            raise HTTPException(status_code=400, detail="端口号必须在 1-65535 之间")

        # 验证协议
        if config.protocol not in ("tcp", "udp"):
            raise HTTPException(status_code=400, detail="协议类型必须是 tcp 或 udp")

        tcp_server.set_config(
            port=config.port,
            protocol=config.protocol,
            auto_start=config.auto_start,
        )

        return {
            "success": True,
            "message": "配置已更新，重启服务器后生效",
            "config": tcp_server.get_config(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")


@router.post("/start", response_model=dict, summary="启动TCP服务器")
async def start_tcp_server():
    """
    启动TCP/UDP服务器，开始监听设备连接。

    默认监听端口: 4059
    """
    if tcp_server.running:
        raise HTTPException(status_code=400, detail="服务器已在运行")

    result = await tcp_server.start()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/stop", response_model=dict, summary="停止TCP服务器")
async def stop_tcp_server():
    """
    停止TCP/UDP服务器，断开所有客户端连接。
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="服务器未运行")

    result = await tcp_server.stop()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/restart", response_model=dict, summary="重启TCP服务器")
async def restart_tcp_server():
    """
    重启TCP/UDP服务器以应用新配置。
    """
    result = await tcp_server.restart()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/clients", summary="获取设备连接列表")
async def get_clients():
    """
    获取所有已连接的TCP/UDP客户端（设备）列表。

    返回包含 system_title、ip、port、连接时间等信息。
    """
    try:
        connections = tcp_server.get_connections()
        return {
            "success": True,
            "devices": [conn.model_dump() for conn in connections],
            "total": len(connections),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取客户端列表失败: {e}")


@router.get("/clients/{connection_id}", response_model=TcpConnection, summary="获取指定连接信息")
async def get_client(connection_id: str):
    """
    获取指定连接的详细信息。

    - **connection_id**: 连接ID
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="服务器未运行")

    conn = tcp_server.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"连接 {connection_id} 不存在")
    return conn


@router.get("/device/{system_title}", summary="根据System Title获取设备信息")
async def get_device_by_system_title(system_title: str):
    """
    根据设备的 System Title 获取设备详细信息。

    - **system_title**: 设备System Title (8字节十六进制)
    """
    try:
        device = tcp_server.get_device_by_system_title(system_title)
        if not device:
            raise HTTPException(status_code=404, detail=f"未找到 System Title 为 {system_title} 的设备")
        return {
            "success": True,
            "device": device.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备信息失败: {e}")


@router.put("/device/{system_title}/name", summary="重命名设备")
async def rename_device(system_title: str, request: DeviceRenameRequest):
    """
    修改设备的显示名称。

    - **system_title**: 设备System Title
    - **device_name**: 新的设备名称
    """
    try:
        success = tcp_server.rename_device(system_title, request.device_name)
        return {
            "success": True,
            "message": "设备名称已更新" if success else "设备未连接，名称已保存",
            "system_title": system_title,
            "device_name": request.device_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名设备失败: {e}")


@router.post("/send", response_model=dict, summary="发送数据")
async def send_data(request: TcpSendRequest):
    """
    向设备发送十六进制数据

    - **connection_id**: 目标连接ID（不填则向所有设备广播）
    - **system_title**: 目标设备System Title（优先级高于connection_id）
    - **hex_data**: 要发送的十六进制数据
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="服务器未运行")

    try:
        data = hex_to_bytes(request.hex_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"十六进制数据格式错误: {e}")

    if not data:
        raise HTTPException(status_code=400, detail="发送数据不能为空")

    try:
        if request.system_title:
            # 按 System Title 发送
            result = await tcp_server.send_to_device(request.system_title, data)
        elif request.connection_id:
            # 发送到指定连接
            result = await tcp_server.send_data(request.connection_id, data)
        else:
            # 广播到所有连接
            result = await tcp_server.broadcast_data(data)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送失败: {e}")


@router.post("/send-to-device", summary="按System Title发送数据")
async def send_to_device(request: TcpSendRequest):
    """
    按设备 System Title 发送十六进制数据。

    - **system_title**: 目标设备System Title
    - **hex_data**: 要发送的十六进制数据
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="服务器未运行")

    if not request.system_title:
        raise HTTPException(status_code=400, detail="缺少 system_title 参数")

    try:
        data = hex_to_bytes(request.hex_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"十六进制数据格式错误: {e}")

    if not data:
        raise HTTPException(status_code=400, detail="发送数据不能为空")

    try:
        result = await tcp_server.send_to_device(request.system_title, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送失败: {e}")
