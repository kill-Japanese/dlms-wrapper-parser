"""
加密帧模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional


class CipherInfo(BaseModel):
    """加密信息模型"""

    encrypted: bool = Field(default=False, description="是否加密")
    authenticated: bool = Field(default=False, description="是否认证")
    compressed: bool = Field(default=False, description="是否压缩")
    key_id: int = Field(default=0, description="密钥ID")


class CipherFrame(BaseModel):
    """加密帧模型"""

    security_control: str = Field(description="安全控制字节（十六进制）")
    security_control_byte: int = Field(description="安全控制字节原始值")
    system_title: str = Field(description="系统标题（十六进制）")
    invocation_counter: int = Field(description="调用计数器")
    ciphered_data_hex: str = Field(description="加密数据（十六进制字符串）")
    gmac_tag: str = Field(default="", description="GMAC认证标签")
    decrypt_success: bool = Field(default=False, description="解密是否成功")
    cipher_info: Optional[CipherInfo] = Field(default=None, description="加密详情")

    model_config = {
        "json_schema_extra": {
            "example": {
                "security_control": "20",
                "security_control_byte": 32,
                "system_title": "000000000000",
                "invocation_counter": 1,
                "ciphered_data_hex": "abcd1234...",
                "gmac_tag": "deadbeef",
                "decrypt_success": True,
                "cipher_info": {
                    "encrypted": True,
                    "authenticated": False,
                    "compressed": False,
                    "key_id": 0,
                },
            }
        }
    }
