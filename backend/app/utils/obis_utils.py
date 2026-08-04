"""
OBIS码工具函数
OBIS (Object Identification System) - IEC 62056-61
格式: A-B:C.D.E.F  (6个字节)
"""
import re
from typing import Union, Tuple


def obis_str_to_bytes(obis: str) -> bytes:
    """
    将OBIS字符串转换为6字节数据

    支持的格式:
    - "1-0:1.8.0.255" (标准格式)
    - "1.0.1.8.0.255" (点分隔)
    - "1-0:1.8.0*255" (星号分隔F)
    - "0100010800FF" (十六进制字符串)

    Args:
        obis: OBIS字符串

    Returns:
        bytes: 6字节OBIS码

    Raises:
        ValueError: 如果OBIS格式无效
    """
    if not obis:
        raise ValueError("OBIS码不能为空")

    # 检查是否为纯十六进制字符串（12个十六进制字符）
    if re.match(r"^[0-9a-fA-F]{12}$", obis.strip()):
        return bytes.fromhex(obis.strip())

    # 解析标准格式 A-B:C.D.E.F
    # 先把所有分隔符替换成点
    normalized = obis.strip().replace("-", ".").replace(":", ".").replace("*", ".")

    parts = normalized.split(".")
    if len(parts) != 6:
        raise ValueError(f"OBIS码必须包含6个部分，当前有 {len(parts)} 个: {obis}")

    try:
        values = [int(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"OBIS码包含无效数字: {obis}") from e

    for v in values:
        if v < 0 or v > 255:
            raise ValueError(f"OBIS码每个部分必须在0-255范围内: {obis}")

    return bytes(values)


def obis_bytes_to_str(obis_bytes: bytes, format_type: str = "standard") -> str:
    """
    将6字节OBIS码转换为字符串

    Args:
        obis_bytes: 6字节OBIS数据
        format_type: 输出格式
            - "standard": A-B:C.D.E.F (默认)
            - "dotted": A.B.C.D.E.F
            - "hex": 12字符十六进制

    Returns:
        str: OBIS字符串

    Raises:
        ValueError: 如果字节长度不为6
    """
    if len(obis_bytes) != 6:
        raise ValueError(f"OBIS码必须为6字节，当前长度: {len(obis_bytes)}")

    a, b, c, d, e, f = list(obis_bytes)

    if format_type == "standard":
        return f"{a}-{b}:{c}.{d}.{e}.{f}"
    elif format_type == "dotted":
        return f"{a}.{b}.{c}.{d}.{e}.{f}"
    elif format_type == "hex":
        return obis_bytes.hex()
    else:
        raise ValueError(f"未知的格式类型: {format_type}")


def normalize_obis(obis: Union[str, bytes, list, tuple]) -> Tuple[int, ...]:
    """
    将OBIS码统一为6字节元组，用于比较和索引

    Args:
        obis: OBIS码（字符串、字节、列表或元组）

    Returns:
        tuple: 6个整数组成的元组 (A, B, C, D, E, F)

    Raises:
        ValueError: 如果OBIS格式无效
    """
    if isinstance(obis, (bytes, bytearray)):
        if len(obis) != 6:
            raise ValueError(f"OBIS字节长度必须为6，当前: {len(obis)}")
        return tuple(obis)

    if isinstance(obis, (list, tuple)):
        if len(obis) != 6:
            raise ValueError(f"OBIS列表长度必须为6，当前: {len(obis)}")
        return tuple(int(x) for x in obis)

    if isinstance(obis, str):
        obis_bytes = obis_str_to_bytes(obis)
        return tuple(obis_bytes)

    raise ValueError(f"不支持的OBIS类型: {type(obis)}")


def obis_match(obis1: Union[str, bytes, tuple], obis2: Union[str, bytes, tuple],
               wildcards: bool = False) -> bool:
    """
    比较两个OBIS码是否匹配

    Args:
        obis1: 第一个OBIS码
        obis2: 第二个OBIS码
        wildcards: 是否支持通配符（255表示匹配任意）

    Returns:
        bool: 是否匹配
    """
    t1 = normalize_obis(obis1)
    t2 = normalize_obis(obis2)

    if wildcards:
        for a, b in zip(t1, t2):
            if a != 255 and b != 255 and a != b:
                return False
        return True
    else:
        return t1 == t2


def parse_obis_from_string(text: str) -> list:
    """
    从文本中提取所有OBIS码

    Args:
        text: 输入文本

    Returns:
        list: 找到的OBIS码字符串列表
    """
    # 匹配标准格式 A-B:C.D.E.F
    pattern = r"\b(\d{1,3})-(\d{1,3}):(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
    matches = re.findall(pattern, text)
    return ["-".join(m[:2]) + ":" + ".".join(m[2:]) for m in matches]
