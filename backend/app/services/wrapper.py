"""
Wrapper层解析/封装 (IEC 62056-47 / WPD Wrapper)

Wrapper头格式（8字节，大端序）:
- Version (2 bytes): 版本号，通常为0x0001
- Source WPort (2 bytes): 源端口号
- Destination WPort (2 bytes): 目的端口号
- Data Length (2 bytes): 后续数据长度（字节数）
"""
import struct
from typing import Optional

from app.models.wrapper import WrapperFrame
from app.utils.hex_utils import bytes_to_hex


# Wrapper头长度
WRAPPER_HEADER_LENGTH = 8

# 常见WPort定义
WPORT_CLIENT = 1       # 客户端WPort
WPORT_METER = 16       # 电表WPort
WPORT_P2P = 40         # P2P WPort


def parse_wpd(data: bytes) -> WrapperFrame:
    """
    解析Wrapper层帧头 (WPD - Wrapper Protocol Data)

    Args:
        data: 完整的帧数据（包含8字节头）

    Returns:
        WrapperFrame: 解析后的Wrapper帧对象

    Raises:
        ValueError: 如果数据长度不足或格式错误
    """
    if len(data) < WRAPPER_HEADER_LENGTH:
        raise ValueError(
            f"Wrapper帧数据长度不足，至少需要{WRAPPER_HEADER_LENGTH}字节，"
            f"实际{len(data)}字节"
        )

    # 解析8字节头：版本、源WPort、目的WPort、数据长度
    # struct格式 '>HHHH' 表示4个无符号短整型，大端序
    version, src_wport, dst_wport, data_length = struct.unpack(">HHHH", data[:8])

    # 验证数据长度
    actual_payload_len = len(data) - WRAPPER_HEADER_LENGTH
    if actual_payload_len < data_length:
        # 数据不完整
        raise ValueError(
            f"Wrapper帧数据不完整，声明长度{data_length}字节，"
            f"实际载荷{actual_payload_len}字节"
        )

    # 提取载荷（只取声明长度的数据）
    payload = data[WRAPPER_HEADER_LENGTH:WRAPPER_HEADER_LENGTH + data_length]

    return WrapperFrame(
        version=version,
        src_wport=src_wport,
        dst_wport=dst_wport,
        data_length=data_length,
        payload_hex=bytes_to_hex(payload),
    )


def build_wpd(payload: bytes, src_wport: int = WPORT_CLIENT,
              dst_wport: int = WPORT_METER, version: int = 1) -> bytes:
    """
    构建Wrapper层帧

    Args:
        payload: 载荷数据（APDU等）
        src_wport: 源WPort，默认1（客户端）
        dst_wport: 目的WPort，默认16（电表）
        version: 版本号，默认1

    Returns:
        bytes: 完整的Wrapper帧数据（8字节头 + 载荷）
    """
    data_length = len(payload)

    # 构建8字节头
    header = struct.pack(">HHHH", version, src_wport, dst_wport, data_length)

    return header + payload


def is_wrapper_frame(data: bytes) -> bool:
    """
    检查数据是否可能是Wrapper帧

    通过检查前几个字节是否符合Wrapper帧特征来判断：
    - 版本号应为0x0001
    - 数据长度应与实际数据匹配

    Args:
        data: 待检查的数据

    Returns:
        bool: 是否可能是Wrapper帧
    """
    if len(data) < WRAPPER_HEADER_LENGTH:
        return False

    try:
        version, src_wport, dst_wport, data_length = struct.unpack(">HHHH", data[:8])
        # 版本号通常为1
        if version != 1:
            return False
        # 数据长度应合理（不小于0，不超过实际数据长度）
        if data_length < 0 or data_length > len(data) - WRAPPER_HEADER_LENGTH:
            # 可能是粘包，也可能不是
            # 只要长度声明合理，暂时认为是
            return data_length >= 0 and data_length < 65535
        return True
    except Exception:
        return False


def extract_wrapper_payload(data: bytes) -> Optional[bytes]:
    """
    从数据中提取Wrapper载荷（简化版，不抛异常）

    Args:
        data: 帧数据

    Returns:
        载荷字节，解析失败返回None
    """
    try:
        frame = parse_wpd(data)
        from app.utils.hex_utils import hex_to_bytes
        return hex_to_bytes(frame.payload_hex)
    except Exception:
        return None
