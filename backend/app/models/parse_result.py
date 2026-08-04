"""
解析结果模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from app.models.wrapper import WrapperFrame
from app.models.cipher import CipherFrame


class ParseLogEntry(BaseModel):
    """解析日志条目"""

    level: str = Field(description="日志级别 (info/warn/error/debug)")
    step: str = Field(description="解析步骤")
    message: str = Field(description="日志消息")
    timestamp: str = Field(description="时间戳")


class ParseResult(BaseModel):
    """帧解析结果模型"""

    frame_id: str = Field(description="帧唯一标识")
    timestamp: str = Field(description="解析时间戳")
    raw_hex: str = Field(description="原始十六进制数据")
    wrapper: Optional[WrapperFrame] = Field(default=None, description="Wrapper层解析结果")
    ciphering: Optional[CipherFrame] = Field(default=None, description="加密层解析结果")
    compression: Optional[dict] = Field(default=None, description="压缩层信息")
    apdu: Optional[dict] = Field(default=None, description="APDU解析结果")
    matched_objects: List[dict] = Field(default_factory=list, description="匹配到的数据模型对象")
    parse_logs: List[ParseLogEntry] = Field(default_factory=list, description="解析日志")
    errors: List[str] = Field(default_factory=list, description="错误列表")

    model_config = {
        "json_schema_extra": {
            "example": {
                "frame_id": "abc123",
                "timestamp": "2024-01-01T12:00:00",
                "raw_hex": "0001000100100080c8010007...",
                "wrapper": {"version": 1, "src_wport": 1, "dst_wport": 16, "data_length": 128, "payload_hex": "c801..."},
                "ciphering": None,
                "compression": None,
                "apdu": {"tag": 15, "type_name": "DataNotification", "items": []},
                "matched_objects": [],
                "parse_logs": [],
                "errors": [],
            }
        }
    }


class ParseRequest(BaseModel):
    """解析请求模型"""

    hex_data: str = Field(description="十六进制帧数据")
    encryption_key: Optional[str] = Field(default=None, description="加密密钥（可选，十六进制）")
    system_title: Optional[str] = Field(default=None, description="系统标题（可选，十六进制）")


class BuildRequest(BaseModel):
    """组帧请求模型"""

    apdu_type: str = Field(description="APDU类型")
    params: dict = Field(default_factory=dict, description="APDU参数")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")
    encrypt: bool = Field(default=False, description="是否加密")
    encryption_key: Optional[str] = Field(default=None, description="加密密钥")
    system_title: Optional[str] = Field(default=None, description="系统标题")


class BuildResponse(BaseModel):
    """组帧响应模型"""

    success: bool = Field(description="是否成功")
    hex_data: str = Field(default="", description="生成的十六进制帧数据")
    frame_length: int = Field(default=0, description="帧长度（字节）")
    message: str = Field(default="", description="消息")
