"""
加密帧模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional


class CipherInfo(BaseModel):
    """加密信息模型

    Security Control (SC) 字节位定义 (参考 DLMS 蓝皮书/IEC 62056-53):
    - bit 0 (0x01): EK - Encryption Key 使用标识（1=已加密）
    - bit 1 (0x02): AK - Authentication Key 使用标识（1=已认证）
    - bit 2 (0x04): 压缩标识（1=已压缩，V.44）
    - bit 3-4 (0x08, 0x10): Key 类型标识
      - 00 (0x00) = Unicast / GUEK (Global Unicast Encryption Key)
      - 01 (0x08) = Broadcast / GUBK (Global Unicast Broadcast Key)
      - 10 (0x10) = System Key
    - bit 5 (0x20): ECC 签名标识（1=有ECC签名）
    - bit 6-7: 保留
    """

    encrypted: bool = Field(default=False, description="是否加密 (bit 0, EK)")
    authenticated: bool = Field(default=False, description="是否认证 (bit 1, AK)")
    compressed: bool = Field(default=False, description="是否压缩 (bit 2, V.44)")
    key_id: int = Field(default=0, description="密钥标识 (bit 3-4): 0=Unicast/GUEK, 1=Broadcast/GUBK, 2=System")
    ecc_signed: bool = Field(default=False, description="是否有ECC签名 (bit 5)")


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
                "security_control": "20",
                "security_control_byte": 32,
                "system_title": "000000000000",
                "invocation_counter": 1,
                "ciphered_data_hex": "abcd1234...",
                "gmac_tag": "deadbeef",
                "decrypt_success": True,
                "extracted_from_frame": True,
                "cipher_info": {
                    "encrypted": True,
                    "authenticated": False,
                    "compressed": False,
                    "key_id": 0,
                    "ecc_signed": False,
                },
            }
        }
    }
