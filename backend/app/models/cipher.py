"""
加密帧模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional


class CipherInfo(BaseModel):
    """加密信息模型

    Security Control (SC) 字节位定义 (参考 DLMS 蓝皮书/IEC 62056-53):
    - Bit 7 (0x80): C - Compression 压缩标识
    - Bit 6 (0x40): Key_Set 密钥集 (0=Unicast/GUEK, 1=Broadcast/GUBK)
    - Bit 5 (0x20): E - Encryption 加密标识
    - Bit 4 (0x10): A - Authentication 认证标识
    - Bit 3-0 (0x0F): Security_Suite_Id 安全套件ID (0/1/2)
    """

    encrypted: bool = Field(default=False, description="是否加密 (Bit 5, E)")
    authenticated: bool = Field(default=False, description="是否认证 (Bit 4, A)")
    compressed: bool = Field(default=False, description="是否压缩 (Bit 7, C)")
    key_id: int = Field(default=0, description="密钥集 (Bit 6): 0=Unicast/GUEK, 1=Broadcast/GUBK")
    ecc_signed: bool = Field(default=False, description="是否有ECC签名 (兼容旧字段)")
    suite_id: int = Field(default=1, description="安全套件ID (Bit 3-0): 0/1/2")


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
    extracted_from_frame: bool = Field(default=False, description="System Title和Invocation Counter是否从帧中提取")

    model_config = {
        "json_schema_extra": {
            "example": {
                "security_control": "31",
                "security_control_byte": 49,
                "system_title": "4953453131303733",
                "invocation_counter": 1,
                "ciphered_data_hex": "abcd1234...",
                "gmac_tag": "deadbeef...",
                "decrypt_success": True,
                "extracted_from_frame": True,
                "cipher_info": {
                    "encrypted": True,
                    "authenticated": True,
                    "compressed": False,
                    "key_id": 0,
                    "suite_id": 1,
                },
            }
        }
    }
