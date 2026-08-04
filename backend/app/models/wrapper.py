"""
Wrapper帧模型定义
"""
from pydantic import BaseModel, Field


class WrapperFrame(BaseModel):
    """DLMS Wrapper层帧模型 (IEC 62056-47 / HDLC Wrapper)"""

    version: int = Field(description="Wrapper协议版本")
    src_wport: int = Field(description="源WPort地址")
    dst_wport: int = Field(description="目的WPort地址")
    data_length: int = Field(description="数据长度（字节）")
    payload_hex: str = Field(description="载荷数据（十六进制字符串）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": 1,
                "src_wport": 1,
                "dst_wport": 16,
                "data_length": 128,
                "payload_hex": "c8010007...",
            }
        }
    }
