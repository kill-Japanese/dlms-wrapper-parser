"""
V.44 数据压缩模块 (ITU-T V.44 / DLMS/COSEM)

从 v44-compression skill 导入核心功能。
"""
from .v44 import (
    v44_compress,
    v44_decompress,
    v44_roundtrip,
    V44Encoder,
    V44Decoder,
    V44BitstreamWriter,
    V44BitstreamReader,
    # 常量
    V44_N2,
    V44_N4,
    V44_N5,
    V44_N7,
    V44_C5_INIT_BIT7,
    V44_C5_INIT_BIT8,
    V44_C2_INIT,
    V44_C3_INIT,
    V44_N1_MAX,
    V44_OK,
    V44_ERR_BUFFER_FULL,
    V44_ERR_INVALID_CODE,
    V44_ERR_OUTPUT_FULL,
    V44_ERR_INPUT_EMPTY,
    V44_CTRL_ETM,
    V44_CTRL_FLUSH,
    V44_CTRL_STEPUP,
    V44_CTRL_REINIT,
)

__all__ = [
    "v44_compress",
    "v44_decompress",
    "v44_roundtrip",
    "V44Encoder",
    "V44Decoder",
    "V44BitstreamWriter",
    "V44BitstreamReader",
]
