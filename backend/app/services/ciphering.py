"""
加解密层 (Ciphering Layer)

DLMS/COSEM 安全加密使用 AES-GCM 算法
参考: IEC 62056-53 Clause 7.4.2 (Blue Book) / Green Book

加密帧格式 (General-Glo-Ciphering / General-Ciphering):
- Security Control (1 byte): 安全控制字节
  - bit 0 (0x01): EK - Encryption Key 使用标识（1=已加密）
  - bit 1 (0x02): AK - Authentication Key 使用标识（1=已认证）
  - bit 2 (0x04): 压缩标识（1=已压缩，V.44）
  - bit 3-4 (0x08, 0x10): Key 类型标识
    - 00 (0x00) = Unicast / GUEK (Global Unicast Encryption Key)
    - 01 (0x08) = Broadcast / GUBK (Global Unicast Broadcast Key)
    - 10 (0x10) = System Key
  - bit 5 (0x20): ECC 签名标识（1=有ECC签名）
  - bit 6-7: 保留
- System Title (8 bytes): 系统标题
- Length of invocation counter (n)
- Invocation Counter (n bytes): 调用计数器
- Ciphered Text (variable): 密文
- GMAC Tag (12 bytes if authenticated): GMAC认证标签
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
    解析加密帧，尝试解密

    注意：这是骨架实现，完整实现需要根据DLMS规范处理多种场景。
    当前实现处理最常见的 General-Glo-Ciphering 格式。

    Args:
        data: 加密帧数据（从安全控制字节开始）
        key: 解密密钥（16字节AES-128密钥，向后兼容参数）
        keys: 密钥字典，包含 guek, gubk, ak, kek 等
              当提供 keys 时，会根据 key_id 自动选择密钥

    Returns:
        (plaintext_apdu, CipherFrame): 解密后的APDU数据和加密帧信息

    Raises:
        CipheringError: 解析或解密失败
    """
    if len(data) < 1:
        raise CipheringError("加密帧数据为空")

    offset = 0

    # 1. 安全控制字节
    sc_byte = data[offset]
    offset += 1
    cipher_info = _parse_security_control(sc_byte)

    # 2. 系统标题 (8字节)
    if len(data) < offset + 8:
        raise CipheringError("数据不足，无法读取系统标题")
    system_title = data[offset:offset + 8]
    offset += 8

    # 3. 调用计数器长度和值
    if offset >= len(data):
        raise CipheringError("数据不足，无法读取调用计数器长度")
    ic_length = data[offset]
    offset += 1

    if len(data) < offset + ic_length:
        raise CipheringError("数据不足，无法读取调用计数器")
    invocation_counter = int.from_bytes(data[offset:offset + ic_length], "big")
    offset += ic_length

    # 4. 密文数据
    # 如果有认证，最后12字节是GMAC tag
    gmac_tag = b""
    ciphered_data = data[offset:]

    if cipher_info.authenticated and len(ciphered_data) > 12:
        gmac_tag = ciphered_data[-12:]
        ciphered_data = ciphered_data[:-12]

    # 5. 选择解密密钥
    # 如果提供了 keys 字典，根据 key_id 选择对应密钥
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

            # 构建nonce: system_title + invocation_counter
            nonce = system_title + invocation_counter.to_bytes(
                max(4, ic_length), "big"
            )[-12 + len(system_title):]  # 12 - len(system_title) bytes from IC
            # 标准nonce是 system_title(8) + invocation_counter(4) = 12 bytes
            ic_bytes = invocation_counter.to_bytes(4, "big")
            nonce = system_title + ic_bytes[-4:]  # 12 bytes total
            nonce = nonce[:12]

            # 关联数据 (AAD) - 用于认证
            # 通常包含 security_control 和一些附加数据
            aad = bytes([sc_byte])

            # 解密
            if cipher_info.authenticated:
                # 带认证标签
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
        extracted_from_frame=True,  # ST和IC始终从帧中提取
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
    构建加密帧

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
        bytes: 加密帧数据（包含安全控制字节、系统标题、调用计数器、密文、GMAC tag）

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

    # 调用计数器（4字节）
    ic_length = 4
    ic_bytes = invocation_counter.to_bytes(ic_length, "big")

    # 构建帧头
    result = bytes([sc_byte]) + system_title + bytes([ic_length]) + ic_bytes

    if not encrypted and not authenticated:
        # 不加密也不认证，直接附加明文
        result += apdu
        return result

    # 使用AES-GCM加密
    try:
        if active_key is None:
            raise CipheringError("加密需要提供密钥")

        gcm_key = _derive_gcm_key(active_key)
        aesgcm = AESGCM(gcm_key)

        # nonce = system_title(8) + invocation_counter(4) = 12 bytes
        nonce = system_title + ic_bytes
        nonce = nonce[:12]

        # 关联数据
        aad = bytes([sc_byte])

        # 加密并生成认证标签
        ciphertext_with_tag = aesgcm.encrypt(nonce, apdu, aad)

        if authenticated:
            # 密文 + 12字节GMAC tag
            result += ciphertext_with_tag
        else:
            # 只有密文，没有tag（DLMS中不常见）
            # AESGCM.encrypt返回密文+tag(16字节)，DLMS使用12字节tag
            # 这里需要特殊处理
            # TODO: 处理仅加密不认证的情况
            result += ciphertext_with_tag

        return result

    except CipheringError:
        raise
    except Exception as e:
        raise CipheringError(f"加密失败: {e}") from e


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
