"""
BER (Basic Encoding Rules) / A-XDR 编码工具
用于DLMS/COSEM协议数据的编码和解码

DLMS使用的是BER的子集，也称为A-XDR (Application context XDR)
"""
from typing import Any, Tuple, Optional

# DLMS数据类型标签
DATA_TYPES = {
    0: "null-data",
    1: "array",
    2: "structure",
    3: "boolean",
    4: "bit-string",
    5: "double-long",  # int32
    6: "double-long-unsigned",  # uint32
    7: "octet-string",
    8: "visible-string",
    9: "utf8-string",
    10: "bcd",
    11: "integer",  # int8
    12: "long",  # int16
    13: "unsigned",  # uint8
    14: "long-unsigned",  # uint16
    15: "compact-array",
    16: "long64",  # int64
    17: "long64-unsigned",  # uint64
    18: "enum",
    19: "float",  # float32
    20: "double",  # float64
    21: "date-time",
    22: "date",
    23: "time",
    # 24-250: reserved
    251: "dont-care",
    252: "dont-care",
    253: "dependent",
    254: "no-selective-access",
    255: "no-data",
}

# 反向映射
DATA_TYPE_NAMES = {v: k for k, v in DATA_TYPES.items()}


def _decode_length(data: bytes, offset: int) -> Tuple[int, int]:
    """
    解码BER长度字段

    Args:
        data: 字节数据
        offset: 当前偏移量

    Returns:
        (length, new_offset)
    """
    if offset >= len(data):
        raise ValueError("数据不足，无法解码长度")

    first_byte = data[offset]
    if first_byte < 0x80:
        # 短形式 - 单字节长度
        return first_byte, offset + 1
    else:
        # 长形式 - 后续字节数由低7位指定
        num_bytes = first_byte & 0x7F
        if num_bytes == 0:
            raise ValueError("不支持的不确定长度")
        if offset + 1 + num_bytes > len(data):
            raise ValueError("数据不足，无法解码长度字段")
        length = 0
        for i in range(num_bytes):
            length = (length << 8) | data[offset + 1 + i]
        return length, offset + 1 + num_bytes


def _encode_length(length: int) -> bytes:
    """
    编码BER长度字段

    Args:
        length: 长度值

    Returns:
        编码后的长度字节
    """
    if length < 0x80:
        return bytes([length])
    elif length <= 0xFF:
        return bytes([0x81, length])
    elif length <= 0xFFFF:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    elif length <= 0xFFFFFF:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x84, (length >> 24) & 0xFF, (length >> 16) & 0xFF,
                      (length >> 8) & 0xFF, length & 0xFF])


def decode_data(data: bytes, offset: int = 0, data_type: Optional[int] = None) -> Tuple[Any, int, str]:
    """
    解码BER编码的数据

    Args:
        data: 字节数据
        offset: 起始偏移量
        data_type: 已知的数据类型标签（如果为None则从数据中读取）

    Returns:
        (value, new_offset, type_name)

    Raises:
        ValueError: 数据不足或格式错误
    """
    if offset >= len(data):
        raise ValueError(f"数据不足，offset={offset}, len={len(data)}")

    # 读取标签（数据类型）
    if data_type is None:
        tag = data[offset]
        offset += 1
    else:
        tag = data_type

    type_name = DATA_TYPES.get(tag, f"unknown({tag})")

    # 根据数据类型解码
    if tag == 0:  # null-data
        return None, offset, type_name

    elif tag == 1 or tag == 2:  # array / structure
        length, offset = _decode_length(data, offset)
        end_offset = offset + length
        items = []
        while offset < end_offset:
            item_value, offset, _ = decode_data(data, offset)
            items.append(item_value)
        return items, offset, type_name

    elif tag == 3:  # boolean
        length, offset = _decode_length(data, offset)
        if length == 0:
            return False, offset, type_name
        val = data[offset] != 0
        offset += length
        return val, offset, type_name

    elif tag == 4:  # bit-string
        length, offset = _decode_length(data, offset)
        bit_string = data[offset:offset + length]
        offset += length
        return bit_string, offset, type_name

    elif tag == 5:  # double-long (int32)
        length, offset = _decode_length(data, offset)
        if length != 4:
            raise ValueError(f"double-long 长度应为4，实际: {length}")
        val = int.from_bytes(data[offset:offset + 4], "big", signed=True)
        offset += 4
        return val, offset, type_name

    elif tag == 6:  # double-long-unsigned (uint32)
        length, offset = _decode_length(data, offset)
        if length != 4:
            raise ValueError(f"double-long-unsigned 长度应为4，实际: {length}")
        val = int.from_bytes(data[offset:offset + 4], "big", signed=False)
        offset += 4
        return val, offset, type_name

    elif tag == 7:  # octet-string
        length, offset = _decode_length(data, offset)
        val = data[offset:offset + length]
        offset += length
        return val, offset, type_name

    elif tag == 8:  # visible-string
        length, offset = _decode_length(data, offset)
        val = data[offset:offset + length].decode("ascii", errors="replace")
        offset += length
        return val, offset, type_name

    elif tag == 9:  # utf8-string
        length, offset = _decode_length(data, offset)
        val = data[offset:offset + length].decode("utf-8", errors="replace")
        offset += length
        return val, offset, type_name

    elif tag == 11:  # integer (int8)
        length, offset = _decode_length(data, offset)
        if length != 1:
            raise ValueError(f"integer 长度应为1，实际: {length}")
        val = int.from_bytes(data[offset:offset + 1], "big", signed=True)
        offset += 1
        return val, offset, type_name

    elif tag == 12:  # long (int16)
        length, offset = _decode_length(data, offset)
        if length != 2:
            raise ValueError(f"long 长度应为2，实际: {length}")
        val = int.from_bytes(data[offset:offset + 2], "big", signed=True)
        offset += 2
        return val, offset, type_name

    elif tag == 13:  # unsigned (uint8)
        length, offset = _decode_length(data, offset)
        if length != 1:
            raise ValueError(f"unsigned 长度应为1，实际: {length}")
        val = int.from_bytes(data[offset:offset + 1], "big", signed=False)
        offset += 1
        return val, offset, type_name

    elif tag == 14:  # long-unsigned (uint16)
        length, offset = _decode_length(data, offset)
        if length != 2:
            raise ValueError(f"long-unsigned 长度应为2，实际: {length}")
        val = int.from_bytes(data[offset:offset + 2], "big", signed=False)
        offset += 2
        return val, offset, type_name

    elif tag == 16:  # long64 (int64)
        length, offset = _decode_length(data, offset)
        if length != 8:
            raise ValueError(f"long64 长度应为8，实际: {length}")
        val = int.from_bytes(data[offset:offset + 8], "big", signed=True)
        offset += 8
        return val, offset, type_name

    elif tag == 17:  # long64-unsigned (uint64)
        length, offset = _decode_length(data, offset)
        if length != 8:
            raise ValueError(f"long64-unsigned 长度应为8，实际: {length}")
        val = int.from_bytes(data[offset:offset + 8], "big", signed=False)
        offset += 8
        return val, offset, type_name

    elif tag == 18:  # enum
        length, offset = _decode_length(data, offset)
        if length != 1:
            raise ValueError(f"enum 长度应为1，实际: {length}")
        val = data[offset]
        offset += 1
        return val, offset, type_name

    elif tag == 19:  # float (float32)
        import struct
        length, offset = _decode_length(data, offset)
        if length != 4:
            raise ValueError(f"float 长度应为4，实际: {length}")
        val = struct.unpack(">f", data[offset:offset + 4])[0]
        offset += 4
        return val, offset, type_name

    elif tag == 20:  # double (float64)
        import struct
        length, offset = _decode_length(data, offset)
        if length != 8:
            raise ValueError(f"double 长度应为8，实际: {length}")
        val = struct.unpack(">d", data[offset:offset + 8])[0]
        offset += 8
        return val, offset, type_name

    elif tag == 21:  # date-time
        length, offset = _decode_length(data, offset)
        # TODO: 完整解析date-time格式（12字节）
        dt_bytes = data[offset:offset + length]
        offset += length
        return dt_bytes.hex(), offset, type_name

    elif tag == 22:  # date
        length, offset = _decode_length(data, offset)
        # 5字节日期: year_high year_low month day day_of_week
        dt_bytes = data[offset:offset + length]
        offset += length
        return dt_bytes.hex(), offset, type_name

    elif tag == 23:  # time
        length, offset = _decode_length(data, offset)
        # 4字节时间: hour minute second hundredths
        dt_bytes = data[offset:offset + length]
        offset += length
        return dt_bytes.hex(), offset, type_name

    else:
        # 未知/保留类型 - 尝试按octet-string处理
        try:
            length, offset = _decode_length(data, offset)
            val = data[offset:offset + length]
            offset += length
            return val, offset, type_name
        except Exception:
            raise ValueError(f"不支持的数据类型: {tag} ({type_name})")


def encode_data(value: Any, data_type: str) -> bytes:
    """
    编码数据为BER格式

    Args:
        value: 数据值
        data_type: 数据类型名称

    Returns:
        bytes: 编码后的数据

    Raises:
        ValueError: 不支持的数据类型
    """
    tag = DATA_TYPE_NAMES.get(data_type)
    if tag is None:
        raise ValueError(f"未知的数据类型: {data_type}")

    if data_type == "null-data":
        return bytes([tag, 0])

    elif data_type == "boolean":
        val = 1 if value else 0
        return bytes([tag, 1, val])

    elif data_type in ("double-long", "double-long-unsigned"):
        signed = data_type == "double-long"
        val = int(value).to_bytes(4, "big", signed=signed)
        return bytes([tag]) + _encode_length(4) + val

    elif data_type in ("octet-string", "bit-string"):
        if isinstance(value, str):
            from app.utils.hex_utils import hex_to_bytes
            value = hex_to_bytes(value)
        return bytes([tag]) + _encode_length(len(value)) + bytes(value)

    elif data_type == "visible-string":
        val = str(value).encode("ascii")
        return bytes([tag]) + _encode_length(len(val)) + val

    elif data_type == "utf8-string":
        val = str(value).encode("utf-8")
        return bytes([tag]) + _encode_length(len(val)) + val

    elif data_type == "integer":
        val = int(value).to_bytes(1, "big", signed=True)
        return bytes([tag, 1]) + val

    elif data_type == "long":
        val = int(value).to_bytes(2, "big", signed=True)
        return bytes([tag, 2]) + val

    elif data_type == "unsigned":
        val = int(value).to_bytes(1, "big", signed=False)
        return bytes([tag, 1]) + val

    elif data_type == "long-unsigned":
        val = int(value).to_bytes(2, "big", signed=False)
        return bytes([tag, 2]) + val

    elif data_type == "long64":
        val = int(value).to_bytes(8, "big", signed=True)
        return bytes([tag, 8]) + val

    elif data_type == "long64-unsigned":
        val = int(value).to_bytes(8, "big", signed=False)
        return bytes([tag, 8]) + val

    elif data_type == "enum":
        val = int(value) & 0xFF
        return bytes([tag, 1, val])

    elif data_type in ("array", "structure"):
        # value应该是已编码好的字节，或者是元素列表
        if isinstance(value, (bytes, bytearray)):
            content = bytes(value)
        else:
            # TODO: 支持自动编码列表元素
            raise NotImplementedError("数组/结构的自动编码暂未实现")
        return bytes([tag]) + _encode_length(len(content)) + content

    else:
        raise ValueError(f"暂不支持编码的数据类型: {data_type}")
