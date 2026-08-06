"""
NB-IoT 设备 HTTP 上传路由

注意：Render 不支持原生 TCP，NB 设备可通过 HTTP POST 发送 DLMS 数据。
本路由提供两个端点，接收 NB-IoT 设备通过 HTTP 上报的 DLMS Wrapper 帧数据，
复用 app.services.dlms_stack.parse_frame 进行完整协议栈解析，解析成功后
通过 WebSocket 广播给前端，并返回解析结果的简化版本。

适用场景：
- NB-IoT / 蜂窝模组通过 CoAP/HTTP 上报的 DLMS 数据
- 部署在 Render / Serverless 等不支持长连接 TCP 的平台
- 设备侧将原本通过 TCP 传输的 Wrapper 帧改为 HTTP POST 上送
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.dlms_stack import parse_frame
from app.services.tcp_server import tcp_server
from app.services.log_manager import log_manager
from app.utils.hex_utils import bytes_to_hex


router = APIRouter(prefix="/api/nb-device", tags=["NB-Device"])


# NB 设备 HTTP 上传使用的伪连接 ID 前缀，用于在 WebSocket 消息中区分来源
_HTTP_CONN_PREFIX = "http-nb"


class HexUploadRequest(BaseModel):
    """十六进制上传请求体"""

    hex: str = Field(
        ...,
        description="DLMS Wrapper 帧的十六进制字符串，可带空格/换行/冒号分隔",
    )


def _get_ws_manager():
    """
    获取 WebSocket 广播管理器。

    tcp_server 在应用启动时通过 set_ws_manager 绑定 WebSocketManager，
    这里通过其内部引用拿到广播能力。若管理器尚未初始化则返回 None。
    """
    return getattr(tcp_server, "_ws_manager", None)


async def _broadcast_parse_result(parse_result, source: str, system_title: Optional[str] = None) -> None:
    """
    通过 WebSocket 广播解析结果。

    广播消息结构与 TCP 服务器 _process_frame 中的 frame_received 保持一致，
    前端可复用同一套处理逻辑，仅通过 source / connection_id 区分来源为 HTTP。

    Args:
        parse_result: ParseResult 解析结果对象
        source: 数据来源标识（binary / hex）
        system_title: 设备 System Title（若可识别）
    """
    ws_manager = _get_ws_manager()
    if ws_manager is None:
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "warn", "broadcast",
            "WebSocket 管理器未初始化，跳过广播（TCP 服务器可能未启动）",
        )
        return

    message = {
        "type": "frame_received",
        "connection_id": f"{_HTTP_CONN_PREFIX}-{uuid.uuid4().hex[:8]}",
        "source": f"http-{source}",
        "system_title": system_title,
        "timestamp": datetime.now().isoformat(),
        "parse_result": parse_result.model_dump(),
    }
    try:
        await ws_manager.broadcast(message)
    except Exception as e:
        # 广播失败不应影响 HTTP 响应，仅记录日志
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "error", "broadcast",
            f"WebSocket 广播失败: {e}",
        )


def _build_simplified_response(parse_result) -> dict:
    """
    构建简化版解析结果响应。

    Args:
        parse_result: ParseResult 解析结果对象

    Returns:
        dict: 包含 status / frame_count / apdu_type / timestamp 等字段的简化结果
    """
    # 提取 APDU 类型
    apdu_type = None
    if isinstance(parse_result.apdu, dict):
        apdu_type = parse_result.apdu.get("type_name")

    # 判断整体状态
    has_errors = bool(parse_result.errors)
    if parse_result.apdu is None:
        status = "error"
    elif has_errors:
        status = "partial"
    else:
        status = "success"

    return {
        "status": status,
        "frame_count": 1,
        "apdu_type": apdu_type,
        "timestamp": parse_result.timestamp,
        "frame_id": parse_result.frame_id,
        "errors": parse_result.errors,
    }


@router.post("/upload", summary="接收原始二进制 DLMS 数据")
async def upload_binary(
    request: Request,
    guek: Optional[str] = Query(default=None, description="全局单播加密密钥（十六进制）"),
    gubk: Optional[str] = Query(default=None, description="全局广播密钥（十六进制）"),
    ak: Optional[str] = Query(default=None, description="认证密钥（十六进制）"),
    kek: Optional[str] = Query(default=None, description="密钥加密密钥（十六进制）"),
    system_title: Optional[str] = Query(default=None, description="系统标题（十六进制，用于解密验证）"),
):
    """
    NB-IoT 设备通过 HTTP POST 上传原始二进制 DLMS Wrapper 帧。

    期望 Content-Type: application/octet-stream，请求体为原始字节流。
    解析逻辑复用 app.services.dlms_stack.parse_frame，解析成功后通过
    WebSocket 广播，并返回简化版结果。

    对于加密数据，可通过查询参数提供解密密钥（guek/gubk/ak/kek）。
    """
    request_id = uuid.uuid4().hex[:8]

    try:
        body = await request.body()
        if not body:
            log_manager.add_log(
                _HTTP_CONN_PREFIX, "warn", "upload",
                f"[{request_id}] 二进制上传请求体为空",
            )
            raise HTTPException(status_code=400, detail="请求体为空，未收到任何 DLMS 数据")

        content_type = request.headers.get("content-type", "")
        byte_len = len(body)
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "info", "upload",
            f"[{request_id}] 收到二进制数据: {byte_len} 字节, Content-Type={content_type}",
        )

        # 字节流转十六进制字符串后复用 parse_frame
        hex_data = bytes_to_hex(body)
        if len(hex_data) < 16:
            log_manager.add_log(
                _HTTP_CONN_PREFIX, "warn", "upload",
                f"[{request_id}] 数据过短({byte_len}字节)，不足以构成完整 Wrapper 帧",
            )
            raise HTTPException(status_code=400, detail="数据过短，不足以构成完整 DLMS 帧")

        # 调用协议栈解析
        parse_result = parse_frame(
            hex_data=hex_data,
            guek=guek,
            gubk=gubk,
            ak=ak,
            kek=kek,
            system_title=system_title,
        )

        log_manager.add_log(
            _HTTP_CONN_PREFIX, "info", "upload",
            f"[{request_id}] 解析完成: frame_id={parse_result.frame_id}, "
            f"errors={len(parse_result.errors)}",
        )

        # 广播解析结果
        await _broadcast_parse_result(parse_result, source="binary")

        return _build_simplified_response(parse_result)

    except HTTPException:
        raise
    except ValueError as e:
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "error", "upload",
            f"[{request_id}] 数据格式错误: {e}",
        )
        raise HTTPException(status_code=400, detail=f"数据格式错误: {e}")
    except Exception as e:
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "error", "upload",
            f"[{request_id}] 二进制上传解析异常: {e}",
        )
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")


@router.post("/upload-hex", summary="接收十六进制字符串 DLMS 数据")
async def upload_hex(
    payload: HexUploadRequest,
    guek: Optional[str] = Query(default=None, description="全局单播加密密钥（十六进制）"),
    gubk: Optional[str] = Query(default=None, description="全局广播密钥（十六进制）"),
    ak: Optional[str] = Query(default=None, description="认证密钥（十六进制）"),
    kek: Optional[str] = Query(default=None, description="密钥加密密钥（十六进制）"),
    system_title: Optional[str] = Query(default=None, description="系统标题（十六进制，用于解密验证）"),
):
    """
    NB-IoT 设备通过 HTTP POST 上传十六进制字符串形式的 DLMS Wrapper 帧。

    请求体 JSON: {"hex": "000100010010..."}，可带空格/换行/冒号分隔。
    解析逻辑复用 app.services.dlms_stack.parse_frame，解析成功后通过
    WebSocket 广播，并返回简化版结果。

    对于加密数据，可通过查询参数提供解密密钥（guek/gubk/ak/kek）。
    """
    request_id = uuid.uuid4().hex[:8]

    try:
        hex_data = (payload.hex or "").strip()
        if not hex_data:
            log_manager.add_log(
                _HTTP_CONN_PREFIX, "warn", "upload-hex",
                f"[{request_id}] 十六进制上传 hex 字段为空",
            )
            raise HTTPException(status_code=400, detail="hex 字段不能为空")

        # 粗略去除空白后统计长度（hex_to_bytes 内部会做更完整清洗）
        cleaned_len = len(hex_data.replace(" ", "").replace("\n", "").replace("\r", ""))
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "info", "upload-hex",
            f"[{request_id}] 收到十六进制数据: 原始{len(payload.hex)}字符, 去空白{cleaned_len}字符",
        )

        if cleaned_len < 16:
            log_manager.add_log(
                _HTTP_CONN_PREFIX, "warn", "upload-hex",
                f"[{request_id}] 数据过短({cleaned_len}字符)，不足以构成完整 Wrapper 帧",
            )
            raise HTTPException(status_code=400, detail="数据过短，不足以构成完整 DLMS 帧")

        # 调用协议栈解析（parse_frame 内部调用 hex_to_bytes，已处理空格/换行/冒号/0x 前缀）
        parse_result = parse_frame(
            hex_data=hex_data,
            guek=guek,
            gubk=gubk,
            ak=ak,
            kek=kek,
            system_title=system_title,
        )

        log_manager.add_log(
            _HTTP_CONN_PREFIX, "info", "upload-hex",
            f"[{request_id}] 解析完成: frame_id={parse_result.frame_id}, "
            f"errors={len(parse_result.errors)}",
        )

        # 广播解析结果
        await _broadcast_parse_result(parse_result, source="hex")

        return _build_simplified_response(parse_result)

    except HTTPException:
        raise
    except ValueError as e:
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "error", "upload-hex",
            f"[{request_id}] 十六进制格式错误: {e}",
        )
        raise HTTPException(status_code=400, detail=f"十六进制格式错误: {e}")
    except Exception as e:
        log_manager.add_log(
            _HTTP_CONN_PREFIX, "error", "upload-hex",
            f"[{request_id}] 十六进制上传解析异常: {e}",
        )
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")
