"""
加解密层 (Ciphering Layer)

DLMS/COSEM 安全加密使用 AES-GCM 算法
参考: IEC 62056-53 Clause 7.4 (Blue Book) / Green Book

Security Control 字节定义（按DLMS蓝皮书）:
  Bit 7 (0x80): C - Compression 压缩标识（1=已压缩，V.44）
  Bit 6 (0x40): Key_Set 密钥集（0=Unicast/GUEK, 1=Broadcast/GUBK）
  Bit 5 (0x20): E - Encryption 加密标识（1=已加密）
  Bit 4 (0x10): A - Authentication 认证标识（1=已认证）
  Bit 3-0 (0x0F): Security_Suite_Id 安全套件ID（0/1/2）

General-Glo-Ciphering APDU 格式 (BER-encoded):
  Tag (1 byte): 0xDB (General-Glo-Ciphering)
  system-title (OCTET STRING):
    length (1 byte): 通常为 0x08
    value (8 bytes): System Title
  ciphered-service (OCTET STRING):
    length (variable)
    value:
      security-control (1 byte): 安全控制字节
      invocation-counter (4 bytes, big-endian): 调用计数器
      ciphered-content (variable): 加密的APDU内容
      GMAC tag (12 bytes): 认证标签（如果认证开启）
"""
from typing import Optional, Tuple, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.models.cipher import CipherFrame, CipherInfo
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes


class CipheringError(Exception):
    """加解密异常"""
    pass


# ============================================================
# Security Control 字节位定义（按DLMS蓝皮书）
# ============================================================
# Bit 7 (0x80): C - Compression (压缩标识)
# Bit 6 (0x40): Key_Set (密钥集: 0=Unicast, 1=Broadcast)
# Bit 5 (0x20): E - Encryption (加密标识)
# Bit 4 (0x10): A - Authentication (认证标识)
# Bit 3-0 (0x0F): Security_Suite_Id (安全套件ID: 0/1/2)
# ============================================================
SC_MASK_COMPRESSED = 0x80       # bit 7 - C (Compression)
SC_MASK_KEY_SET = 0x40          # bit 6 - Key_Set (0=Unicast, 1=Broadcast)
SC_MASK_ENCRYPTED = 0x20        # bit 5 - E (Encryption)
SC_MASK_AUTHENTICATED = 0x10    # bit 4 - A (Authentication)
SC_MASK_SUITE_ID = 0x0F         # bit 3-0 - Security_Suite_Id

# 密钥集常量
KEY_SET_UNICAST = 0     # 0 = Unicast (GUEK)
KEY_SET_BROADCAST = 1   # 1 = Broadcast (GUBK)

# 安全套件常量
SUITE_0 = 0  # Suite 0 (预留)
SUITE_1 = 1  # Suite 1 (AES-128-GCM)
SUITE_2 = 2  # Suite 2 (ECC + AES-256-GCM)


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


def select_key_by_key_set(key_set: int, keys: Dict[str, Optional[bytes]]) -> Optional[bytes]:
    """
    根据 Key_Set 选择对应的加密密钥

    Args:
        key_set: 密钥集 (0=Unicast/GUEK, 1=Broadcast/GUBK)
        keys: 密钥字典，包含 guek, gubk, ak, kek 等

    Returns:
        选中的密钥字节，或 None
    """
    if key_set == KEY_SET_UNICAST:
        return keys.get("guek")
    elif key_set == KEY_SET_BROADCAST:
        return keys.get("gubk")
    else:
        # 默认使用GUEK
        return keys.get("guek")


def _parse_security_control(sc_byte: int) -> CipherInfo:
    """
    解析安全控制字节 (Security Control byte)

    按DLMS蓝皮书定义:
    - Bit 7 (0x80): C - Compression 压缩标识
    - Bit 6 (0x40): Key_Set 密钥集 (0=Unicast, 1=Broadcast)
    - Bit 5 (0x20): E - Encryption 加密标识
    - Bit 4 (0x10): A - Authentication 认证标识
    - Bit 3-0 (0x0F): Security_Suite_Id 安全套件ID

    Args:
        sc_byte: 安全控制字节值 (0x00 - 0xFF)

    Returns:
        CipherInfo: 加密信息对象
    """
    compressed = bool(sc_byte & SC_MASK_COMPRESSED)
    key_set = (sc_byte & SC_MASK_KEY_SET) >> 6  # bit 6
    encrypted = bool(sc_byte & SC_MASK_ENCRYPTED)
    authenticated = bool(sc_byte & SC_MASK_AUTHENTICATED)
    suite_id = sc_byte & SC_MASK_SUITE_ID  # bit 3-0

    print(f"[CIPHER DEBUG] SC byte = 0x{sc_byte:02X} ({sc_byte})")
    print(f"  Bit 7 (C/Compression):  {(sc_byte >> 7) & 1} -> {'压缩' if compressed else '未压缩'}")
    print(f"  Bit 6 (Key_Set):        {(sc_byte >> 6) & 1} -> {'广播(GUBK)' if key_set else '单播(GUEK)'}")
    print(f"  Bit 5 (E/Encryption):   {(sc_byte >> 5) & 1} -> {'加密' if encrypted else '未加密'}")
    print(f"  Bit 4 (A/Authentication): {(sc_byte >> 4) & 1} -> {'认证' if authenticated else '未认证'}")
    print(f"  Bit 3-0 (Suite ID):     {suite_id} -> Suite {suite_id}")

    return CipherInfo(
        encrypted=encrypted,
        authenticated=authenticated,
        compressed=compressed,
        key_id=key_set,  # 用 key_id 字段存储 key_set
        ecc_signed=False,  # 旧字段保留，实际ECC信息在suite_id中
        suite_id=suite_id,
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
    if cipher_info.compressed:
        sc |= SC_MASK_COMPRESSED
    if cipher_info.key_id == KEY_SET_BROADCAST:
        sc |= SC_MASK_KEY_SET
    if cipher_info.encrypted:
        sc |= SC_MASK_ENCRYPTED
    if cipher_info.authenticated:
        sc |= SC_MASK_AUTHENTICATED
    # Suite ID
    suite_id = getattr(cipher_info, 'suite_id', SUITE_1)
    sc |= (suite_id & 0x0F)
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


def _compute_nonce(system_title: bytes, invocation_counter: int, ic_length: int = 4) -> bytes:
    """
    计算 AES-GCM Nonce (IV)

    按 DLMS 规范:
    Nonce = System Title + Invocation Counter = 12 字节

    - System Title: 8字节（从帧中提取，跳过BER长度字节后的值）
    - Invocation Counter: 4字节，大端序

    Args:
        system_title: System Title (8字节)
        invocation_counter: 调用计数器
        ic_length: IC字节长度（默认4字节）

    Returns:
        12字节 Nonce
    """
    ic_bytes = invocation_counter.to_bytes(ic_length, "big")
    nonce = system_title + ic_bytes
    nonce = nonce[:12]  # 确保总共12字节

    print(f"[CIPHER DEBUG] Nonce (IV) 计算:")
    print(f"  System Title:    {bytes_to_hex(system_title)} ({len(system_title)} bytes)")
    print(f"  Invocation Ctr:  {invocation_counter} (0x{invocation_counter:08X})")
    print(f"  IC bytes:        {bytes_to_hex(ic_bytes)} ({len(ic_bytes)} bytes)")
    print(f"  Nonce (12B):     {bytes_to_hex(nonce)} ({len(nonce)} bytes)")

    return nonce


def _compute_aad(sc_byte: int, system_title: bytes = None) -> bytes:
    """
    计算 AES-GCM AAD (Additional Authenticated Data, 关联认证数据)

    按 DLMS 规范，AAD 至少包含 Security Control 字节。
    部分实现可能还包含 System Title 等其他数据。

    注意：不同厂商/设备可能有不同的AAD构造方式。
    如果解密失败，可以尝试调整AAD的构造。

    Args:
        sc_byte: Security Control 字节
        system_title: System Title（可选，部分设备需要）

    Returns:
        AAD 字节
    """
    # 基本AAD = SC 字节
    aad = bytes([sc_byte])

    print(f"[CIPHER DEBUG] AAD (关联认证数据) 计算:")
    print(f"  AAD = SC byte:    {bytes_to_hex(aad)} ({len(aad)} bytes)")

    return aad


def _aes_gcm_decrypt(
    key: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes,
    aad: bytes = b"",
) -> bytes:
    """
    AES-GCM 解密，支持任意长度的 GMAC tag

    使用底层 Cipher API 而不是 AESGCM 类，
    因为 AESGCM 类只支持 16 字节 tag，
    而 DLMS Suite 1 使用 12 字节 tag。

    Args:
        key: 16字节 AES 密钥
        nonce: 12字节 Nonce/IV
        ciphertext: 密文数据
        tag: GMAC 认证标签（可以是12/16字节等）
        aad: 关联认证数据

    Returns:
        明文数据

    Raises:
        Exception: 认证失败或解密失败
    """
    tag_len = len(tag)
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, tag, min_tag_length=tag_len),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decryptor.authenticate_additional_data(aad)
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext


def _aes_gcm_encrypt(
    key: bytes,
    nonce: bytes,
    plaintext: bytes,
    aad: bytes = b"",
    tag_length: int = 12,
) -> Tuple[bytes, bytes]:
    """
    AES-GCM 加密，支持指定 tag 长度

    Args:
        key: 16字节 AES 密钥
        nonce: 12字节 Nonce/IV
        plaintext: 明文数据
        aad: 关联认证数据
        tag_length: tag长度（默认12字节，DLMS Suite 1）

    Returns:
        (ciphertext, tag): 密文和GMAC标签
    """
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, min_tag_length=tag_length),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encryptor.authenticate_additional_data(aad)
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag[:tag_length]
    return ciphertext, tag


def _try_decrypt_with_multiple_aads(
    key: bytes,
    nonce: bytes,
    ciphered_data: bytes,
    gmac_tag: bytes,
    sc_byte: int,
    system_title: bytes,
    invocation_counter: int,
) -> Tuple[bytes, str]:
    """
    尝试用多种 AAD 构造方式解密

    DLMS 不同厂商的 AAD 构造可能不同，依次尝试：
    1. AAD = SC byte (最常见)
    2. AAD = SC byte + System Title (部分厂商)
    3. AAD = SC byte + System Title + IC (少数厂商)

    Args:
        key: 密钥
        nonce: Nonce/IV
        ciphered_data: 密文
        gmac_tag: GMAC标签
        sc_byte: Security Control字节
        system_title: System Title
        invocation_counter: 调用计数器

    Returns:
        (plaintext, aad_description): 明文和使用的AAD描述
        如果所有方式都失败，抛出异常
    """
    # 构造不同的AAD进行尝试
    aad_attempts = [
        (bytes([sc_byte]), "SC byte (1B)"),
        (bytes([sc_byte]) + system_title, "SC + System Title (9B)"),
        (bytes([sc_byte]) + system_title + invocation_counter.to_bytes(4, "big"), "SC + ST + IC (13B)"),
        (system_title + bytes([sc_byte]), "System Title + SC (9B)"),
    ]

    for aad, desc in aad_attempts:
        try:
            print(f"[CIPHER DEBUG]   尝试 AAD={desc}: {bytes_to_hex(aad)}")
            plaintext = _aes_gcm_decrypt(key, nonce, ciphered_data, gmac_tag, aad)
            print(f"[CIPHER DEBUG]   ✅ AAD={desc} 解密成功!")
            return plaintext, desc
        except Exception as e:
            print(f"[CIPHER DEBUG]   ❌ AAD={desc} 失败: {type(e).__name__}")
            continue

    # 所有方式都失败，抛出最后一个异常
    raise Exception("所有AAD构造方式都解密失败")


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
              当提供 keys 时，会根据 key_set 自动选择密钥

    Returns:
        (plaintext_apdu, CipherFrame): 解密后的APDU数据和加密帧信息

    Raises:
        CipheringError: 解析或解密失败
    """
    print(f"\n{'='*60}")
    print(f"[CIPHER DEBUG] ===== 开始解析加密帧 =====")
    print(f"{'='*60}")
    print(f"[CIPHER DEBUG] 输入数据长度: {len(data)} bytes")
    print(f"[CIPHER DEBUG] 输入数据前32字节: {bytes_to_hex(data[:32])}")

    if len(data) < 2:
        raise CipheringError("加密帧数据太短")

    offset = 0

    # 1. APDU Tag
    tag = data[offset]
    offset += 1
    print(f"[CIPHER DEBUG] APDU Tag: 0x{tag:02X} ({tag})")

    if tag not in (0xDA, 0xDB, 0xDC, 0xD8):
        raise CipheringError(f"不是加密APDU，tag={tag:#04x}")

    # 2. System Title (OCTET STRING, BER编码)
    print(f"\n[CIPHER DEBUG] --- 解析 System Title ---")
    try:
        st_length, offset = _parse_ber_length(data, offset)
        print(f"[CIPHER DEBUG] ST BER length: {st_length} (0x{st_length:02X})")
        if st_length == 0 or offset + st_length > len(data):
            raise CipheringError("System Title 长度无效")
        system_title = data[offset:offset + st_length]
        offset += st_length
        print(f"[CIPHER DEBUG] System Title value: {bytes_to_hex(system_title)} ({len(system_title)} bytes)")
    except CipheringError:
        raise
    except Exception as e:
        raise CipheringError(f"解析System Title失败: {e}")

    # 3. Ciphered Service Data (OCTET STRING, BER编码)
    print(f"\n[CIPHER DEBUG] --- 解析 Ciphered Service ---")
    try:
        cs_length, offset = _parse_ber_length(data, offset)
        print(f"[CIPHER DEBUG] CS BER length: {cs_length} (0x{cs_length:02X})")
        if cs_length == 0 or offset + cs_length > len(data):
            raise CipheringError(f"加密服务数据长度无效: {cs_length}")
        ciphered_service = data[offset:offset + cs_length]
        print(f"[CIPHER DEBUG] Ciphered Service 内容 ({len(ciphered_service)} bytes):")
        print(f"  前16字节: {bytes_to_hex(ciphered_service[:16])}")
        if len(ciphered_service) > 16:
            print(f"  后12字节: {bytes_to_hex(ciphered_service[-12:])}")
    except CipheringError:
        raise
    except Exception as e:
        raise CipheringError(f"解析加密服务数据失败: {e}")

    # 4. 解析 ciphered-service 内部结构
    print(f"\n[CIPHER DEBUG] --- 解析 Ciphered Service 内部字段 ---")
    cs_offset = 0

    # 4.1 Security Control 字节
    if cs_offset >= len(ciphered_service):
        raise CipheringError("数据不足，无法读取安全控制字节")
    sc_byte = ciphered_service[cs_offset]
    cs_offset += 1
    cipher_info = _parse_security_control(sc_byte)

    # 4.2 Invocation Counter (4字节，大端序)
    ic_length = 4  # Suite 1 固定4字节
    if cs_offset + ic_length > len(ciphered_service):
        raise CipheringError("数据不足，无法读取调用计数器")
    invocation_counter = int.from_bytes(
        ciphered_service[cs_offset:cs_offset + ic_length], "big"
    )
    cs_offset += ic_length
    print(f"\n[CIPHER DEBUG] Invocation Counter: {invocation_counter} (0x{invocation_counter:08X})")

    # 4.3 密文数据 + GMAC Tag
    remaining = ciphered_service[cs_offset:]
    gmac_tag = b""
    ciphered_data = remaining

    if cipher_info.authenticated and len(remaining) > 12:
        gmac_tag = remaining[-12:]
        ciphered_data = remaining[:-12]
        print(f"[CIPHER DEBUG] 密文数据: {len(ciphered_data)} bytes")
        print(f"  前8字节: {bytes_to_hex(ciphered_data[:8])}")
        print(f"[CIPHER DEBUG] GMAC Tag: {bytes_to_hex(gmac_tag)} (12 bytes)")
    else:
        print(f"[CIPHER DEBUG] 密文数据: {len(ciphered_data)} bytes (未认证)")
        print(f"  前8字节: {bytes_to_hex(ciphered_data[:8]) if len(ciphered_data) >= 8 else bytes_to_hex(ciphered_data)}")

    # 5. 选择解密密钥
    print(f"\n[CIPHER DEBUG] --- 选择密钥 ---")
    active_key = key
    active_key_name = "default (param key)"
    if keys is not None:
        selected_key = select_key_by_key_set(cipher_info.key_id, keys)
        if selected_key is not None:
            active_key = selected_key
            key_set_names = {0: "GUEK (Unicast)", 1: "GUBK (Broadcast)"}
            active_key_name = key_set_names.get(cipher_info.key_id, f"key_set={cipher_info.key_id}")
    print(f"[CIPHER DEBUG] 使用密钥: {active_key_name}")
    if active_key is not None:
        print(f"[CIPHER DEBUG] 密钥值: {bytes_to_hex(active_key)}")
    else:
        print(f"[CIPHER DEBUG] 密钥值: None (未提供密钥)")

    # 6. 计算 Nonce 和 AAD
    print(f"\n[CIPHER DEBUG] --- 计算 AES-GCM 参数 ---")
    nonce = _compute_nonce(system_title, invocation_counter, ic_length)
    aad = _compute_aad(sc_byte, system_title)

    # 7. 尝试解密
    print(f"\n[CIPHER DEBUG] --- 开始解密 ---")
    decrypt_success = False
    plaintext = b""
    aad_used = ""

    if cipher_info.encrypted and active_key is not None:
        try:
            gcm_key = _derive_gcm_key(active_key)
            print(f"[CIPHER DEBUG] AES-GCM 密钥 (16B): {bytes_to_hex(gcm_key)}")
            print(f"[CIPHER DEBUG] GMAC Tag 长度: {len(gmac_tag)} bytes")
            print(f"[CIPHER DEBUG] 使用底层Cipher API（支持12字节tag）")

            if cipher_info.authenticated:
                # 带认证标签，尝试多种AAD构造
                print(f"[CIPHER DEBUG] 尝试多种AAD构造方式:")
                plaintext, aad_used = _try_decrypt_with_multiple_aads(
                    gcm_key, nonce, ciphered_data, gmac_tag,
                    sc_byte, system_title, invocation_counter
                )
            else:
                # 仅加密（不认证），不需要tag验证
                print(f"[CIPHER DEBUG] 未认证模式，直接解密")
                # 使用AAD=SC
                aad = bytes([sc_byte])
                plaintext = _aes_gcm_decrypt(gcm_key, nonce, ciphered_data, b"", aad)
                aad_used = "SC byte (1B, no auth)"

            decrypt_success = True
            print(f"[CIPHER DEBUG] ✅ 解密成功! (AAD={aad_used})")
            print(f"[CIPHER DEBUG] 明文长度: {len(plaintext)} bytes")
            print(f"[CIPHER DEBUG] 明文前16字节: {bytes_to_hex(plaintext[:16])}")
            if len(plaintext) >= 16:
                print(f"[CIPHER DEBUG] 明文后16字节: {bytes_to_hex(plaintext[-16:])}")
        except Exception as e:
            decrypt_success = False
            plaintext = b""
            print(f"[CIPHER DEBUG] ❌ 解密失败: {e}")
            print(f"[CIPHER DEBUG] 可能的原因:")
            print(f"  1. 密钥不正确（最常见）")
            print(f"  2. Nonce/IV 计算错误")
            print(f"  3. AAD 构造错误（已尝试4种常见方式）")
            print(f"  4. GMAC Tag 长度或位置不对")
            print(f"  5. 密文数据不完整")
    elif not cipher_info.encrypted:
        # 未加密，直接返回
        plaintext = ciphered_data
        decrypt_success = True
        print(f"[CIPHER DEBUG] 未加密，直接返回明文")
    else:
        print(f"[CIPHER DEBUG] 未提供密钥，无法解密")

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

    print(f"\n{'='*60}")
    print(f"[CIPHER DEBUG] ===== 解析完成 =====")
    print(f"  解密成功: {decrypt_success}")
    print(f"  明文长度: {len(plaintext)} bytes")
    print(f"{'='*60}\n")

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
    suite_id: int = SUITE_1,
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
        key_id: 密钥集 (0=Unicast/GUEK, 1=Broadcast/GUBK)
        keys: 密钥字典
        suite_id: 安全套件ID (默认Suite 1)

    Returns:
        bytes: 完整的加密APDU数据（从0xDB tag开始）

    Raises:
        CipheringError: 加密失败
    """
    # 选择加密密钥
    active_key = key
    if keys is not None:
        selected_key = select_key_by_key_set(key_id, keys)
        if selected_key is not None:
            active_key = selected_key

    cipher_info = CipherInfo(
        encrypted=encrypted,
        authenticated=authenticated,
        compressed=compressed,
        key_id=key_id,
        suite_id=suite_id,
    )

    sc_byte = _build_security_control(cipher_info)

    # 调用计数器（4字节，大端序）
    ic_bytes = invocation_counter.to_bytes(4, "big")

    # 构建 ciphered-service 的内容
    if not encrypted and not authenticated:
        # 不加密也不认证，直接附加明文
        cs_content = bytes([sc_byte]) + ic_bytes + apdu
    else:
        # 使用AES-GCM加密（12字节tag，符合DLMS Suite 1规范）
        if active_key is None:
            raise CipheringError("加密需要提供密钥")

        gcm_key = _derive_gcm_key(active_key)

        # Nonce = System Title (8字节) + Invocation Counter (4字节) = 12字节
        nonce = system_title + ic_bytes
        nonce = nonce[:12]

        # 关联数据 = SC字节
        aad = bytes([sc_byte])

        # 加密并生成12字节认证标签（DLMS Suite 1标准）
        ciphertext, tag = _aes_gcm_encrypt(gcm_key, nonce, apdu, aad, tag_length=12)

        # 构建 ciphered-service 内容
        # SC(1) + IC(4) + ciphertext + tag(12)
        cs_content = bytes([sc_byte]) + ic_bytes + ciphertext + tag

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
