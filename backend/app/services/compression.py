"""
压缩层 (Compression Layer)

DLMS/COSEM 使用 V.44 数据压缩算法 (ITU-T V.44)
参考: IEC 62056-53 Clause 7.4.3

当安全控制字节的bit 2为1时，表示数据经过V.44压缩。
"""
from typing import Optional

try:
    from app.v44 import v44_compress, v44_decompress
    V44_AVAILABLE = True
except ImportError:
    V44_AVAILABLE = False
    # 提供占位函数，避免导入错误
    def v44_compress(data: bytes) -> bytes:
        raise NotImplementedError("V.44压缩模块不可用")

    def v44_decompress(data: bytes) -> bytes:
        raise NotImplementedError("V.44压缩模块不可用")


class CompressionError(Exception):
    """压缩/解压异常"""
    pass


def decompress(data: bytes) -> bytes:
    """
    解压V.44压缩的数据

    Args:
        data: 压缩后的数据

    Returns:
        bytes: 解压后的数据

    Raises:
        CompressionError: 解压失败
    """
    if not data:
        return b""

    if not V44_AVAILABLE:
        raise CompressionError("V.44压缩模块不可用，无法解压")

    try:
        return v44_decompress(data)
    except Exception as e:
        raise CompressionError(f"V.44解压失败: {e}") from e


def compress(data: bytes) -> bytes:
    """
    使用V.44压缩数据

    Args:
        data: 原始数据

    Returns:
        bytes: 压缩后的数据

    Raises:
        CompressionError: 压缩失败
    """
    if not data:
        return b""

    if not V44_AVAILABLE:
        raise CompressionError("V.44压缩模块不可用，无法压缩")

    try:
        return v44_compress(data)
    except Exception as e:
        raise CompressionError(f"V.44压缩失败: {e}") from e


def is_v44_compressed(data: bytes) -> Optional[bool]:
    """
    尝试判断数据是否经过V.44压缩

    通过检查V.44数据的特征来判断：
    - V.44数据包通常以特定的控制码开头
    - 这是一个启发式判断，不一定准确

    Args:
        data: 待检测的数据

    Returns:
        True=可能是压缩数据, False=可能不是, None=无法判断
    """
    if not data or len(data) < 2:
        return None

    # V.44压缩数据的一些特征：
    # 1. 通常以0x00开头（重置码）
    # 2. 数据中有一定的熵（压缩后的数据通常看起来随机）
    # 这是一个非常粗略的判断，实际应用中应结合安全控制字节来判断

    # 检查是否有V.44的典型起始模式
    # V.44 packet method 通常以 <DLE><STX> 或特定控制序列开始
    if data[0] == 0x00 and len(data) > 1:
        # 可能是V.44压缩数据的开始
        return True

    # 计算字节熵（简单的启发式）
    # 压缩后的数据通常字节分布更均匀
    unique_bytes = len(set(data[:min(100, len(data))]))
    if unique_bytes > 50:  # 前100字节中有超过50种不同的值
        return True

    return None


def get_compression_info(data: bytes) -> dict:
    """
    获取压缩信息

    Args:
        data: 压缩数据

    Returns:
        dict: 压缩信息字典
    """
    info = {
        "original_size": 0,
        "compressed_size": len(data),
        "ratio": 0.0,
        "algorithm": "V.44",
        "decompressed": False,
    }

    if V44_AVAILABLE:
        try:
            decompressed = decompress(data)
            info["original_size"] = len(decompressed)
            info["ratio"] = round(len(data) / len(decompressed), 4) if decompressed else 0
            info["decompressed"] = True
        except Exception:
            info["decompressed"] = False

    return info
