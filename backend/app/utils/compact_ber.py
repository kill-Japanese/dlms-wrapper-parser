"""
DLMS 紧凑 BER 编码工具
用于 DataNotification 等使用紧凑编码的场景

紧凑编码规则 (DLMS A-XDR compact encoding):
- 固定长度类型: tag + value (无 length 字段)
- 可变长度类型 (octet-string, visible-string, etc.): tag + length + value
- structure, array: tag + num_elements + elements (length = 元素个数)
- null-data, dont-care: 只有 tag，无 value
"""
from typing import Any, Tuple, Optional

# 固定长度类型: tag -> (value_bytes, type_name)
FIXED_LENGTH_TYPES = {
    0x00: (0, "null-data"),
    0x03: (1, "boolean"),
    0x05: (4, "double-long"),       # int32
    0x06: (4, "double-long-unsigned"),  # uint32
    0x0F: (1, "integer"),           # int8
    0x10: (2, "long"),              # int16
    0x11: (1, "unsigned"),          # uint8
    0x12: (2, "long-unsigned"),     # uint16
    0x14: (8, "long64"),            # int64
    0x15: (8, "long64-unsigned"),   # uint64
    0x16: (1, "enum"),              # uint8
    0x17: (4, "float32"),
    0x18: (8, "float64"),
    0x19: (12, "date-time"),
    0x1A: (5, "date"),
    0x1B: (4, "time"),
    0xFF: (0, "dont-care"),
}

# 可变长度类型: tag -> type_name
VARIABLE_LENGTH_TYPES = {
    0x04: "bit-string",
    0x09: "octet-string",
    0x0A: "visible-string",
    0x0B: "utf8-string",
}

# 元素计数类型 (length = 元素个数)
COUNT_TYPES = {
    0x01: "array",
    0x02: "structure",
}


def decode_compact_length(data: bytes, offset: int) -> Tuple[int, int]:
    """
    解码可变长度类型的长度字段（字节数）
    
    紧凑编码中，可变长度类型的 length 字段：
    - 如果第一个字节 < 0x80，就是长度值
    - 如果第一个字节 >= 0x80，低 7 位表示后续长度字节数
    """
    if offset >= len(data):
        raise ValueError(f"数据不足，无法解码长度，offset={offset}")
    
    first_byte = data[offset]
    if first_byte < 0x80:
        return first_byte, offset + 1
    else:
        num_bytes = first_byte & 0x7F
        if num_bytes == 0:
            raise ValueError("不支持的不确定长度")
        if offset + num_bytes >= len(data):
            raise ValueError(f"长度字段数据不足")
        length = int.from_bytes(data[offset + 1:offset + 1 + num_bytes], "big")
        return length, offset + 1 + num_bytes


def decode_compact_data(data: bytes, offset: int = 0, max_depth: int = 30, lenient: bool = False) -> Tuple[Any, int, str]:
    """
    解码 DLMS 紧凑 BER 编码的数据
    
    Args:
        data: 字节数据
        offset: 起始偏移量
        max_depth: 最大递归深度
        lenient: 是否宽容模式（数据不足时不抛出异常，返回已解析的部分）
    
    Returns:
        (value, new_offset, type_name)
    """
    if offset >= len(data):
        raise ValueError(f"数据不足，offset={offset}, len={len(data)}")
    
    if max_depth <= 0:
        raise ValueError("超过最大递归深度")
    
    tag = data[offset]
    offset += 1
    
    # 固定长度类型
    if tag in FIXED_LENGTH_TYPES:
        val_len, type_name = FIXED_LENGTH_TYPES[tag]
        val_end = offset + val_len
        
        if val_end > len(data):
            raise ValueError(f"{type_name} 数据不足，需要{val_len}字节，实际只有{len(data) - offset}字节")
        
        val_bytes = data[offset:val_end]
        
        if val_len == 0:
            value = None
        elif type_name == "boolean":
            value = bool(val_bytes[0])
        elif type_name == "enum":
            value = val_bytes[0]
        elif type_name in ("float32", "float64"):
            import struct
            fmt = '>f' if type_name == "float32" else '>d'
            value = struct.unpack(fmt, val_bytes)[0]
        elif type_name in ("date-time", "date", "time"):
            value = val_bytes  # 返回原始字节，由上层解析
        elif "unsigned" in type_name or type_name in ("long64-unsigned",):
            value = int.from_bytes(val_bytes, "big", signed=False)
        elif "long" in type_name or "integer" in type_name or type_name in ("double-long", "long64"):
            value = int.from_bytes(val_bytes, "big", signed=True)
        else:
            value = val_bytes
        
        return value, val_end, type_name
    
    # 可变长度类型
    if tag in VARIABLE_LENGTH_TYPES:
        type_name = VARIABLE_LENGTH_TYPES[tag]
        length, offset = decode_compact_length(data, offset)
        val_end = offset + length
        
        if val_end > len(data):
            raise ValueError(f"{type_name} 数据不足，需要{length}字节，实际只有{len(data) - offset}字节")
        
        value = data[offset:val_end]
        
        # 对于字符串类型，尝试解码
        if type_name == "visible-string":
            try:
                value = value.decode("ascii", errors="replace")
            except:
                pass
        elif type_name == "utf8-string":
            try:
                value = value.decode("utf-8", errors="replace")
            except:
                pass
        
        return value, val_end, type_name
    
    # 元素计数类型 (array / structure)
    if tag in COUNT_TYPES:
        type_name = COUNT_TYPES[tag]
        num_elements = data[offset]  # 单字节元素个数 (0-255)
        offset += 1
        
        items = []
        for i in range(num_elements):
            if offset >= len(data):
                if lenient:
                    # 宽容模式：数据不足时返回已解析的部分
                    break
                raise ValueError(f"{type_name} 数据不足，预期{num_elements}个元素，实际只有{i}个")
            try:
                item_value, offset, _ = decode_compact_data(data, offset, max_depth - 1, lenient)
                items.append(item_value)
            except ValueError as e:
                if lenient:
                    break
                raise ValueError(f"{type_name} 第{i}个元素解析失败: {e}") from e
        
        return items, offset, type_name
    
    # 未知类型
    type_name = f"unknown_0x{tag:02X}"
    return None, offset, type_name


def encode_compact_data(value: Any, type_name: str) -> bytes:
    """
    编码为 DLMS 紧凑 BER 格式（简化版，用于测试）
    """
    # TODO: 实现编码
    raise NotImplementedError("紧凑编码暂未实现")
