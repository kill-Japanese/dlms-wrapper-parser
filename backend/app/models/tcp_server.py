"""
TCP服务器相关模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class TcpConnection(BaseModel):
    """TCP连接模型"""

    connection_id: str = Field(description="连接唯一标识")
    client_ip: str = Field(description="客户端IP地址")
    client_port: int = Field(description="客户端端口")
    device_id: Optional[str] = Field(default=None, description="设备ID（如果已识别）")
    connected_at: str = Field(description="连接时间")
    status: str = Field(default="connected", description="连接状态 (connected/disconnected)")
    frames_received: int = Field(default=0, description="收到的帧数")
    last_frame_time: Optional[str] = Field(default=None, description="最后一帧时间")


class TcpServerStatus(BaseModel):
    """TCP服务器状态"""

    running: bool = Field(description="是否运行中")
    host: str = Field(description="监听地址")
    port: int = Field(description="监听端口")
    client_count: int = Field(default=0, description="客户端连接数")
    total_frames: int = Field(default=0, description="总接收帧数")
    started_at: Optional[str] = Field(default=None, description="启动时间")


class TcpSendRequest(BaseModel):
    """TCP发送数据请求"""

    connection_id: Optional[str] = Field(default=None, description="目标连接ID（不填则广播）")
    hex_data: str = Field(description="要发送的十六进制数据")
