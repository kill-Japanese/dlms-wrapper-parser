"""
DLMS测试帧数据生成器

包含各种DLMS协议帧的测试数据构造函数，覆盖：
- 明文Wrapper帧 + DataNotification
- 加密Wrapper帧 + DataNotification (AES-GCM)
- 加密+压缩Wrapper帧 + DataNotification (AES-GCM + V.44)
- GetRequest帧（明文）
- GetResponse帧（明文）
"""

import struct
from typing import Tuple

from app.services.wrapper import build_wpd
from app.services.ciphering import build_ciphered
from app.services.compression import compress, V44_AVAILABLE
from app.services.apdu_parser import build_apdu
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes
from app.utils.ber_encoder import encode_data
from app.utils.obis_utils import obis_str_to_bytes

# ============================================================================
# 测试常量
# ============================================================================

# 测试密钥 (16字节 AES-128)
TEST_BLOCK_CIPHER_KEY = bytes.fromhex('00112233445566778899AABBCCDDEEFF')

# 测试系统标题 (8字节) - ISK11073 的 ASCII 编码
TEST_SYSTEM_TITLE = bytes.fromhex('4953453131303733')

# 测试调用计数器
TEST_INVOCATION_COUNTER = 1

# 安全控制字节：认证+加密 (0x30 = 0011 0000)
# bit0=1(加密), bit1=1(认证), bit3-4=1(key_id=1)
# 注意：DLMS标准中 0x30 表示 authenticated + encrypted (key_id=1)
# 但我们的实现中key_id在bit3-4，所以 0x03 = 加密+认证 (key_id=0)
# 为了与常见电表一致，使用 0x30 (key_id=1, 加密+认证)
TEST_SECURITY_CONTROL_AUTH_ENC = 0x30

# 安全控制字节：认证+加密+压缩 (0x70 = 0111 0000)
# bit2=1(压缩), bit0-1=加密+认证, key_id=1
TEST_SECURITY_CONTROL_AUTH_ENC_COMP = 0x70

# 测试WPort
TEST_SRC_WPORT = 1  # 客户端
TEST_DST_WPORT = 16  # 电表


# ============================================================================
# 辅助函数
# ============================================================================

def hex_str(data: bytes) -> str:
    """将字节转换为十六进制字符串"""
    return bytes_to_hex(data)


def byte_str(hex_str_value: str) -> bytes:
    """将十六进制字符串转换为字节"""
    return hex_to_bytes(hex_str_value)


# ============================================================================
# DataNotification APDU 构造
# ============================================================================

def build_data_notification_apdu(
    invoke_id: int = 0x00000001,
    include_datetime: bool = False,
    data_items: list = None,
) -> bytes:
    """
    构造DataNotification APDU

    DataNotification格式 (tag=15):
    - tag (1 byte): 0x0F
    - long-invoke-id-and-priority (4 bytes): 调用ID
    - datetime (可选): date-time类型，可选
    - notification-body: 通知体（array of structure）

    Args:
        invoke_id: 调用ID
        include_datetime: 是否包含日期时间
        data_items: 数据项列表，每项为(class_id, obis, attribute_id, data_type, value)

    Returns:
        bytes: 完整的DataNotification APDU
    """
    if data_items is None:
        # 默认数据项：3个不同类型的数据
        data_items = [
            # uint32 类型数据: 电压 (class=3, OBIS=0-0:1.0.0.255, attr=2)
            (3, "0-0:1.0.0.255", 2, "double-long-unsigned", 230000),
            # octet-string 类型数据: 序列号 (class=1, OBIS=0-0:96.1.0.255, attr=2)
            (1, "0-0:96.1.0.255", 2, "octet-string", bytes.fromhex('1234567890ABCDEF')),
            # structure 类型数据: 复合数据 (class=3, OBIS=1-0:1.8.0.255, attr=2)
            (3, "1-0:1.8.0.255", 2, "structure",
             [("double-long-unsigned", 12345678),
              ("unsigned", 18)]),  # 1.8.0 (正向有功总电能), scaler_unit
        ]

    # 构建通知体: array of structure
    # 每个structure包含: class_id(2) + obis(6) + attribute_id(1) + data_value
    notification_items = []
    for class_id, obis_str, attr_id, data_type, value in data_items:
        item_content = b""
        # class_id (uint16)
        item_content += struct.pack(">H", class_id)
        # obis (6 bytes octet-string)
        obis_bytes = obis_str_to_bytes(obis_str)
        item_content += obis_bytes
        # attribute_id (uint8)
        item_content += bytes([attr_id])
        # data value (BER编码)
        if data_type == "structure":
            # 结构类型 - 编码每个元素
            struct_content = b""
            for sub_type, sub_val in value:
                struct_content += encode_data(sub_val, sub_type)
            item_content += encode_data(struct_content, "structure")
        else:
            item_content += encode_data(value, data_type)
        notification_items.append(item_content)

    # 构建 array (将所有structure元素拼在一起)
    array_content = b"".join(notification_items)
    notification_body = encode_data(array_content, "array")

    # 构建APDU
    apdu = b""
    # tag
    apdu += bytes([15])  # DataNotification
    # long-invoke-id-and-priority
    apdu += struct.pack(">I", invoke_id)
    # datetime (可选)
    if include_datetime:
        # date-time: 12字节 (year(2) month day hour minute second hundredths deviation status clock_status
        dt_data = bytes.fromhex('07e8'  # year=2024
                                '01'    # month=1
                                '0f'    # day=15
                                '07'    # day_of_week=Sunday(7)? 不对
                                '0c'    # hour=12
                                '00'    # minute=0
                                '00'    # second=0
                                '00'    # hundredths=0
                                'fff0'  # deviation=-60 (UTC+1, 负数用补码？简化处理)
                                '00'    # clock_status=0
                                '01')   # 不对，应该是12字节
        # 修正: 标准date-time是12字节，这里用简化版本
        # year(2) month(1) day(1) day_of_week(1) hour(1) minute(1) second(1) hundredths(1) deviation(2) status(1) clock_status(1)
        dt_data = bytes.fromhex('07e8010f070c000000ffc00001')
        apdu += encode_data(dt_data, "date-time")

    # notification body
    apdu += notification_body

    return apdu


def get_plain_data_notification_apdu() -> bytes:
    """获取明文DataNotification APDU（不含Wrapper）"""
    return build_data_notification_apdu()


# ============================================================================
# GetRequest APDU 构造
# ============================================================================

def get_get_request_apdu(
    class_id: int = 3,
    obis: str = "0-0:1.0.0.255",
    attribute_id: int = 2,
    invoke_id: int = 1,
    get_type: int = 1,
) -> bytes:
    """
    获取GetRequest APDU

    Args:
        class_id: 类ID (默认3=Register)
        obis: OBIS码
        attribute_id: 属性ID
        invoke_id: 调用ID
        get_type: Get请求类型 (1=normal, 2=next, 3=with-list)

    Returns:
        bytes: GetRequest APDU
    """
    return build_apdu("getrequest", {
        "get_type": get_type,
        "invoke_id": invoke_id,
        "class_id": class_id,
        "obis": obis,
        "attribute_id": attribute_id,
    })


# ============================================================================
# GetResponse APDU 构造
# ============================================================================

def get_get_response_apdu(
    value: int = 230000,
    data_type: str = "double-long-unsigned",
    invoke_id: int = 1,
    get_type: int = 1,
) -> bytes:
    """
    构造GetResponse APDU

    GetResponse格式 (tag=193):
    - tag (1 byte): 0xC1
    - get-type (1 byte): 1=normal
    - invoke-id-and-priority (4 bytes)
    - result:
      - 0 = data (成功，后跟数据)
      - 1 = data-access-result (错误)
    - data (BER编码)

    Args:
        value: 返回值
        data_type: 数据类型
        invoke_id: 调用ID
        get_type: Get响应类型

    Returns:
        bytes: GetResponse APDU
    """
    apdu = b""
    # tag
    apdu += bytes([193])  # GetResponse
    # get-type
    apdu += bytes([get_type])
    # invoke-id-and-priority
    apdu += struct.pack(">I", invoke_id)
    # result = 0 (data, 成功)
    apdu += bytes([0])
    # data value (BER编码)
    apdu += encode_data(value, data_type)

    return apdu


# ============================================================================
# Wrapper帧构造
# ============================================================================

def get_plain_wrapper_frame() -> bytes:
    """
    获取明文Wrapper帧 + DataNotification

    帧结构:
    Wrapper Header (8 bytes) + DataNotification APDU

    Returns:
        bytes: 完整的Wrapper帧
    """
    apdu = build_data_notification_apdu()
    return build_wpd(apdu, src_wport=TEST_SRC_WPORT, dst_wport=TEST_DST_WPORT)


def get_encrypted_wrapper_frame() -> bytes:
    """
    获取加密Wrapper帧 + DataNotification (AES-GCM, 无压缩)

    帧结构:
    Wrapper Header (8 bytes) + GeneralGloCiphering (加密的DataNotification)

    Returns:
        bytes: 完整的加密Wrapper帧
    """
    # 构造明文APDU
    plain_apdu = build_data_notification_apdu()

    # 加密 (AES-GCM, 认证+加密)
    # key_id = 1 (从TEST_SECURITY_CONTROL_AUTH_ENC = 0x30 提取: (0x30 >> 3) & 0x03 = 1
    key_id = (TEST_SECURITY_CONTROL_AUTH_ENC >> 3) & 0x03
    encrypted_data = build_ciphered(
        apdu=plain_apdu,
        key=TEST_BLOCK_CIPHER_KEY,
        system_title=TEST_SYSTEM_TITLE,
        invocation_counter=TEST_INVOCATION_COUNTER,
        encrypted=True,
        authenticated=True,
        compressed=False,
        key_id=key_id,
    )

    # Wrapper封装
    return build_wpd(encrypted_data, src_wport=TEST_SRC_WPORT, dst_wport=TEST_DST_WPORT)


def get_encrypted_compressed_wrapper_frame() -> bytes:
    """
    获取加密+压缩Wrapper帧 + DataNotification (AES-GCM + V.44)

    帧结构:
    Wrapper Header (8 bytes) + GeneralGloCiphering (加密的压缩DataNotification)

    处理流程:
    DataNotification APDU → V.44压缩 → AES-GCM加密 → Wrapper封装

    Returns:
        bytes: 完整的加密压缩Wrapper帧
    """
    if not V44_AVAILABLE:
        raise RuntimeError("V.44压缩模块不可用，无法构造加密压缩帧")

    # 构造明文APDU
    plain_apdu = build_data_notification_apdu()

    # V.44压缩
    compressed_data = compress(plain_apdu)

    # 加密 (AES-GCM, 认证+加密+压缩)
    key_id = (TEST_SECURITY_CONTROL_AUTH_ENC_COMP >> 3) & 0x03
    encrypted_data = build_ciphered(
        apdu=compressed_data,
        key=TEST_BLOCK_CIPHER_KEY,
        system_title=TEST_SYSTEM_TITLE,
        invocation_counter=TEST_INVOCATION_COUNTER,
        encrypted=True,
        authenticated=True,
        compressed=True,
        key_id=key_id,
    )

    # Wrapper封装
    return build_wpd(encrypted_data, src_wport=TEST_SRC_WPORT, dst_wport=TEST_DST_WPORT)


def get_get_request_wrapper_frame() -> bytes:
    """
    获取GetRequest Wrapper帧（明文）

    读取 Register (class=3) OBIS=0-0:1.0.0.255 属性2

    Returns:
        bytes: 完整的GetRequest Wrapper帧
    """
    apdu = get_get_request_apdu()
    return build_wpd(apdu, src_wport=TEST_SRC_WPORT, dst_wport=TEST_DST_WPORT)


def get_get_response_wrapper_frame() -> bytes:
    """
    获取GetResponse Wrapper帧（明文）

    返回uint32值

    Returns:
        bytes: 完整的GetResponse Wrapper帧
    """
    apdu = get_get_response_apdu()
    return build_wpd(apdu, src_wport=TEST_DST_WPORT, dst_wport=TEST_SRC_WPORT)


# ============================================================================
# 数据获取辅助函数
# ============================================================================

def get_data_notification_plain_apdu() -> bytes:
    """获取明文DataNotification APDU（兼容函数）"""
    return get_plain_data_notification_apdu()


def generate_test_frame(frame_type: str) -> Tuple[bytes, dict]:
    """
    根据类型生成测试帧

    Args:
        frame_type: 帧类型
            - 'plain_dn': 明文DataNotification
            - 'encrypted_dn': 加密DataNotification
            - 'compressed_dn': 加密+压缩DataNotification
            - 'get_request': GetRequest
            - 'get_response': GetResponse

    Returns:
        (frame_bytes, metadata_dict): 帧数据和元信息
    """
    metadata = {
        "type": frame_type,
        "key": TEST_BLOCK_CIPHER_KEY.hex(),
        "system_title": TEST_SYSTEM_TITLE.hex(),
        "invocation_counter": TEST_INVOCATION_COUNTER,
    }

    if frame_type == "plain_dn":
        frame = get_plain_wrapper_frame()
        metadata["description"] = "明文DataNotification Wrapper帧"
    elif frame_type == "encrypted_dn":
        frame = get_encrypted_wrapper_frame()
        metadata["description"] = "加密DataNotification Wrapper帧 (AES-GCM)"
        metadata["security_control"] = hex(TEST_SECURITY_CONTROL_AUTH_ENC)
    elif frame_type == "compressed_dn":
        frame = get_encrypted_compressed_wrapper_frame()
        metadata["description"] = "加密+压缩DataNotification Wrapper帧 (AES-GCM + V.44)"
        metadata["security_control"] = hex(TEST_SECURITY_CONTROL_AUTH_ENC_COMP)
    elif frame_type == "get_request":
        frame = get_get_request_wrapper_frame()
        metadata["description"] = "GetRequest Wrapper帧 (明文)"
    elif frame_type == "get_response":
        frame = get_get_response_wrapper_frame()
        metadata["description"] = "GetResponse Wrapper帧 (明文)"
    else:
        raise ValueError(f"未知的帧类型: {frame_type}")

    metadata["length"] = len(frame)
    metadata["hex"] = bytes_to_hex(frame)

    return frame, metadata


# ============================================================================
# 预计算的十六进制字符串（用于快速引用）
# ============================================================================

# 在模块加载时预计算
def _get_all_frames_hex() -> dict:
    """获取所有测试帧的十六进制表示"""
    result = {}

    # 明文DataNotification
    plain_frame = get_plain_wrapper_frame()
    result["plain_dn_hex"] = bytes_to_hex(plain_frame)

    # 加密DataNotification
    enc_frame = get_encrypted_wrapper_frame()
    result["encrypted_dn_hex"] = bytes_to_hex(enc_frame)

    # GetRequest
    gr_frame = get_get_request_wrapper_frame()
    result["get_request_hex"] = bytes_to_hex(gr_frame)

    # GetResponse
    gresp_frame = get_get_response_wrapper_frame()
    result["get_response_hex"] = bytes_to_hex(gresp_frame)

    return result


# 延迟导入时计算（避免循环导入问题）
_test_frames_cache = None


def get_all_test_frames() -> dict:
    """获取所有测试帧（缓存）"""
    global _test_frames_cache
    if _test_frames_cache is None:
        _test_frames_cache = _get_all_frames_hex()
    return _test_frames_cache
