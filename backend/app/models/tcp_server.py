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
    system_title: Optional[str] = Field(default=None, description="设备System Title (8字节十六进制)")
    device_name: Optional[str] = Field(default=None, description="设备名称（可编辑）")
    device_id: Optional[str] = Field(default=None, description="设备ID（如果已识别）")
    connected_at: str = Field(description="连接时间")
    last_seen: Optional[str] = Field(default=None, description="最后活动时间")
    status: str = Field(default="connected", description="连接状态 (connected/disconnected)")
    frames_received: int = Field(default=0, description="收到的帧数")
    last_frame_time: Optional[str] = Field(default=None, description="最后一帧时间")


class TcpServerStatus(BaseModel):
    """TCP服务器状态"""

    running: bool = Field(description="是否运行中")
    host: str = Field(description="监听地址")
    port: int = Field(description="监听端口")
    protocol: str = Field(default="tcp", description="协议类型: tcp/udp")
    client_count: int = Field(default=0, description="客户端连接数")
    total_frames: int = Field(default=0, description="总接收帧数")
    started_at: Optional[str] = Field(default=None, description="启动时间")


class TcpServerConfig(BaseModel):
    """TCP服务器配置"""

    port: int = Field(default=4059, description="监听端口")
    protocol: str = Field(default="tcp", description="协议类型: tcp/udp")
    enabled: bool = Field(default=True, description="是否启用")
    auto_start: bool = Field(default=False, description="是否自动启动")


class TcpSendRequest(BaseModel):
    """TCP发送数据请求"""

    connection_id: Optional[str] = Field(default=None, description="目标连接ID（不填则广播）")
    system_title: Optional[str] = Field(default=None, description="目标设备System Title")
    hex_data: str = Field(description="要发送的十六进制数据")


class DeviceRenameRequest(BaseModel):
    """设备重命名请求"""

    device_name: str = Field(description="新的设备名称")
