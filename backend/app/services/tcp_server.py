"""
TCP/UDP服务器模块

使用asyncio实现异步TCP/UDP服务器，处理DLMS设备的连接和数据收发。

功能:
- 监听指定端口，接受设备连接（TCP）或接收数据报（UDP）
- 处理粘包/拆包（基于Wrapper帧头的长度字段）
- 管理连接池，按System Title索引设备
- 从首帧中解析System Title进行设备识别
- 收到完整帧后调用协议栈解析
- 通过WebSocket向前端推送解析结果
- 支持向设备发送数据
"""
import asyncio
import uuid
import struct
from datetime import datetime
from typing import Optional, Dict, List

from app.config import settings
from app.models.tcp_server import TcpConnection
from app.services.log_manager import log_manager


class TcpServer:
    """
    异步TCP/UDP服务器

    支持 TCP 和 UDP 两种协议模式。
    """

    def __init__(self):
        self.running: bool = False
        self.host: str = settings.TCP_HOST
        self.port: int = settings.TCP_PORT
        self.protocol: str = "tcp"  # tcp 或 udp
        self.auto_start: bool = False

        # TCP 服务器实例
        self._server: Optional[asyncio.Server] = None
        # UDP 传输实例
        self._udp_transport: Optional[asyncio.DatagramTransport] = None

        # 连接池: connection_id -> (reader, writer, connection_info)
        self.clients: Dict[str, dict] = {}

        # 设备索引: system_title -> connection_id
        self._device_index: Dict[str, str] = {}

        # 设备名称持久化存储: system_title -> device_name
        self._device_names: Dict[str, str] = {}

        # WebSocket管理器引用（用于广播解析结果）
        self._ws_manager = None

        # 统计
        self._total_frames: int = 0
        self._started_at: Optional[str] = None

    def set_ws_manager(self, ws_manager):
        """设置WebSocket管理器，用于广播解析结果"""
        self._ws_manager = ws_manager

    def set_config(self, port: int = None, protocol: str = None, auto_start: bool = None):
        """
        更新服务器配置（需要重启生效）

        Args:
            port: 监听端口
            protocol: 协议类型 (tcp/udp)
            auto_start: 是否自动启动
        """
        if port is not None:
            self.port = port
        if protocol is not None:
            self.protocol = protocol
        if auto_start is not None:
            self.auto_start = auto_start

    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            "port": self.port,
            "protocol": self.protocol,
            "enabled": True,
            "auto_start": self.auto_start,
        }

    async def start(self) -> dict:
        """
        启动服务器

        Returns:
            启动结果
        """
        if self.running:
            return {"success": False, "message": f"{self.protocol.upper()}服务器已在运行"}

        try:
            if self.protocol == "udp":
                await self._start_udp()
            else:
                await self._start_tcp()

            self.running = True
            self._started_at = datetime.now().isoformat()
            log_manager.info("tcp", "tcp_server",
                           f"{self.protocol.upper()}服务器启动成功，监听 {self.host}:{self.port}")
            return {
                "success": True,
                "message": f"{self.protocol.upper()}服务器已启动，监听 {self.host}:{self.port}",
                "host": self.host,
                "port": self.port,
                "protocol": self.protocol,
            }
        except Exception as e:
            log_manager.error("tcp", "tcp_server", f"服务器启动失败: {e}")
            return {"success": False, "message": f"启动失败: {e}"}

    async def _start_tcp(self):
        """启动TCP服务器"""
        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

    async def _start_udp(self):
        """启动UDP服务器"""
        loop = asyncio.get_running_loop()

        class UdpProtocol:
            def __init__(self, server):
                self.server = server

            def connection_made(self, transport):
                self.transport = transport

            def datagram_received(self, data, addr):
                asyncio.create_task(self.server._handle_udp_datagram(data, addr))

            def error_received(self, exc):
                log_manager.error("tcp", "udp_server", f"UDP错误: {exc}")

        self._udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: UdpProtocol(self),
            local_addr=(self.host, self.port)
        )

    async def stop(self) -> dict:
        """
        停止服务器

        Returns:
            停止结果
        """
        if not self.running:
            return {"success": False, "message": "服务器未运行"}

        try:
            # 关闭所有客户端连接
            for conn_id in list(self.clients.keys()):
                await self._cleanup_connection(conn_id)

            # 关闭服务器
            if self.protocol == "udp" and self._udp_transport:
                self._udp_transport.close()
                self._udp_transport = None
            elif self._server:
                self._server.close()
                await self._server.wait_closed()
                self._server = None

            self.clients.clear()
            self._device_index.clear()
            self.running = False
            self._started_at = None
            log_manager.info("tcp", "tcp_server", f"{self.protocol.upper()}服务器已停止")
            return {"success": True, "message": f"{self.protocol.upper()}服务器已停止"}
        except Exception as e:
            log_manager.error("tcp", "tcp_server", f"服务器停止失败: {e}")
            return {"success": False, "message": f"停止失败: {e}"}

    async def restart(self) -> dict:
        """重启服务器以应用新配置"""
        if self.running:
            await self.stop()
        return await self.start()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理TCP客户端连接

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
            system_title=None,
            device_name=None,
            device_id=None,
            connected_at=datetime.now().isoformat(),
            last_seen=datetime.now().isoformat(),
            status="connected",
        )

        self.clients[conn_id] = {
            "reader": reader,
            "writer": writer,
            "info": conn_info,
            "buffer": b"",  # 接收缓冲区，用于粘包处理
            "is_udp": False,
            "udp_addr": None,
        }

        log_manager.info("tcp", "tcp_client",
                        f"新连接: {client_ip}:{client_port} (conn_id={conn_id})")

        # 广播设备连接事件
        await self._broadcast_device_event("device_connected", conn_info)

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

    async def _handle_udp_datagram(self, data: bytes, addr):
        """
        处理UDP数据报

        Args:
            data: 收到的数据
            addr: 源地址 (ip, port)
        """
        client_ip, client_port = addr

        # 为UDP客户端生成虚拟连接（基于地址）
        conn_id = f"udp-{client_ip}-{client_port}"

        client = self.clients.get(conn_id)
        if not client:
            # 新的UDP客户端
            conn_info = TcpConnection(
                connection_id=conn_id,
                client_ip=client_ip,
                client_port=client_port,
                system_title=None,
                device_name=None,
                device_id=None,
                connected_at=datetime.now().isoformat(),
                last_seen=datetime.now().isoformat(),
                status="connected",
            )

            self.clients[conn_id] = {
                "reader": None,
                "writer": None,
                "info": conn_info,
                "buffer": b"",
                "is_udp": True,
                "udp_addr": addr,
            }

            log_manager.info("tcp", "udp_client",
                           f"新UDP客户端: {client_ip}:{client_port} (conn_id={conn_id})")
            await self._broadcast_device_event("device_connected", conn_info)
        else:
            # 更新最后活动时间
            client["info"].last_seen = datetime.now().isoformat()

        # 将数据加入缓冲区处理
        client = self.clients.get(conn_id)
        if client:
            buffer = client["buffer"] + data

            # 处理粘包
            while len(buffer) >= 8:
                try:
                    version, src_wport, dst_wport, data_length = struct.unpack(
                        ">HHHH", buffer[:8]
                    )

                    if version != 1:
                        buffer = buffer[1:]
                        continue

                    total_frame_length = 8 + data_length
                    if len(buffer) >= total_frame_length:
                        frame_data = buffer[:total_frame_length]
                        buffer = buffer[total_frame_length:]
                        await self._process_frame(conn_id, frame_data)
                    else:
                        break
                except Exception as e:
                    log_manager.error("tcp", "frame_parse", f"帧解析异常: {e}")
                    buffer = buffer[1:]

            client["buffer"] = buffer

    async def _read_loop(self, conn_id: str, reader: asyncio.StreamReader):
        """
        TCP读取循环

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
                    try:
                        version, src_wport, dst_wport, data_length = struct.unpack(
                            ">HHHH", buffer[:8]
                        )

                        # 检查版本号是否合理
                        if version != 1:
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

    def _extract_system_title(self, frame_data: bytes) -> Optional[str]:
        """
        从Wrapper帧中尝试提取System Title

        DLMS Wrapper 帧中，System Title 通常出现在 AARQ/AARE 的 Conformance 块中，
        或者在应用上下文引用中。这里尝试从帧数据中解析。

        简化策略：从帧数据中查找可能的System Title位置。
        在 DLMS/COSEM 中，System Title 通常是 8 字节，出现在 AARQ 的
        'calling-AP-title' 或 'called-AP-title' 字段中。

        由于完整解析复杂，这里采用启发式方法：
        1. 先看Wrapper头后的APDU部分
        2. 查找 AARQ 帧中的 calling-AE-qualifier + calling-AP-title

        Args:
            frame_data: 完整的Wrapper帧数据

        Returns:
            System Title 十六进制字符串，如果未找到则返回None
        """
        try:
            if len(frame_data) < 16:
                return None

            # 跳过 Wrapper 头 (8字节)
            apdu_data = frame_data[8:]

            # 查找 AARQ 标签 (0x60) 或 AARE 标签 (0x61)
            # AARQ: 60 len ...
            # 在 AARQ 中，AP-title (0xA2) 后跟着 System Title
            # 简化: 查找 8 字节连续数据作为候选 System Title

            # 策略1: 在 AARQ 中查找 calling-AP-title (tag 0xA2)
            # AARQ: 60 | len | 80 len protocol-version | A1 len ... | A2 len ap-title | ...
            pos = 0
            if len(apdu_data) < 3:
                return None

            # 检查是否是 AARQ (0x60) 或 AARE (0x61)
            if apdu_data[0] in (0x60, 0x61):
                # 获取长度
                pos = 1
                length = 0
                if apdu_data[pos] & 0x80:
                    num_len_bytes = apdu_data[pos] & 0x7F
                    pos += 1
                    for _ in range(num_len_bytes):
                        length = (length << 8) | apdu_data[pos]
                        pos += 1
                else:
                    length = apdu_data[pos]
                    pos += 1

                # 在 AARQ/AARE 内容中查找 AP-title (tag 0xA2)
                # 实际格式更复杂，这里简化处理
                content_end = min(pos + length, len(apdu_data))
                search_pos = pos

                while search_pos < content_end - 2:
                    # 查找 context-specific tag，形式如 [0] [1] [2] ...
                    tag = apdu_data[search_pos]

                    # 跳过已知的短字段
                    if tag in (0x80, 0x81, 0x82, 0xA0, 0xA1, 0xBE, 0xBF):
                        # 读取长度
                        search_pos += 1
                        if search_pos >= content_end:
                            break
                        field_len = 0
                        if apdu_data[search_pos] & 0x80:
                            num_len_bytes = apdu_data[search_pos] & 0x7F
                            search_pos += 1
                            for _ in range(num_len_bytes):
                                if search_pos >= content_end:
                                    break
                                field_len = (field_len << 8) | apdu_data[search_pos]
                                search_pos += 1
                        else:
                            field_len = apdu_data[search_pos]
                            search_pos += 1
                        search_pos += field_len
                    elif tag == 0xA2:  # calling-AP-title
                        search_pos += 1
                        if search_pos >= content_end:
                            break
                        # 读取长度
                        st_len = 0
                        if apdu_data[search_pos] & 0x80:
                            num_len_bytes = apdu_data[search_pos] & 0x7F
                            search_pos += 1
                            for _ in range(num_len_bytes):
                                if search_pos >= content_end:
                                    break
                                st_len = (st_len << 8) | apdu_data[search_pos]
                                search_pos += 1
                        else:
                            st_len = apdu_data[search_pos]
                            search_pos += 1

                        # System Title 应该是 8 字节
                        if st_len == 8 and search_pos + 8 <= content_end:
                            st_bytes = apdu_data[search_pos:search_pos + 8]
                            return st_bytes.hex().upper()
                        break
                    else:
                        search_pos += 1

            # 策略2: 如果未从APDU中解析到，尝试检查帧中是否有明显的8字节模式
            # （启发式：查找 8 个字节的序列，其值看起来像设备地址）
            # 这里不做太激进的猜测，避免误识别

            return None

        except Exception as e:
            log_manager.debug("tcp", "system_title", f"提取System Title失败: {e}")
            return None

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
            client["info"].last_seen = datetime.now().isoformat()

            # 如果还没有识别出System Title，尝试从首帧中解析
            if not client["info"].system_title:
                st = self._extract_system_title(frame_data)
                if st:
                    client["info"].system_title = st
                    # 检查是否有持久化的设备名称
                    if st in self._device_names:
                        client["info"].device_name = self._device_names[st]
                    # 加入设备索引
                    self._device_index[st] = conn_id
                    log_manager.info("tcp", "device_identified",
                                    f"设备识别: {st} (conn={conn_id})")
                    # 广播设备更新事件
                    await self._broadcast_device_event("device_updated", client["info"])

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
                "system_title": client["info"].system_title if client else None,
                "timestamp": datetime.now().isoformat(),
                "parse_result": parse_result.model_dump(),
            }
            asyncio.create_task(self._ws_manager.broadcast(message))

        # 检测DataNotification并触发自动处理
        self._check_and_trigger_auto_handler(conn_id, parse_result)

    def _check_and_trigger_auto_handler(self, conn_id: str, parse_result):
        """
        检测帧是否为DataNotification，如果是则触发自动处理流程

        Args:
            conn_id: 连接ID
            parse_result: 解析结果
        """
        try:
            # 检查APDU是否为DataNotification
            apdu = parse_result.apdu
            if not apdu or not isinstance(apdu, dict):
                return

            type_name = apdu.get("type_name", "")
            if type_name != "DataNotification":
                return

            # 获取设备System Title
            system_title = None
            client = self.clients.get(conn_id)
            if client and client["info"].system_title:
                system_title = client["info"].system_title

            # 触发自动处理
            from app.services.auto_handler import auto_handler
            asyncio.create_task(
                auto_handler.handle_data_notification(
                    connection_id=conn_id,
                    device_id=system_title,
                    notification_data=apdu,
                )
            )

            log_manager.info("tcp", "auto_handler",
                           f"检测到DataNotification，已触发自动处理流程 (conn={conn_id}, st={system_title})")

        except Exception as e:
            log_manager.error("tcp", "auto_handler",
                            f"自动处理触发异常: {e}")

    async def _cleanup_connection(self, conn_id: str):
        """
        清理连接

        Args:
            conn_id: 连接ID
        """
        client = self.clients.pop(conn_id, None)
        if client:
            # 从设备索引中移除
            if client["info"].system_title and self._device_index.get(client["info"].system_title) == conn_id:
                del self._device_index[client["info"].system_title]

            # 广播设备断开事件
            await self._broadcast_device_event("device_disconnected", client["info"])

            try:
                if client.get("writer"):
                    client["writer"].close()
                    await client["writer"].wait_closed()
            except Exception:
                pass

    async def _broadcast_device_event(self, event_type: str, conn_info: TcpConnection):
        """广播设备事件到WebSocket"""
        if self._ws_manager:
            message = {
                "type": event_type,
                "device": {
                    "connection_id": conn_info.connection_id,
                    "system_title": conn_info.system_title,
                    "device_name": conn_info.device_name,
                    "ip": conn_info.client_ip,
                    "port": conn_info.client_port,
                    "connected_at": conn_info.connected_at,
                    "last_seen": conn_info.last_seen,
                    "status": conn_info.status,
                }
            }
            asyncio.create_task(self._ws_manager.broadcast(message))

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
            if client.get("is_udp") and self._udp_transport:
                # UDP 发送
                self._udp_transport.sendto(data, client["udp_addr"])
            else:
                # TCP 发送
                client["writer"].write(data)
                await client["writer"].drain()

            log_manager.info("tcp", "send",
                           f"向 {connection_id} 发送 {len(data)} 字节")
            return {"success": True, "message": f"已发送 {len(data)} 字节", "bytes_sent": len(data)}
        except Exception as e:
            log_manager.error("tcp", "send", f"发送失败: {e}")
            return {"success": False, "message": f"发送失败: {e}"}

    async def send_to_device(self, system_title: str, data: bytes) -> dict:
        """
        按System Title向设备发送数据

        Args:
            system_title: 设备System Title
            data: 要发送的数据

        Returns:
            发送结果
        """
        conn_id = self._device_index.get(system_title)
        if not conn_id:
            return {"success": False, "message": f"未找到 System Title 为 {system_title} 的设备"}
        return await self.send_data(conn_id, data)

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

    def get_device_by_system_title(self, system_title: str) -> Optional[TcpConnection]:
        """
        根据System Title获取设备信息

        Args:
            system_title: 设备System Title

        Returns:
            设备连接信息，如果未找到则返回None
        """
        conn_id = self._device_index.get(system_title)
        if conn_id:
            client = self.clients.get(conn_id)
            if client:
                return client["info"]
        return None

    def get_status(self) -> dict:
        """获取服务器状态"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
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

    def rename_device(self, system_title: str, device_name: str) -> bool:
        """
        重命名设备

        Args:
            system_title: 设备System Title
            device_name: 新的设备名称

        Returns:
            是否成功
        """
        # 持久化存储
        self._device_names[system_title] = device_name

        # 更新当前连接的设备
        conn_id = self._device_index.get(system_title)
        if conn_id:
            client = self.clients.get(conn_id)
            if client:
                client["info"].device_name = device_name
                return True

        return False


# 全局TCP服务器实例
tcp_server = TcpServer()
