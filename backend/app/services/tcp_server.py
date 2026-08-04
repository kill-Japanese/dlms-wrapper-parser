"""
TCP服务器模块

使用asyncio实现异步TCP服务器，处理DLMS设备的连接和数据收发。

功能:
- 监听指定端口，接受设备连接
- 处理粘包/拆包（基于Wrapper帧头的长度字段）
- 管理连接池
- 收到完整帧后调用协议栈解析
- 通过WebSocket向前端推送解析结果
- 支持向设备发送数据
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, List

from app.config import settings
from app.models.tcp_server import TcpConnection
from app.services.log_manager import log_manager


class TcpServer:
    """
    异步TCP服务器

    使用 asyncio.start_server 实现。
    """

    def __init__(self):
        self.running: bool = False
        self.host: str = settings.TCP_HOST
        self.port: int = settings.TCP_PORT
        self._server: Optional[asyncio.Server] = None

        # 连接池: connection_id -> (reader, writer, connection_info)
        self.clients: Dict[str, dict] = {}

        # WebSocket管理器引用（用于广播解析结果）
        self._ws_manager = None

        # 统计
        self._total_frames: int = 0
        self._started_at: Optional[str] = None

    def set_ws_manager(self, ws_manager):
        """设置WebSocket管理器，用于广播解析结果"""
        self._ws_manager = ws_manager

    async def start(self) -> dict:
        """
        启动TCP服务器

        Returns:
            启动结果
        """
        if self.running:
            return {"success": False, "message": "TCP服务器已在运行"}

        try:
            self._server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
            )
            self.running = True
            self._started_at = datetime.now().isoformat()
            log_manager.info("tcp", "tcp_server",
                           f"TCP服务器启动成功，监听 {self.host}:{self.port}")
            return {
                "success": True,
                "message": f"TCP服务器已启动，监听 {self.host}:{self.port}",
                "host": self.host,
                "port": self.port,
            }
        except Exception as e:
            log_manager.error("tcp", "tcp_server", f"TCP服务器启动失败: {e}")
            return {"success": False, "message": f"启动失败: {e}"}

    async def stop(self) -> dict:
        """
        停止TCP服务器

        Returns:
            停止结果
        """
        if not self.running:
            return {"success": False, "message": "TCP服务器未运行"}

        try:
            # 关闭所有客户端连接
            for conn_id, client in list(self.clients.items()):
                try:
                    client["writer"].close()
                    await client["writer"].wait_closed()
                except Exception:
                    pass
            self.clients.clear()

            # 关闭服务器
            if self._server:
                self._server.close()
                await self._server.wait_closed()

            self.running = False
            self._started_at = None
            log_manager.info("tcp", "tcp_server", "TCP服务器已停止")
            return {"success": True, "message": "TCP服务器已停止"}
        except Exception as e:
            log_manager.error("tcp", "tcp_server", f"TCP服务器停止失败: {e}")
            return {"success": False, "message": f"停止失败: {e}"}

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理客户端连接

        Args:
            reader: 读流
            writer: 写流
        """
        # 获取客户端地址
        addr = writer.get_extra_info("peername")
        if addr:
            client_ip, client_port = addr[0], addr[1]
        else:
            client_ip, client_port = "unknown", 0

        conn_id = str(uuid.uuid4())[:8]

        # 注册连接
        conn_info = TcpConnection(
            connection_id=conn_id,
            client_ip=client_ip,
            client_port=client_port,
            device_id=None,
            connected_at=datetime.now().isoformat(),
            status="connected",
        )

        self.clients[conn_id] = {
            "reader": reader,
            "writer": writer,
            "info": conn_info,
            "buffer": b"",  # 接收缓冲区，用于粘包处理
        }

        log_manager.info("tcp", "tcp_client",
                        f"新连接: {client_ip}:{client_port} (conn_id={conn_id})")

        try:
            await self._read_loop(conn_id, reader)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_manager.error("tcp", "tcp_client",
                            f"连接异常 {conn_id}: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(conn_id)
            log_manager.info("tcp", "tcp_client",
                           f"连接断开: {client_ip}:{client_port} (conn_id={conn_id})")

    async def _read_loop(self, conn_id: str, reader: asyncio.StreamReader):
        """
        读取循环

        Args:
            conn_id: 连接ID
            reader: 读流
        """
        client = self.clients.get(conn_id)
        if not client:
            return

        buffer = client["buffer"]

        while True:
            try:
                data = await reader.read(settings.TCP_BUFFER_SIZE)
                if not data:
                    # 连接关闭
                    break

                buffer += data
                log_manager.debug("tcp", "tcp_client",
                                f"收到 {len(data)} 字节，缓冲区 {len(buffer)} 字节")

                # 处理粘包 - 尝试从缓冲区中提取完整帧
                while len(buffer) >= 8:  # Wrapper头至少8字节
                    # 检查是否是Wrapper帧
                    # Wrapper头格式: version(2) + src(2) + dst(2) + length(2)
                    import struct
                    try:
                        version, src_wport, dst_wport, data_length = struct.unpack(
                            ">HHHH", buffer[:8]
                        )

                        # 检查版本号是否合理
                        if version != 1:
                            # 可能不是Wrapper帧，尝试其他方式处理
                            # 暂时直接丢弃第一个字节，继续寻找
                            buffer = buffer[1:]
                            continue

                        total_frame_length = 8 + data_length
                        if len(buffer) >= total_frame_length:
                            # 提取完整帧
                            frame_data = buffer[:total_frame_length]
                            buffer = buffer[total_frame_length:]

                            # 处理帧
                            await self._process_frame(conn_id, frame_data)
                        else:
                            # 数据不足，等待更多数据
                            break
                    except Exception as e:
                        log_manager.error("tcp", "frame_parse",
                                        f"帧解析异常: {e}")
                        buffer = buffer[1:]  # 跳过一个字节继续尝试

                # 更新缓冲区
                client["buffer"] = buffer

            except asyncio.CancelledError:
                break
            except ConnectionError:
                break
            except Exception as e:
                log_manager.error("tcp", "read_loop", f"读取异常: {e}")
                break

    async def _process_frame(self, conn_id: str, frame_data: bytes):
        """
        处理收到的完整帧

        Args:
            conn_id: 连接ID
            frame_data: 帧数据
        """
        self._total_frames += 1

        # 更新连接信息
        client = self.clients.get(conn_id)
        if client:
            client["info"].frames_received += 1
            client["info"].last_frame_time = datetime.now().isoformat()

        from app.utils.hex_utils import bytes_to_hex
        from app.services.dlms_stack import parse_frame

        # 调用协议栈解析
        hex_data = bytes_to_hex(frame_data)
        parse_result = parse_frame(hex_data)

        log_manager.info("tcp", "frame",
                        f"收到帧 {parse_result.frame_id}: {len(frame_data)} 字节")

        # 通过WebSocket广播解析结果
        if self._ws_manager:
            message = {
                "type": "frame_received",
                "connection_id": conn_id,
                "timestamp": datetime.now().isoformat(),
                "parse_result": parse_result.model_dump(),
            }
            asyncio.create_task(self._ws_manager.broadcast(message))

    async def _cleanup_connection(self, conn_id: str):
        """
        清理连接

        Args:
            conn_id: 连接ID
        """
        client = self.clients.pop(conn_id, None)
        if client:
            try:
                client["writer"].close()
                await client["writer"].wait_closed()
            except Exception:
                pass

    async def send_data(self, connection_id: str, data: bytes) -> dict:
        """
        向指定连接发送数据

        Args:
            connection_id: 连接ID
            data: 要发送的数据

        Returns:
            发送结果
        """
        client = self.clients.get(connection_id)
        if not client:
            return {"success": False, "message": f"连接 {connection_id} 不存在"}

        try:
            client["writer"].write(data)
            await client["writer"].drain()
            log_manager.info("tcp", "send",
                           f"向 {connection_id} 发送 {len(data)} 字节")
            return {"success": True, "message": f"已发送 {len(data)} 字节", "bytes_sent": len(data)}
        except Exception as e:
            log_manager.error("tcp", "send", f"发送失败: {e}")
            return {"success": False, "message": f"发送失败: {e}"}

    async def broadcast_data(self, data: bytes) -> dict:
        """
        向所有连接广播数据

        Args:
            data: 要发送的数据

        Returns:
            广播结果
        """
        count = 0
        for conn_id in list(self.clients.keys()):
            result = await self.send_data(conn_id, data)
            if result["success"]:
                count += 1
        return {"success": True, "message": f"已广播到 {count} 个客户端", "clients": count}

    def get_status(self) -> dict:
        """获取服务器状态"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "client_count": len(self.clients),
            "total_frames": self._total_frames,
            "started_at": self._started_at,
        }

    def get_connections(self) -> List[TcpConnection]:
        """获取所有连接信息"""
        return [client["info"] for client in self.clients.values()]

    def get_connection(self, conn_id: str) -> Optional[TcpConnection]:
        """获取指定连接信息"""
        client = self.clients.get(conn_id)
        if client:
            return client["info"]
        return None


# 全局TCP服务器实例
tcp_server = TcpServer()
