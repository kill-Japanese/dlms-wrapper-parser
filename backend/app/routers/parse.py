"""
帧解析路由 - 提供帧解析和组帧接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional

from app.models.parse_result import (
    ParseResult,
    ParseRequest,
    BuildRequest,
    BuildResponse,
)
from app.services.dlms_stack import parse_frame, build_frame
from app.services.log_manager import log_manager
from app.utils.hex_utils import hex_to_bytes, bytes_to_hex


router = APIRouter(prefix="/api/parse", tags=["Parse"])


@router.post("/hex", response_model=ParseResult, summary="解析十六进制帧数据")
async def parse_hex(request: ParseRequest):
    """
    解析DLMS帧数据（十六进制字符串输入）

    - **hex_data**: 十六进制帧数据，可以带空格、换行等
    - **encryption_key**: 加密密钥（兼容别名，映射到guek，十六进制格式）
    - **guek**: Global Unicast Encryption Key - 全局单播加密密钥（十六进制）
    - **gubk**: Global Unicast Broadcast Key - 广播密钥（十六进制）
    - **ak**: Authentication Key - 认证密钥（十六进制）
    - **kek**: Key Encryption Key - 密钥加密密钥（十六进制）
    - **system_title**: 系统标题（可选，十六进制格式）
    - **invocation_counter**: 调用计数器（可选）
    """
    if not request.hex_data or not request.hex_data.strip():
        raise HTTPException(status_code=400, detail="hex_data不能为空")

    try:
        result = parse_frame(
            hex_data=request.hex_data,
            encryption_key=request.encryption_key,
            guek=request.guek,
            gubk=request.gubk,
            ak=request.ak,
            kek=request.kek,
            system_title=request.system_title,
            invocation_counter=request.invocation_counter,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")


@router.post("/file", response_model=list[ParseResult], summary="从文件解析帧数据")
async def parse_file(
    file: UploadFile = File(..., description="二进制文件或文本文件"),
    encryption_key: Optional[str] = None,
):
    """
    从文件中解析DLMS帧数据

    支持:
    - 二进制文件 (.bin) - 直接读取字节
    - 文本文件 (.txt, .hex) - 读取十六进制文本

    如果文件包含多个帧，将尝试分割并逐个解析。
    """
    try:
        contents = await file.read()
        filename = file.filename or ""

        # 判断文件类型
        is_text = filename.endswith((".txt", ".hex", ".log"))

        if is_text:
            # 文本文件 - 尝试解析十六进制
            try:
                text = contents.decode("utf-8", errors="replace")
                # 提取所有十六进制字符
                import re
                hex_chars = re.sub(r"[\s\r\n:]", "", text)
                hex_data = hex_chars
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")
        else:
            # 二进制文件
            hex_data = bytes_to_hex(contents)

        if not hex_data or len(hex_data) < 16:
            raise HTTPException(status_code=400, detail="文件数据太短或为空")

        # TODO: 多帧分割 - 暂时作为单帧处理
        # 后续可以根据Wrapper帧头和长度字段分割多帧
        result = parse_frame(
            hex_data=hex_data,
            encryption_key=encryption_key,
        )

        return [result]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {e}")


@router.post("/build", response_model=BuildResponse, summary="组帧接口")
async def build_frame_endpoint(request: BuildRequest):
    """
    构建DLMS帧数据

    - **apdu_type**: APDU类型 (GetRequest, DataNotification等)
    - **params**: APDU参数字典
    - **src_wport**: 源WPort (默认1)
    - **dst_wport**: 目的WPort (默认16)
    - **encrypt**: 是否加密 (默认false)
    - **encryption_key**: 加密密钥 (兼容别名，映射到guek)
    - **guek**: Global Unicast Encryption Key - 全局单播加密密钥（十六进制）
    - **gubk**: Global Unicast Broadcast Key - 广播密钥（十六进制）
    - **ak**: Authentication Key - 认证密钥（十六进制）
    - **kek**: Key Encryption Key - 密钥加密密钥（十六进制）
    - **system_title**: 系统标题 (加密时必填)
    - **invocation_counter**: 调用计数器 (默认1)
    - **key_id**: 密钥标识 (0=unicast/GUEK, 1=broadcast/GUBK, 2=system)
    """
    try:
        result = build_frame(
            apdu_type=request.apdu_type,
            params=request.params,
            src_wport=request.src_wport,
            dst_wport=request.dst_wport,
            encrypt=request.encrypt,
            encryption_key=request.encryption_key,
            guek=request.guek,
            gubk=request.gubk,
            ak=request.ak,
            kek=request.kek,
            system_title=request.system_title,
            invocation_counter=request.invocation_counter or 1,
            key_id=request.key_id,
        )
        return BuildResponse(**result)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"组帧失败: {e}")


@router.get("/logs/{frame_id}", summary="获取帧解析日志")
async def get_parse_logs(frame_id: str, level: str = "debug"):
    """
    获取指定帧的详细解析日志

    - **frame_id**: 帧ID
    - **level**: 最低日志级别 (debug/info/warn/error)
    """
    logs = log_manager.get_logs(frame_id, min_level=level)
    if not logs:
        raise HTTPException(status_code=404, detail=f"未找到帧 {frame_id} 的日志")
    return {"frame_id": frame_id, "logs": logs, "count": len(logs)}
