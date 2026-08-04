"""
自动处理流程服务 (AutoHandler)

收到DataNotification后，自动执行预设的Pull操作并发送Confirm。

功能:
1. 预设操作配置 - 用户可配置要读取的对象列表、是否发送Confirm等
2. 自动处理流程 - 收到DataNotification后自动执行Pull操作
3. 配置管理 - 支持为不同设备配置不同的预设操作
"""
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from app.services.log_manager import log_manager


@dataclass
class PullOperation:
    """Pull操作配置项"""
    class_id: int
    obis: str  # OBIS码，格式 "A-B:C.D.E.F"
    attribute_id: int = 2  # 属性ID，默认2（值属性）
    description: str = ""  # 描述


@dataclass
class AutoHandlerConfig:
    """自动处理配置"""
    enabled: bool = False  # 是否启用自动处理
    send_confirm: bool = True  # 是否发送DataNotification Confirm
    pull_operations: List[PullOperation] = field(default_factory=list)  # 预设Pull操作列表
    pull_timeout: float = 5.0  # Pull操作超时时间（秒）
    operation_order: str = "pull_then_confirm"  # 操作顺序: pull_then_confirm / confirm_then_pull / pull_only / confirm_only


class AutoHandler:
    """
    自动处理器

    收到DataNotification后，自动执行预设的Pull操作并发送Confirm。
    单例模式。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 设备配置: device_id (str) -> AutoHandlerConfig
        self._device_configs: Dict[str, AutoHandlerConfig] = {}

        # 默认配置（用于未指定设备时）
        self._default_config = AutoHandlerConfig()

        # TCP服务器引用（用于发送数据）
        self._tcp_server = None

        # 正在进行的自动处理任务
        self._active_tasks: Dict[str, asyncio.Task] = {}

    def set_tcp_server(self, tcp_server):
        """设置TCP服务器引用，用于发送数据"""
        self._tcp_server = tcp_server

    # ---------- 配置管理 ----------

    def get_config(self, device_id: Optional[str] = None) -> dict:
        """
        获取自动处理配置

        Args:
            device_id: 设备ID，None表示获取默认配置

        Returns:
            dict: 配置信息
        """
        config = self._get_config(device_id)
        return self._config_to_dict(config)

    def set_config(self, config_data: dict, device_id: Optional[str] = None) -> dict:
        """
        更新自动处理配置

        Args:
            config_data: 配置数据字典
            device_id: 设备ID，None表示更新默认配置

        Returns:
            dict: 更新后的配置
        """
        config = self._dict_to_config(config_data)
        if device_id:
            self._device_configs[device_id] = config
        else:
            self._default_config = config

        log_manager.info("auto", "config",
                        f"配置已更新 {'(设备: ' + device_id + ')' if device_id else '(默认)'}: "
                        f"enabled={config.enabled}, operations={len(config.pull_operations)}")
        return self._config_to_dict(config)

    def list_device_configs(self) -> List[dict]:
        """获取所有设备配置列表"""
        result = []
        for device_id, config in self._device_configs.items():
            result.append({
                "device_id": device_id,
                **self._config_to_dict(config),
            })
        return result

    def delete_device_config(self, device_id: str) -> bool:
        """
        删除指定设备的配置

        Returns:
            bool: 是否成功删除
        """
        if device_id in self._device_configs:
            del self._device_configs[device_id]
            return True
        return False

    def _get_config(self, device_id: Optional[str] = None) -> AutoHandlerConfig:
        """获取配置（内部方法）"""
        if device_id and device_id in self._device_configs:
            return self._device_configs[device_id]
        return self._default_config

    # ---------- 自动处理流程 ----------

    async def handle_data_notification(self, connection_id: str,
                                        device_id: Optional[str] = None,
                                        notification_data: Optional[dict] = None) -> dict:
        """
        处理DataNotification - 执行自动处理流程

        流程:
        1. 检查配置是否启用
        2. 根据操作顺序执行Pull和/或Confirm
        3. 返回处理结果

        Args:
            connection_id: TCP连接ID
            device_id: 设备ID（用于查找配置）
            notification_data: DataNotification数据（可选）

        Returns:
            dict: 处理结果
        """
        config = self._get_config(device_id)

        if not config.enabled:
            return {
                "success": True,
                "skipped": True,
                "reason": "auto_handler_disabled",
                "message": "自动处理未启用",
            }

        # 检查是否已有正在进行的任务
        task_key = f"{connection_id}:{device_id or 'default'}"
        if task_key in self._active_tasks and not self._active_tasks[task_key].done():
            return {
                "success": False,
                "skipped": True,
                "reason": "task_already_running",
                "message": "已有自动处理任务正在进行",
            }

        # 创建任务
        task = asyncio.create_task(
            self._execute_auto_flow(connection_id, device_id, config, notification_data)
        )
        self._active_tasks[task_key] = task

        # 不等待任务完成，直接返回（异步执行）
        return {
            "success": True,
            "started": True,
            "task_id": task_key,
            "message": "自动处理流程已启动",
            "operations": len(config.pull_operations),
            "order": config.operation_order,
        }

    async def _execute_auto_flow(self, connection_id: str,
                                  device_id: Optional[str],
                                  config: AutoHandlerConfig,
                                  notification_data: Optional[dict] = None) -> dict:
        """
        执行自动处理流程（内部方法）

        Args:
            connection_id: TCP连接ID
            device_id: 设备ID
            config: 自动处理配置
            notification_data: DataNotification数据

        Returns:
            dict: 执行结果
        """
        results = {
            "connection_id": connection_id,
            "device_id": device_id,
            "pull_results": [],
            "confirm_result": None,
            "errors": [],
        }

        try:
            order = config.operation_order

            if order in ("pull_then_confirm", "pull_only"):
                # 先执行Pull操作
                pull_results = await self._execute_pull_operations(
                    connection_id, config.pull_operations, config.pull_timeout
                )
                results["pull_results"] = pull_results

            if order in ("pull_then_confirm", "confirm_then_pull", "confirm_only"):
                if config.send_confirm:
                    # 发送Confirm
                    confirm_result = await self._send_confirm(connection_id, notification_data)
                    results["confirm_result"] = confirm_result

            if order == "confirm_then_pull":
                # 先Confirm再Pull
                pull_results = await self._execute_pull_operations(
                    connection_id, config.pull_operations, config.pull_timeout
                )
                results["pull_results"] = pull_results

            log_manager.info("auto", "flow",
                            f"自动处理流程完成: conn={connection_id}, "
                            f"pulls={len(results['pull_results'])}, "
                            f"confirm={'sent' if results['confirm_result'] else 'skipped'}")

        except Exception as e:
            results["errors"].append(str(e))
            log_manager.error("auto", "flow",
                            f"自动处理流程异常: {e}")

        return results

    async def _execute_pull_operations(self, connection_id: str,
                                        operations: List[PullOperation],
                                        timeout: float) -> List[dict]:
        """
        执行Pull操作列表

        对每个操作构造GetRequest并发送到设备。

        Args:
            connection_id: TCP连接ID
            operations: Pull操作列表
            timeout: 每个操作的超时时间

        Returns:
            List[dict]: 每个操作的结果
        """
        results = []

        if not self._tcp_server:
            return [{
                "success": False,
                "error": "tcp_server_not_available",
                "message": "TCP服务器未连接",
            }]

        for i, op in enumerate(operations):
            try:
                # 构造GetRequest APDU
                from app.services.apdu_parser import build_apdu
                from app.services.wrapper import build_wpd
                from app.utils.hex_utils import hex_to_bytes

                apdu_data = build_apdu("get-request", {
                    "get_type": 1,
                    "invoke_id": i + 1,
                    "class_id": op.class_id,
                    "obis": op.obis,
                    "attribute_id": op.attribute_id,
                })

                # 封装Wrapper帧
                frame = build_wpd(apdu_data, src_wport=1, dst_wport=16)

                # 发送数据
                result = await self._tcp_server.send_data(connection_id, frame)

                results.append({
                    "operation_index": i,
                    "class_id": op.class_id,
                    "obis": op.obis,
                    "attribute_id": op.attribute_id,
                    "description": op.description,
                    "sent": result.get("success", False),
                    "bytes_sent": result.get("bytes_sent", 0),
                    "error": result.get("message", "") if not result.get("success") else "",
                })

                log_manager.info("auto", "pull",
                                f"Pull操作 {i+1}: class={op.class_id}, obis={op.obis}, "
                                f"attr={op.attribute_id} - "
                                f"{'发送成功' if result.get('success') else '发送失败: ' + result.get('message', '')}")

            except Exception as e:
                results.append({
                    "operation_index": i,
                    "class_id": op.class_id,
                    "obis": op.obis,
                    "attribute_id": op.attribute_id,
                    "description": op.description,
                    "sent": False,
                    "error": str(e),
                })
                log_manager.error("auto", "pull",
                                f"Pull操作 {i+1} 异常: {e}")

        return results

    async def _send_confirm(self, connection_id: str,
                             notification_data: Optional[dict] = None) -> dict:
        """
        发送DataNotification Confirm帧

        Args:
            connection_id: TCP连接ID
            notification_data: DataNotification数据（用于构造Confirm）

        Returns:
            dict: 发送结果
        """
        if not self._tcp_server:
            return {
                "success": False,
                "error": "tcp_server_not_available",
                "message": "TCP服务器未连接",
            }

        try:
            # 构造DataNotification Confirm
            # 在DLMS中，DataNotification Confirm通常是一个简单的响应
            # 这里构造一个空的响应（tag=15的响应）
            # 实际Confirm格式根据协议可能不同，这里做简化处理
            from app.services.wrapper import build_wpd

            # DataNotification Confirm的构造
            # 通常是发送一个空的APDU或者特定的响应帧
            # 这里发送一个简单的确认帧
            confirm_apdu = bytes([15])  # DataNotification tag

            # 封装Wrapper帧
            frame = build_wpd(confirm_apdu, src_wport=1, dst_wport=16)

            # 发送数据
            result = await self._tcp_server.send_data(connection_id, frame)

            log_manager.info("auto", "confirm",
                            f"Confirm发送: {'成功' if result.get('success') else '失败: ' + result.get('message', '')}")

            return {
                "success": result.get("success", False),
                "bytes_sent": result.get("bytes_sent", 0),
                "error": "" if result.get("success") else result.get("message", ""),
            }

        except Exception as e:
            log_manager.error("auto", "confirm", f"Confirm发送异常: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ---------- 手动触发 ----------

    async def trigger_manual(self, connection_id: str,
                              device_id: Optional[str] = None) -> dict:
        """
        手动触发自动处理流程（用于测试）

        Args:
            connection_id: TCP连接ID
            device_id: 设备ID

        Returns:
            dict: 触发结果
        """
        # 临时启用配置来执行
        config = self._get_config(device_id)
        if not config.enabled:
            # 手动触发时即使配置未启用也执行
            temp_config = AutoHandlerConfig(
                enabled=True,
                send_confirm=config.send_confirm,
                pull_operations=config.pull_operations,
                pull_timeout=config.pull_timeout,
                operation_order=config.operation_order,
            )
            return await self._execute_auto_flow(connection_id, device_id, temp_config)
        else:
            return await self._execute_auto_flow(connection_id, device_id, config)

    # ---------- 配置序列化 ----------

    @staticmethod
    def _config_to_dict(config: AutoHandlerConfig) -> dict:
        """将配置对象转换为字典"""
        return {
            "enabled": config.enabled,
            "send_confirm": config.send_confirm,
            "pull_operations": [
                {
                    "class_id": op.class_id,
                    "obis": op.obis,
                    "attribute_id": op.attribute_id,
                    "description": op.description,
                }
                for op in config.pull_operations
            ],
            "pull_timeout": config.pull_timeout,
            "operation_order": config.operation_order,
        }

    @staticmethod
    def _dict_to_config(data: dict) -> AutoHandlerConfig:
        """将字典转换为配置对象"""
        operations = []
        for op_data in data.get("pull_operations", []):
            operations.append(PullOperation(
                class_id=int(op_data.get("class_id", 0)),
                obis=str(op_data.get("obis", "0-0:0.0.0.0")),
                attribute_id=int(op_data.get("attribute_id", 2)),
                description=str(op_data.get("description", "")),
            ))

        return AutoHandlerConfig(
            enabled=bool(data.get("enabled", False)),
            send_confirm=bool(data.get("send_confirm", True)),
            pull_operations=operations,
            pull_timeout=float(data.get("pull_timeout", 5.0)),
            operation_order=str(data.get("operation_order", "pull_then_confirm")),
        )


# 全局单例实例
auto_handler = AutoHandler()
