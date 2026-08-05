"""
加解密层 (Ciphering Layer)

DLMS/COSEM 安全加密使用 AES-GCM 算法
参考: IEC 62056-53 Clause 7.4.2 (Blue Book) / Green Book

General-Glo-Ciphering APDU 格式 (BER-encoded):
  Tag (1 byte): 0xDB (General-Glo-Ciphering)
  system-title (OCTET STRING):
    length (1 byte): 通常为 0x08
    value (8 bytes): System Title
  ciphered-service (OCTET STRING):
    length (variable): 加密服务数据长度
    value:
      security-control (1 byte): 安全控制字节
        bit 0 (0x01): EK - 加密标识
        bit 1 (0x02): AK - 认证标识
        bit 2 (0x04): 压缩标识（V.44）
        bit 3-4 (0x18): Key 类型标识
          00 = GUEK (Global Unicast Encryption Key)
          01 = GUBK (Global Unicast Broadcast Key)
          10 = System Key
        bit 5 (0x20): ECC 签名标识
      invocation-counter (4 bytes, big-endian): 调用计数器
      ciphered-content (variable): 加密的APDU内容
      GMAC tag (12 bytes): 认证标签（如果有认证）
"""
from typing import Optional, Tuple, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.models.cipher import CipherFrame, CipherInfo
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes


class CipheringError(Exception):
    """加解密异常"""
    pass


# 密钥ID常量 (Security Control bit 3-4)
KEY_ID_UNICAST = 0    # 00b - GUEK - Global Unicast Encryption Key（全局单播加密密钥）
KEY_ID_BROADCAST = 1  # 01b - GUBK - Global Unicast Broadcast Key（全局广播密钥）
KEY_ID_SYSTEM = 2     # 10b - System Key（系统密钥）

# SC字节位掩码常量
SC_MASK_ENCRYPTED = 0x01     # bit 0 - EK (Encryption Key used)
SC_MASK_AUTHENTICATED = 0x02  # bit 1 - AK (Authentication Key used)
SC_MASK_COMPRESSED = 0x04     # bit 2 - Compressed (V.44)
SC_MASK_KEY_ID = 0x18         # bit 3-4 - Key Identifier (0x08 | 0x10)
SC_MASK_ECC_SIGNED = 0x20     # bit 5 - ECC signature present


def _parse_ber_length(data: bytes, offset: int) -> Tuple[int, int]:
    """
    解析 BER 长度编码

    Args:
        data: 数据
        offset: 起始偏移

    Returns:
        (length, new_offset): 长度值和新的偏移位置
    """
    if offset >= len(data):
        raise ValueError("数据不足，无法读取长度")

    first = data[offset]
    offset += 1

    if first & 0x80:
        # 长格式：最高位为1，低7位表示后续长度字节数
        num_bytes = first & 0x7F
        if num_bytes == 0 or offset + num_bytes > len(data):
            raise ValueError("BER长格式长度无效")
        length = 0
        for _ in range(num_bytes):
            length = (length << 8) | data[offset]
            offset += 1
        return length, offset
    else:
        # 短格式：最高位为0，直接表示长度
        return first, offset


def select_key_by_id(key_id: int, keys: Dict[str, Optional[bytes]]) -> Optional[bytes]:
    """
    根据 key_id 选择对应的密钥

    Args:
        key_id: 密钥标识 (0=unicast, 1=broadcast, 2=system)
        keys: 密钥字典，包含 guek, gubk, ak, kek 等

    Returns:
        选中的密钥字节，或 None

    密钥映射:
        key_id=0 (unicast)   -> GUEK
        key_id=1 (broadcast) -> GUBK
        key_id=2 (system)    -> 系统密钥（暂用GUEK）
    """
    if key_id == KEY_ID_UNICAST:
        return keys.get("guek")
    elif key_id == KEY_ID_BROADCAST:
        return keys.get("gubk")
    elif key_id == KEY_ID_SYSTEM:
        # 系统密钥暂用GUEK
        return keys.get("guek")
    else:
        # 默认使用GUEK
        return keys.get("guek")


def _parse_security_control(sc_byte: int) -> CipherInfo:
    """
    解析安全控制字节 (Security Control byte)

    SC字节位定义:
    - bit 0 (0x01): EK - 加密标识
    - bit 1 (0x02): AK - 认证标识
    - bit 2 (0x04): 压缩标识 (V.44)
    - bit 3-4 (0x18): Key 类型标识 (0=unicast, 1=broadcast, 2=system)
    - bit 5 (0x20): ECC 签名标识
    - bit 6-7: 保留

    Args:
        sc_byte: 安全控制字节值 (0x00 - 0xFF)

    Returns:
        CipherInfo: 加密信息对象
    """
    encrypted = bool(sc_byte & SC_MASK_ENCRYPTED)
    authenticated = bool(sc_byte & SC_MASK_AUTHENTICATED)
    compressed = bool(sc_byte & SC_MASK_COMPRESSED)
    key_id = (sc_byte & SC_MASK_KEY_ID) >> 3  # bit 3-4
    ecc_signed = bool(sc_byte & SC_MASK_ECC_SIGNED)

    return CipherInfo(
        encrypted=encrypted,
        authenticated=authenticated,
        compressed=compressed,
        key_id=key_id,
        ecc_signed=ecc_signed,
    )


def _build_security_control(cipher_info: CipherInfo) -> int:
    """
    构建安全控制字节

    Args:
        cipher_info: 加密信息

    Returns:
        int: 安全控制字节值 (0x00 - 0xFF)
    """
    sc = 0
    if cipher_info.encrypted:
        sc |= SC_MASK_ENCRYPTED
    if cipher_info.authenticated:
        sc |= SC_MASK_AUTHENTICATED
    if cipher_info.compressed:
        sc |= SC_MASK_COMPRESSED
    sc |= (cipher_info.key_id & 0x03) << 3
    if cipher_info.ecc_signed:
        sc |= SC_MASK_ECC_SIGNED
    return sc


def _derive_gcm_key(key: bytes) -> bytes:
    """
    确保密钥长度正确（AES-128 需要16字节）

    Args:
        key: 输入密钥

    Returns:
        16字节密钥
    """
    if len(key) == 16:
        return key
    elif len(key) > 16:
        return key[:16]
    else:
        # 不足时用0填充
        return key + b'\x00' * (16 - len(key))


def parse_ciphered(
    data: bytes,
    key: Optional[bytes] = None,
    keys: Optional[Dict[str, Optional[bytes]]] = None,
) -> Tuple[bytes, CipherFrame]:
    """
    解析 General-Glo-Ciphering 加密帧（BER编码格式），尝试解密

    输入数据格式（完整的加密APDU，从tag字节开始）:
      Tag (1 byte): 0xDB (General-Glo-Ciphering) 或 0xDA (General-Ciphering)
      system-title (OCTET STRING, BER编码):
        length (1 byte): 通常为 0x08（表示后面8字节是System Title）
        value (8 bytes): System Title
      ciphered-service (OCTET STRING, BER编码):
        length (variable)
        value:
          security-control (1 byte)
          invocation-counter (4 bytes, big-endian)
          ciphered-content (variable)
          GMAC tag (12 bytes, if authenticated)

    Args:
        data: 加密APDU数据（从tag字节开始，如0xDB）
        key: 解密密钥（16字节AES-128密钥，向后兼容参数）
        keys: 密钥字典，包含 guek, gubk, ak, kek 等
              当提供 keys 时，会根据 key_id 自动选择密钥

    Returns:
        (plaintext_apdu, CipherFrame): 解密后的APDU数据和加密帧信息

    Raises:
        CipheringError: 解析或解密失败
    """
    if len(data) < 2:
        raise CipheringError("加密帧数据太短")

    offset = 0

    # 1. APDU Tag (0xDB = General-Glo-Ciphering, 0xDA = General-Ciphering)
    tag = data[offset]
    offset += 1

    if tag not in (0xDA, 0xDB, 0xDC, 0xD8):
        raise CipheringError(f"不是加密APDU，tag={tag:#04x}")

    # 2. System Title (OCTET STRING, BER编码)
    #    第一个字节是长度（通常是0x08），后面才是真正的System Title
    try:
        st_length, offset = _parse_ber_length(data, offset)
        if st_length == 0 or offset + st_length > len(data):
            raise CipheringError("System Title 长度无效")
        system_title = data[offset:offset + st_length]
        offset += st_length
    except CipheringError:
        raise
    except Exception as e:
        raise CipheringError(f"解析System Title失败: {e}")

    # 3. Ciphered Service Data (OCTET STRING, BER编码)
    try:
        cs_length, offset = _parse_ber_length(data, offset)
        if cs_length == 0 or offset + cs_length > len(data):
            raise CipheringError("加密服务数据长度无效")
        ciphered_service = data[offset:offset + cs_length]
    except CipheringError:
        raise
    except Exception as e:
        raise CipheringError(f"解析加密服务数据失败: {e}")

    # 4. 解析 ciphered-service 内部结构
    #    结构: security-control(1) + invocation-counter(4) + ciphered-content + GMAC(12 if auth)
    cs_offset = 0

    # 4.1 Security Control 字节
    if cs_offset >= len(ciphered_service):
        raise CipheringError("数据不足，无法读取安全控制字节")
    sc_byte = ciphered_service[cs_offset]
    cs_offset += 1
    cipher_info = _parse_security_control(sc_byte)

    # 4.2 Invocation Counter (4字节，大端序)
    #    注意：DLMS规范中IC的长度通常是4字节
    ic_length = 4  # DLMS标准中Invocation Counter为4字节
    if cs_offset + ic_length > len(ciphered_service):
        raise CipheringError("数据不足，无法读取调用计数器")
    invocation_counter = int.from_bytes(
        ciphered_service[cs_offset:cs_offset + ic_length], "big"
    )
    cs_offset += ic_length

    # 4.3 密文数据 + GMAC Tag
    remaining = ciphered_service[cs_offset:]
    gmac_tag = b""
    ciphered_data = remaining

    # 如果有认证，最后12字节是GMAC tag
    if cipher_info.authenticated and len(remaining) > 12:
        gmac_tag = remaining[-12:]
        ciphered_data = remaining[:-12]

    # 5. 选择解密密钥
    active_key = key
    active_key_name = "default"
    if keys is not None:
        selected_key = select_key_by_id(cipher_info.key_id, keys)
        if selected_key is not None:
            active_key = selected_key
            key_id_names = {0: "GUEK (unicast)", 1: "GUBK (broadcast)", 2: "System Key"}
            active_key_name = key_id_names.get(cipher_info.key_id, f"key_id={cipher_info.key_id}")

    # 6. 尝试解密
    decrypt_success = False
    plaintext = b""

    if cipher_info.encrypted and active_key is not None:
        try:
            gcm_key = _derive_gcm_key(active_key)
            aesgcm = AESGCM(gcm_key)

            # 构建 Nonce (IV): System Title (8字节) + Invocation Counter (4字节) = 12字节
            # System Title 已经跳过了长度字节，直接是8字节的值
            nonce = system_title + invocation_counter.to_bytes(4, "big")
            nonce = nonce[:12]  # 确保总共12字节

            # 关联数据 (AAD): Security Control 字节
            # 注意：部分设备的AAD可能包含更多数据，这里先用最基本的SC字节
            aad = bytes([sc_byte])

            # 解密
            if cipher_info.authenticated:
                # 带认证标签：密文 + 12字节GMAC tag
                ciphertext_with_tag = ciphered_data + gmac_tag
                plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
            else:
                # 仅加密（DLMS中通常同时加密和认证）
                plaintext = aesgcm.decrypt(nonce, ciphered_data, aad)

            decrypt_success = True
        except Exception as e:
            # 解密失败，保留原始密文
            decrypt_success = False
            plaintext = b""
    elif not cipher_info.encrypted:
        # 未加密，直接返回
        plaintext = ciphered_data
        decrypt_success = True

    # 构建返回对象
    cipher_frame = CipherFrame(
        security_control=bytes_to_hex(sc_byte),
        security_control_byte=sc_byte,
        system_title=bytes_to_hex(system_title),
        invocation_counter=invocation_counter,
        ciphered_data_hex=bytes_to_hex(ciphered_data),
        gmac_tag=bytes_to_hex(gmac_tag),
        decrypt_success=decrypt_success,
        cipher_info=cipher_info,
        extracted_from_frame=True,
    )

    return plaintext, cipher_frame


def build_ciphered(
    apdu: bytes,
    key: Optional[bytes] = None,
    system_title: bytes = b"",
    invocation_counter: int = 1,
    encrypted: bool = True,
    authenticated: bool = True,
    compressed: bool = False,
    key_id: int = 0,
    keys: Optional[Dict[str, Optional[bytes]]] = None,
) -> bytes:
    """
    构建 General-Glo-Ciphering 加密帧（BER编码格式）

    输出格式:
      Tag (1 byte): 0xDB
      system-title (OCTET STRING):
        length (1 byte): 0x08
        value (8 bytes): System Title
      ciphered-service (OCTET STRING):
        length (variable)
        value:
          security-control (1 byte)
          invocation-counter (4 bytes)
          ciphered-content (variable)
          GMAC tag (12 bytes, if authenticated)

    Args:
        apdu: 明文APDU数据
        key: 加密密钥（16字节，向后兼容）
        system_title: 系统标题（8字节）
        invocation_counter: 调用计数器
        encrypted: 是否加密
        authenticated: 是否认证
        compressed: 是否压缩
        key_id: 密钥标识 (0-3)
        keys: 密钥字典，包含 guek, gubk, ak, kek 等
              当提供 keys 时，会根据 key_id 自动选择密钥

    Returns:
        bytes: 完整的加密APDU数据（从0xDB tag开始）

    Raises:
        CipheringError: 加密失败
    """
    # 选择加密密钥
    active_key = key
    if keys is not None:
        selected_key = select_key_by_id(key_id, keys)
        if selected_key is not None:
            active_key = selected_key

    cipher_info = CipherInfo(
        encrypted=encrypted,
        authenticated=authenticated,
        compressed=compressed,
        key_id=key_id,
    )

    sc_byte = _build_security_control(cipher_info)

    # 调用计数器（4字节，大端序）
    ic_bytes = invocation_counter.to_bytes(4, "big")

    # 构建 ciphered-service 的内容
    if not encrypted and not authenticated:
        # 不加密也不认证，直接附加明文
        cs_content = bytes([sc_byte]) + ic_bytes + apdu
    else:
        # 使用AES-GCM加密
        if active_key is None:
            raise CipheringError("加密需要提供密钥")

        gcm_key = _derive_gcm_key(active_key)
        aesgcm = AESGCM(gcm_key)

        # Nonce = System Title (8字节) + Invocation Counter (4字节) = 12字节
        nonce = system_title + ic_bytes
        nonce = nonce[:12]

        # 关联数据
        aad = bytes([sc_byte])

        # 加密并生成认证标签
        ciphertext_with_tag = aesgcm.encrypt(nonce, apdu, aad)

        # 构建 ciphered-service 内容
        # SC(1) + IC(4) + ciphertext + tag
        cs_content = bytes([sc_byte]) + ic_bytes + ciphertext_with_tag

    # 构建 ciphered-service OCTET STRING（带BER长度）
    cs_length = len(cs_content)
    if cs_length < 0x80:
        cs_length_bytes = bytes([cs_length])
    else:
        # 长格式
        num_bytes = (cs_length.bit_length() + 7) // 8
        cs_length_bytes = bytes([0x80 | num_bytes]) + cs_length.to_bytes(num_bytes, "big")
    cs_octet_string = cs_length_bytes + cs_content

    # 构建 system-title OCTET STRING（带BER长度）
    st_length = len(system_title)
    st_octet_string = bytes([st_length]) + system_title

    # 完整的 General-Glo-Ciphering APDU
    result = bytes([0xDB]) + st_octet_string + cs_octet_string

    return result


def is_ciphered_apdu(tag: int) -> bool:
    """
    判断APDU标签是否为加密类型

    Args:
        tag: APDU标签

    Returns:
        bool: 是否为加密APDU
    """
    # General-Glo-Ciphering = 219 (0xDB)
    # General-Ciphering = 218 (0xDA)
    # General-Ded-Ciphering = 220 (0xDC)
    # General-Sign = 216 (0xD8)
    return tag in (216, 218, 219, 220)
