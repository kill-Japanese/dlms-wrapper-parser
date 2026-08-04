"""
TCP流路由 - 管理TCP服务器和设备连接
"""
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.tcp_server import (
    TcpServerStatus,
    TcpConnection,
    TcpSendRequest,
)
from app.services.tcp_server import tcp_server
from app.utils.hex_utils import hex_to_bytes


router = APIRouter(prefix="/api/tcp", tags=["TCP Stream"])


@router.get("/status", response_model=TcpServerStatus, summary="获取TCP服务器状态")
async def get_tcp_status():
    """
    获取TCP服务器运行状态

    返回服务器是否运行、监听地址端口、客户端数量等信息。
    """
    try:
        status = tcp_server.get_status()
        return TcpServerStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {e}")


@router.post("/start", response_model=dict, summary="启动TCP服务器")
async def start_tcp_server():
    """
    启动TCP服务器，开始监听设备连接。

    默认监听端口: 4059
    """
    if tcp_server.running:
        raise HTTPException(status_code=400, detail="TCP服务器已在运行")

    result = await tcp_server.start()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/stop", response_model=dict, summary="停止TCP服务器")
async def stop_tcp_server():
    """
    停止TCP服务器，断开所有客户端连接。
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="TCP服务器未运行")

    result = await tcp_server.stop()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/clients", response_model=List[TcpConnection], summary="获取设备连接列表")
async def get_clients():
    """
    获取所有已连接的TCP客户端（设备）列表。
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="TCP服务器未运行")

    try:
        connections = tcp_server.get_connections()
        return connections
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取客户端列表失败: {e}")


@router.get("/clients/{connection_id}", response_model=TcpConnection, summary="获取指定连接信息")
async def get_client(connection_id: str):
    """
    获取指定连接的详细信息。

    - **connection_id**: 连接ID
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="TCP服务器未运行")

    conn = tcp_server.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"连接 {connection_id} 不存在")
    return conn


@router.post("/send", response_model=dict, summary="发送数据")
async def send_data(request: TcpSendRequest):
    """
    向设备发送十六进制数据

    - **connection_id**: 目标连接ID（不填则向所有设备广播）
    - **hex_data**: 要发送的十六进制数据
    """
    if not tcp_server.running:
        raise HTTPException(status_code=400, detail="TCP服务器未运行")

    try:
        data = hex_to_bytes(request.hex_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"十六进制数据格式错误: {e}")

    if not data:
        raise HTTPException(status_code=400, detail="发送数据不能为空")

    try:
        if request.connection_id:
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
