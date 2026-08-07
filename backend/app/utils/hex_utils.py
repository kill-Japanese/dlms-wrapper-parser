"""
十六进制数据工具函数
"""
import re
from typing import Union


def hex_to_bytes(hex_str: str) -> bytes:
    """
    将十六进制字符串转换为字节

    Args:
        hex_str: 十六进制字符串，可以带空格、换行、0x前缀等

    Returns:
        bytes: 转换后的字节

    Raises:
        ValueError: 如果输入包含无效的十六进制字符
    """
    if not hex_str:
        return b""

    # 移除空格、换行、0x前缀等常见格式
    s = str(hex_str).strip()
    # 移除0x/0X前缀（只移除开头的）
    s = re.sub(r'^0[xX]', '', s)
    # 移除空格、换行、制表符、冒号等分隔符
    cleaned = re.sub(r'[\s\r\n\t:]+', '', s)

    # 检查长度是否为偶数
    if len(cleaned) % 2 != 0:
        # 尝试容错：在末尾补"0"（最常见的截断情况）
        # 同时也尝试在开头补"0"，选择能成功解析的那个
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"十六进制字符串长度为奇数({len(cleaned)})，尝试自动补齐")

        # 尝试末尾补0
        try_padded_end = cleaned + "0"
        if re.match(r"^[0-9a-fA-F]*$", try_padded_end):
            cleaned = try_padded_end
        else:
            raise ValueError(f"十六进制字符串长度必须为偶数，当前长度: {len(cleaned)}")

    # 检查是否为有效十六进制
    if not re.match(r"^[0-9a-fA-F]*$", cleaned):
        raise ValueError("包含无效的十六进制字符")

    try:
        return bytes.fromhex(cleaned)
    except ValueError as e:
        raise ValueError(f"无效的十六进制字符串: {e}") from e


def bytes_to_hex(data: Union[bytes, bytearray, int]) -> str:
    """
    将字节转换为十六进制字符串（小写，无分隔符）

    Args:
        data: 字节数据或单个字节整数

    Returns:
        str: 十六进制字符串
    """
    if isinstance(data, int):
        return f"{data:02x}"
    return data.hex()


def format_hex(data: Union[bytes, bytearray], bytes_per_line: int = 16) -> str:
    """
    格式化十六进制数据为可读格式（带偏移量和ASCII显示）

    Args:
        data: 字节数据
        bytes_per_line: 每行显示的字节数

    Returns:
        str: 格式化后的十六进制字符串
    """
    if not data:
        return ""

    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        # 偏移量
        offset = f"{i:08x}"
        # 十六进制部分
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        # 补齐空格
        hex_part = hex_part.ljust(bytes_per_line * 3 - 1)
        # ASCII部分
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset}  {hex_part}  {ascii_part}")

    return "\n".join(lines)


def hex_str_to_list(hex_str: str) -> list:
    """
    将十六进制字符串转换为整数列表

    Args:
        hex_str: 十六进制字符串

    Returns:
        list: 整数字节列表
    """
    data = hex_to_bytes(hex_str)
    return list(data)


def int_to_hex(value: int, width: int = 2) -> str:
    """
    整数转固定宽度的十六进制字符串

    Args:
        value: 整数值
        width: 字节宽度（不是字符宽度）

    Returns:
        str: 十六进制字符串
    """
    if value < 0:
        # 处理负数 - 补码表示
        value = value & (2 ** (width * 8) - 1)
    return f"{value:0{width * 2}x}"


def reverse_bytes(data: Union[bytes, bytearray, str]) -> Union[bytes, str]:
    """
    反转字节序

    Args:
        data: 字节数据或十六进制字符串

    Returns:
        反转后的数据（与输入类型相同）
    """
    if isinstance(data, str):
        b = hex_to_bytes(data)
        return bytes_to_hex(b[::-1])
    return data[::-1]
