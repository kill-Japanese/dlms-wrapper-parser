"""
BER (Basic Encoding Rules) / A-XDR 编码工具
用于DLMS/COSEM协议数据的编码和解码

DLMS使用的是BER的子集，也称为A-XDR (Application context XDR)

DLMS/COSEM 数据类型标签 (IEC 62056-62):
- 0x00 null-data
- 0x01 array
- 0x02 structure
- 0x03 boolean
- 0x04 bit-string
- 0x05 double-long (int32)
- 0x06 double-long-unsigned (uint32)
- 0x09 octet-string
- 0x0a visible-string
- 0x0b utf8-string
- 0x0f integer (int8)
- 0x10 long (int16)
- 0x11 unsigned (uint8)
- 0x12 long-unsigned (uint16)
- 0x13 compact-array
- 0x14 long64 (int64)
- 0x15 long64-unsigned (uint64)
- 0x16 enum
- 0x17 float32
- 0x18 float64 (double)
- 0x19 date-time
- 0x1a date
- 0x1b time
- 0x1c date-time (extended)
- 0xff don't-care / no-data / null
"""
from typing import Any, Tuple, Optional
import struct

# DLMS数据类型标签 -> 类型名称
DATA_TYPES = {
    0x00: "null-data",
    0x01: "array",
    0x02: "structure",
    0x03: "boolean",
    0x04: "bit-string",
    0x05: "double-long",       # int32
    0x06: "double-long-unsigned",  # uint32
    0x09: "octet-string",
    0x0a: "visible-string",
    0x0b: "utf8-string",
    0x0f: "integer",           # int8
    0x10: "long",              # int16
    0x11: "unsigned",          # uint8
    0x12: "long-unsigned",     # uint16
    0x13: "compact-array",
    0x14: "long64",            # int64
    0x15: "long64-unsigned",   # uint64
    0x16: "enum",
    0x17: "float32",
    0x18: "float64",
    0x19: "date-time",
    0x1a: "date",
    0x1b: "time",
    0xff: "dont-care",         # also "no-data" / null
}

# 反向映射：类型名称 -> 标签
DATA_TYPE_NAMES = {v: k for k, v in DATA_TYPES.items()}
# 添加别名
DATA_TYPE_NAMES["bool"] = 0x03
DATA_TYPE_NAMES["double"] = 0x18
DATA_TYPE_NAMES["float"] = 0x17
DATA_TYPE_NAMES["no-data"] = 0xff
DATA_TYPE_NAMES["null"] = 0xff

# 定长类型及其字节大小（A-XDR 编码中不带长度字节）
FIXED_TYPE_SIZES = {
    0x03: 1,   # boolean
    0x05: 4,   # double-long (int32)
    0x06: 4,   # double-long-unsigned (uint32)
    0x0f: 1,   # integer (int8)
    0x10: 2,   # long (int16)
    0x11: 1,   # unsigned (uint8)
    0x12: 2,   # long-unsigned (uint16)
    0x14: 8,   # long64 (int64)
    0x15: 8,   # long64-unsigned (uint64)
    0x16: 1,   # enum
    0x17: 4,   # float32
    0x18: 8,   # float64
    0x19: 12,  # date-time
    0x1a: 5,   # date
    0x1b: 4,   # time
}


def _extract_value_from_encoded(encoded: bytes) -> bytes:
    """
    从编码后的数据元素中提取值部分（去掉tag和可选的length）。
    A-XDR 编码中定长类型没有length字节。
    """
    if not encoded:
        return b""
    tag = encoded[0]
    fixed_size = FIXED_TYPE_SIZES.get(tag)
    if fixed_size is not None:
        return encoded[1:1 + fixed_size]
    else:
        length, pos = _decode_length(encoded, 1)
        return encoded[pos:pos + length]


def _is_valid_data_tag(b: int) -> bool:
    """检查字节是否是有效的DLMS数据类型标签"""
    return b in DATA_TYPES


def _decode_fixed_value(data: bytes, offset: int, size: int, signed: bool, type_name: str) -> Tuple[Any, int]:
    """
    解码定长类型值（A-XDR 编码：无长度字节，直接读取 size 字节）。
    同时兼容旧 BER 编码：当 data[offset]==size 且 A-XDR 解析后偏移越界时回退到 BER。

    Args:
        data: 字节数据
        offset: 当前偏移量（tag之后的第一个字节）
        size: 期望的字节长度
        signed: 是否有符号
        type_name: 类型名称（用于错误信息）

    Returns:
        (value, new_offset)
    """
    if offset >= len(data):
        raise ValueError(f"{type_name} 数据不足，offset={offset}")

    # A-XDR: 直接读取 size 字节（无长度字节）
    if offset + size <= len(data):
        val = int.from_bytes(data[offset:offset + size], "big", signed=signed)
        return val, offset + size

    # BER 回退: 如果数据不足 A-XDR 但可能是 BER 格式（有长度字节）
    # 尝试读取长度字节
    try:
        length, ber_offset = _decode_length(data, offset)
        if length == size and ber_offset + size <= len(data):
            val = int.from_bytes(data[ber_offset:ber_offset + size], "big", signed=signed)
            return val, ber_offset + size
    except Exception:
        pass

    raise ValueError(f"{type_name} 数据不足，需要{size}字节，实际只有{len(data) - offset}字节")


def _decode_length(data: bytes, offset: int) -> Tuple[int, int]:
    """
    解码BER长度字段

    Args:
        data: 字节数据
        offset: 当前偏移量

    Returns:
        (length, new_offset)

    Raises:
        ValueError: 数据不足或格式错误
    """
    if offset >= len(data):
        raise ValueError(f"数据不足，无法解码长度，offset={offset}, len={len(data)}")

    first_byte = data[offset]
    if first_byte < 0x80:
        # 短形式 - 单字节长度
        return first_byte, offset + 1
    else:
        # 长形式 - 后续字节数由低7位指定
        num_bytes = first_byte & 0x7F
        if num_bytes == 0:
            raise ValueError("不支持的不确定长度")
        if num_bytes > 4:
            raise ValueError(f"长度字段过长: {num_bytes}字节")
        if offset + 1 + num_bytes > len(data):
            raise ValueError(f"数据不足，无法解码长度字段，需要{num_bytes}字节，实际只有{len(data) - offset - 1}字节")
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


def _decode_date_time(data: bytes, length: int) -> dict:
    """
    解析date-time数据 (12字节)

    格式:
    - year (2 bytes, big-endian)
    - month (1 byte)
    - day_of_month (1 byte)
    - day_of_week (1 byte)
    - hour (1 byte)
    - minute (1 byte)
    - second (1 byte)
    - hundredths (1 byte)
    - deviation (2 bytes, signed, minutes deviation from UTC)
    - status (1 byte)

    Returns:
        dict: 解析后的日期时间字段
    """
    result = {
        "year": None, "month": None, "day": None, "weekday": None,
        "hour": None, "minute": None, "second": None, "hundredths": None,
        "deviation": None, "status": None, "raw": data.hex()
    }

    if length >= 2:
        result["year"] = int.from_bytes(data[0:2], "big", signed=False)
    if length >= 3:
        result["month"] = data[2]
    if length >= 4:
        result["day"] = data[3]
    if length >= 5:
        result["weekday"] = data[4]
    if length >= 6:
        result["hour"] = data[5]
    if length >= 7:
        result["minute"] = data[6]
    if length >= 8:
        result["second"] = data[7]
    if length >= 9:
        result["hundredths"] = data[8]
    if length >= 11:
        result["deviation"] = int.from_bytes(data[9:11], "big", signed=True)
    if length >= 12:
        result["status"] = data[11]

    # 生成可读字符串
    try:
        if result["year"] is not None and result["month"] is not None:
            result["iso"] = (
                f"{result['year']:04d}-{result['month']:02d}-{result['day']:02d} "
                f"{result['hour']:02d}:{result['minute']:02d}:{result['second']:02d}"
                f".{result.get('hundredths', 0):02d}"
            )
    except Exception:
        pass

    return result


def _decode_date(data: bytes, length: int) -> dict:
    """
    解析date数据 (5字节)

    格式:
    - year (2 bytes)
    - month (1 byte)
    - day_of_month (1 byte)
    - day_of_week (1 byte)
    """
    result = {
        "year": None, "month": None, "day": None, "weekday": None,
        "raw": data.hex()
    }

    if length >= 2:
        result["year"] = int.from_bytes(data[0:2], "big", signed=False)
    if length >= 3:
        result["month"] = data[2]
    if length >= 4:
        result["day"] = data[3]
    if length >= 5:
        result["weekday"] = data[4]

    try:
        if result["year"] is not None and result["month"] is not None:
            result["iso"] = f"{result['year']:04d}-{result['month']:02d}-{result['day']:02d}"
    except Exception:
        pass

    return result


def _decode_time(data: bytes, length: int) -> dict:
    """
    解析time数据 (4字节)

    格式:
    - hour (1 byte)
    - minute (1 byte)
    - second (1 byte)
    - hundredths (1 byte)
    """
    result = {
        "hour": None, "minute": None, "second": None, "hundredths": None,
        "raw": data.hex()
    }

    if length >= 1:
        result["hour"] = data[0]
    if length >= 2:
        result["minute"] = data[1]
    if length >= 3:
        result["second"] = data[2]
    if length >= 4:
        result["hundredths"] = data[3]

    try:
        if result["hour"] is not None:
            result["iso"] = (
                f"{result['hour']:02d}:{result['minute']:02d}:"
                f"{result['second']:02d}.{result.get('hundredths', 0):02d}"
            )
    except Exception:
        pass

    return result


def _encode_date_time(dt_dict: dict) -> bytes:
    """
    编码date-time为12字节数据
    """
    result = bytearray(12)
    year = dt_dict.get("year", 0)
    result[0:2] = year.to_bytes(2, "big", signed=False)
    result[2] = dt_dict.get("month", 1)
    result[3] = dt_dict.get("day", 1)
    result[4] = dt_dict.get("weekday", 0)
    result[5] = dt_dict.get("hour", 0)
    result[6] = dt_dict.get("minute", 0)
    result[7] = dt_dict.get("second", 0)
    result[8] = dt_dict.get("hundredths", 0)
    dev = dt_dict.get("deviation", 0)
    result[9:11] = dev.to_bytes(2, "big", signed=True)
    result[11] = dt_dict.get("status", 0)
    return bytes(result)


def _encode_date(d_dict: dict) -> bytes:
    """编码date为5字节数据"""
    result = bytearray(5)
    year = d_dict.get("year", 0)
    result[0:2] = year.to_bytes(2, "big", signed=False)
    result[2] = d_dict.get("month", 1)
    result[3] = d_dict.get("day", 1)
    result[4] = d_dict.get("weekday", 0)
    return bytes(result)


def _encode_time(t_dict: dict) -> bytes:
    """编码time为4字节数据"""
    result = bytearray(4)
    result[0] = t_dict.get("hour", 0)
    result[1] = t_dict.get("minute", 0)
    result[2] = t_dict.get("second", 0)
    result[3] = t_dict.get("hundredths", 0)
    return bytes(result)


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
    if tag == 0x00:  # null-data
        return None, offset, type_name

    elif tag == 0xFF:  # don't-care / no-data / null
        return None, offset, type_name

    elif tag in (0x01, 0x02):  # array / structure
        # DLMS A-XDR: 长度字段表示元素个数（不是字节数）
        count, offset = _decode_length(data, offset)
        items = []
        for _ in range(count):
            if offset >= len(data):
                break
            try:
                item_value, offset, _ = decode_data(data, offset)
                items.append(item_value)
            except Exception:
                break
        return items, offset, type_name

    elif tag == 0x03:  # boolean
        # A-XDR: 1 byte value, no length byte
        if offset >= len(data):
            raise ValueError(f"boolean 数据不足，offset={offset}")
        val = data[offset] != 0
        return val, offset + 1, type_name

    elif tag == 0x04:  # bit-string
        length, offset = _decode_length(data, offset)
        # 第一个字节是未使用的位数
        if length == 0:
            return b"", offset, type_name
        unused_bits = data[offset]
        bit_bytes = data[offset + 1:offset + length]
        offset += length
        # 返回 (bit_count, bytes)
        total_bits = (length - 1) * 8 - unused_bits
        return {"bit_count": total_bits, "bytes": bit_bytes, "unused_bits": unused_bits}, offset, type_name

    elif tag == 0x05:  # double-long (int32)
        val, offset = _decode_fixed_value(data, offset, 4, signed=True, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x06:  # double-long-unsigned (uint32)
        val, offset = _decode_fixed_value(data, offset, 4, signed=False, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x09:  # octet-string
        length, offset = _decode_length(data, offset)
        if offset + length > len(data):
            raise ValueError(f"octet-string 数据不足，需要{length}字节，实际只有{len(data) - offset}字节")
        val = data[offset:offset + length]
        offset += length
        return val, offset, type_name

    elif tag == 0x0a:  # visible-string
        length, offset = _decode_length(data, offset)
        if offset + length > len(data):
            raise ValueError(f"visible-string 数据不足，需要{length}字节，实际只有{len(data) - offset}字节")
        val = data[offset:offset + length].decode("ascii", errors="replace")
        offset += length
        return val, offset, type_name

    elif tag == 0x0b:  # utf8-string
        length, offset = _decode_length(data, offset)
        if offset + length > len(data):
            raise ValueError(f"utf8-string 数据不足，需要{length}字节，实际只有{len(data) - offset}字节")
        val = data[offset:offset + length].decode("utf-8", errors="replace")
        offset += length
        return val, offset, type_name

    elif tag == 0x0f:  # integer (int8)
        val, offset = _decode_fixed_value(data, offset, 1, signed=True, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x10:  # long (int16)
        val, offset = _decode_fixed_value(data, offset, 2, signed=True, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x11:  # unsigned (uint8)
        val, offset = _decode_fixed_value(data, offset, 1, signed=False, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x12:  # long-unsigned (uint16)
        val, offset = _decode_fixed_value(data, offset, 2, signed=False, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x13:  # compact-array
        # compact-array 格式:
        # tag (0x13) + array_contents_description + item_count + packed_items
        # array_contents_description 描述每个元素的结构
        # 先读取长度
        length, offset = _decode_length(data, offset)
        end_offset = offset + length

        # 第一个元素是 array_contents_description (structure)
        desc_value, offset, _ = decode_data(data, offset)

        # 第二个元素是 item_count (通常是 unsigned 或 long-unsigned)
        item_count_val, offset, _ = decode_data(data, offset)
        item_count = item_count_val if isinstance(item_count_val, int) else 0

        items = []
        # 剩余数据是紧凑排列的元素（没有tag和length前缀）
        if isinstance(desc_value, list) and len(desc_value) > 0 and offset < end_offset:
            # 简单处理：将剩余数据按描述递归解码
            # 实际compact-array解码比较复杂，这里做简化处理
            remaining_data = data[offset:end_offset]
            items = _decode_compact_array_items(remaining_data, desc_value, item_count)

        offset = end_offset
        return {"description": desc_value, "count": item_count, "items": items}, offset, type_name

    elif tag == 0x14:  # long64 (int64)
        val, offset = _decode_fixed_value(data, offset, 8, signed=True, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x15:  # long64-unsigned (uint64)
        val, offset = _decode_fixed_value(data, offset, 8, signed=False, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x16:  # enum
        val, offset = _decode_fixed_value(data, offset, 1, signed=False, type_name=type_name)
        return val, offset, type_name

    elif tag == 0x17:  # float32
        # A-XDR: 4 bytes, no length byte
        if offset + 4 > len(data):
            raise ValueError(f"float32 数据不足，需要4字节")
        val = struct.unpack(">f", data[offset:offset + 4])[0]
        return val, offset + 4, type_name

    elif tag == 0x18:  # float64 (double)
        # A-XDR: 8 bytes, no length byte
        if offset + 8 > len(data):
            raise ValueError(f"float64 数据不足，需要8字节")
        val = struct.unpack(">d", data[offset:offset + 8])[0]
        return val, offset + 8, type_name

    elif tag == 0x19:  # date-time
        # A-XDR: 12 bytes, no length byte
        dt_size = 12
        if offset + dt_size <= len(data):
            dt_bytes = data[offset:offset + dt_size]
            return _decode_date_time(dt_bytes, dt_size), offset + dt_size, type_name
        # BER fallback
        length, offset = _decode_length(data, offset)
        dt_bytes = data[offset:offset + length]
        offset += length
        return _decode_date_time(dt_bytes, length), offset, type_name

    elif tag == 0x1a:  # date
        # A-XDR: 5 bytes, no length byte
        d_size = 5
        if offset + d_size <= len(data):
            d_bytes = data[offset:offset + d_size]
            return _decode_date(d_bytes, d_size), offset + d_size, type_name
        # BER fallback
        length, offset = _decode_length(data, offset)
        d_bytes = data[offset:offset + length]
        offset += length
        return _decode_date(d_bytes, length), offset, type_name

    elif tag == 0x1b:  # time
        # A-XDR: 4 bytes, no length byte
        t_size = 4
        if offset + t_size <= len(data):
            t_bytes = data[offset:offset + t_size]
            return _decode_time(t_bytes, t_size), offset + t_size, type_name
        # BER fallback
        length, offset = _decode_length(data, offset)
        t_bytes = data[offset:offset + length]
        offset += length
        return _decode_time(t_bytes, length), offset, type_name

    else:
        # 未知/保留类型 - 尝试按octet-string处理
        try:
            length, offset = _decode_length(data, offset)
            val = data[offset:offset + length]
            offset += length
            return val, offset, type_name
        except Exception:
            raise ValueError(f"不支持的数据类型: {tag} ({type_name})")


def _decode_compact_array_items(data: bytes, description: list, item_count: int) -> list:
    """
    解码compact-array的紧凑数据项

    Args:
        data: 紧凑数据字节
        description: 元素结构描述（来自array_contents_description）
        item_count: 元素个数

    Returns:
        list: 解码后的元素列表
    """
    items = []
    offset = 0

    # 计算每个元素的固定大小（仅支持简单类型）
    def _get_type_size(type_tag):
        size_map = {
            0x03: 1,  # boolean
            0x05: 4,  # double-long
            0x06: 4,  # double-long-unsigned
            0x0f: 1,  # integer
            0x10: 2,  # long
            0x11: 1,  # unsigned
            0x12: 2,  # long-unsigned
            0x14: 8,  # long64
            0x15: 8,  # long64-unsigned
            0x16: 1,  # enum
            0x17: 4,  # float32
            0x18: 8,  # float64
        }
        return size_map.get(type_tag, None)

    # 简化处理：如果描述是单个类型且有固定大小，直接按固定大小解码
    try:
        if isinstance(description, list) and len(description) == 1:
            type_tag = description[0] if isinstance(description[0], int) else None
            if type_tag and _get_type_size(type_tag):
                sz = _get_type_size(type_tag)
                for _ in range(item_count):
                    if offset + sz > len(data):
                        break
                    val_data = data[offset:offset + sz]
                    # 用data_type方式解码
                    val, _, _ = decode_data(bytes([type_tag]) + bytes([sz]) + val_data, 0)
                    items.append(val)
                    offset += sz
    except Exception:
        pass

    return items


def encode_data(value: Any, type_spec: Any = None) -> bytes:
    """
    编码数据为BER格式

    Args:
        value: 数据值
        type_spec: 数据类型，可以是:
            - 字符串类型名称 (如 "double-long")
            - 整数类型标签 (如 0x06)
            - None: 尝试自动推断类型（仅支持简单类型）

    Returns:
        bytes: 编码后的数据 (tag + length + value)

    Raises:
        ValueError: 不支持的数据类型或参数错误
    """
    # 解析类型
    tag = None
    type_name = None

    if isinstance(type_spec, int):
        tag = type_spec
        type_name = DATA_TYPES.get(tag, f"unknown({tag})")
    elif isinstance(type_spec, str):
        type_name = type_spec.lower()
        tag = DATA_TYPE_NAMES.get(type_name)
        if tag is None:
            raise ValueError(f"未知的数据类型: {type_spec}")
    else:
        # 自动推断类型
        tag, type_name = _infer_type(value)

    return _encode_by_tag(value, tag, type_name)


def _infer_type(value: Any) -> Tuple[int, str]:
    """根据值自动推断数据类型"""
    if value is None:
        return 0x00, "null-data"
    elif isinstance(value, bool):
        return 0x03, "boolean"
    elif isinstance(value, int):
        if -128 <= value <= 127:
            return 0x0f, "integer"
        elif -32768 <= value <= 32767:
            return 0x10, "long"
        elif -2147483648 <= value <= 2147483647:
            return 0x05, "double-long"
        else:
            return 0x14, "long64"
    elif isinstance(value, float):
        return 0x18, "float64"
    elif isinstance(value, bytes):
        return 0x09, "octet-string"
    elif isinstance(value, str):
        return 0x0b, "utf8-string"
    elif isinstance(value, (list, tuple)):
        return 0x02, "structure"
    elif isinstance(value, dict) and "year" in value and "hour" in value:
        return 0x19, "date-time"
    elif isinstance(value, dict) and "year" in value:
        return 0x1a, "date"
    elif isinstance(value, dict) and "hour" in value:
        return 0x1b, "time"
    else:
        return 0x09, "octet-string"


def _encode_by_tag(value: Any, tag: int, type_name: str) -> bytes:
    """根据tag编码值"""
    # null-data / don't-care
    if tag in (0x00, 0xFF):
        return bytes([tag])

    # boolean
    elif tag == 0x03:
        val = 1 if value else 0
        return bytes([tag, val])

    # bit-string
    elif tag == 0x04:
        if isinstance(value, dict):
            bit_bytes = value.get("bytes", b"")
            unused = value.get("unused_bits", 0)
        elif isinstance(value, (bytes, bytearray)):
            bit_bytes = bytes(value)
            unused = 0
        else:
            bit_bytes = b""
            unused = 0
        content = bytes([unused]) + bit_bytes
        return bytes([tag]) + _encode_length(len(content)) + content

    # double-long (int32)
    elif tag == 0x05:
        val = int(value).to_bytes(4, "big", signed=True)
        return bytes([tag]) + val

    # double-long-unsigned (uint32)
    elif tag == 0x06:
        val = int(value).to_bytes(4, "big", signed=False)
        return bytes([tag]) + val

    # octet-string
    elif tag == 0x09:
        if isinstance(value, str):
            from app.utils.hex_utils import hex_to_bytes
            value = hex_to_bytes(value)
        val = bytes(value)
        return bytes([tag]) + _encode_length(len(val)) + val

    # visible-string
    elif tag == 0x0a:
        val = str(value).encode("ascii", errors="replace")
        return bytes([tag]) + _encode_length(len(val)) + val

    # utf8-string
    elif tag == 0x0b:
        val = str(value).encode("utf-8")
        return bytes([tag]) + _encode_length(len(val)) + val

    # integer (int8)
    elif tag == 0x0f:
        val = int(value).to_bytes(1, "big", signed=True)
        return bytes([tag]) + val

    # long (int16)
    elif tag == 0x10:
        val = int(value).to_bytes(2, "big", signed=True)
        return bytes([tag]) + val

    # unsigned (uint8)
    elif tag == 0x11:
        val = int(value).to_bytes(1, "big", signed=False)
        return bytes([tag]) + val

    # long-unsigned (uint16)
    elif tag == 0x12:
        val = int(value).to_bytes(2, "big", signed=False)
        return bytes([tag]) + val

    # compact-array
    elif tag == 0x13:
        if isinstance(value, dict):
            desc = value.get("description", [])
            items = value.get("items", [])
        elif isinstance(value, (list, tuple)):
            items = list(value)
            desc = None
        else:
            items = []
            desc = None

        # 编码描述部分
        if desc is None:
            # 从第一个元素推断
            if items:
                first_tag, _ = _infer_type(items[0])
                desc = [first_tag]
            else:
                desc = [0x06]  # 默认double-long-unsigned

        # 编码描述 (structure of type tags)
        desc_bytes = b""
        for d in desc:
            if isinstance(d, int):
                desc_bytes += encode_data(None, d)  # 仅tag+length
                # 实际上compact-array的描述是类型编码，需要特殊处理
                # 这里简化：每个描述项是一个数据类型
                desc_bytes = desc_bytes  # 保持原样
            else:
                desc_bytes += encode_data(d)

        # 编码item count
        count_bytes = encode_data(len(items), "long-unsigned")

        # 编码紧凑数据项
        items_bytes = b""
        for item in items:
            if isinstance(item, (list, tuple)):
                # 结构元素，编码每个字段（去掉tag和可选length，只保留value部分）
                for i, field_val in enumerate(item):
                    field_tag = desc[i] if i < len(desc) else None
                    if field_tag:
                        encoded = encode_data(field_val, field_tag)
                        items_bytes += _extract_value_from_encoded(encoded)
            else:
                # 简单类型
                if desc and isinstance(desc[0], int):
                    encoded = encode_data(item, desc[0])
                    items_bytes += _extract_value_from_encoded(encoded)
                else:
                    encoded = encode_data(item)
                    items_bytes += encoded

        content = count_bytes + items_bytes
        # 注意：compact-array的完整编码比较复杂，这里是简化版本
        return bytes([tag]) + _encode_length(len(content)) + content

    # long64 (int64)
    elif tag == 0x14:
        val = int(value).to_bytes(8, "big", signed=True)
        return bytes([tag]) + val

    # long64-unsigned (uint64)
    elif tag == 0x15:
        val = int(value).to_bytes(8, "big", signed=False)
        return bytes([tag]) + val

    # enum
    elif tag == 0x16:
        val = int(value) & 0xFF
        return bytes([tag, val])

    # float32
    elif tag == 0x17:
        val = struct.pack(">f", float(value))
        return bytes([tag]) + val

    # float64
    elif tag == 0x18:
        val = struct.pack(">d", float(value))
        return bytes([tag]) + val

    # date-time
    elif tag == 0x19:
        if isinstance(value, dict):
            dt_bytes = _encode_date_time(value)
        elif isinstance(value, (bytes, bytearray)):
            dt_bytes = bytes(value)
        else:
            dt_bytes = bytes(12)
        return bytes([tag]) + dt_bytes

    # date
    elif tag == 0x1a:
        if isinstance(value, dict):
            d_bytes = _encode_date(value)
        elif isinstance(value, (bytes, bytearray)):
            d_bytes = bytes(value)
        else:
            d_bytes = bytes(5)
        return bytes([tag]) + d_bytes

    # time
    elif tag == 0x1b:
        if isinstance(value, dict):
            t_bytes = _encode_time(value)
        elif isinstance(value, (bytes, bytearray)):
            t_bytes = bytes(value)
        else:
            t_bytes = bytes(4)
        return bytes([tag]) + t_bytes

    # array / structure
    elif tag in (0x01, 0x02):
        content = b""
        if isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], (str, int)):
                    # (value, type_spec) 形式
                    content += encode_data(item[0], item[1])
                elif isinstance(item, dict) and "type" in item and "value" in item:
                    # {"type": ..., "value": ...} 形式
                    content += encode_data(item["value"], item["type"])
                else:
                    # 自动推断类型
                    content += encode_data(item)
        elif isinstance(value, (bytes, bytearray)):
            content = bytes(value)

        return bytes([tag]) + _encode_length(len(content)) + content

    else:
        raise ValueError(f"暂不支持编码的数据类型: {type_name} (tag=0x{tag:02x})")
