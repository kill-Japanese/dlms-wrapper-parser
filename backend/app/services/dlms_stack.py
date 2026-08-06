"""
DLMS协议栈总控模块

负责协调各层的解析和组帧流程:
Wrapper -> Ciphering -> Compression -> APDU -> DataModel

解析流程 (parse_frame):
1. Wrapper层解析 - 提取WPD头和载荷
2. 加密层检测 - 判断是否加密，尝试解密
3. 压缩层检测 - 判断是否压缩，尝试解压
4. APDU解析 - 解析应用层数据单元
5. 数据模型匹配 - 将解析到的对象与数据模型匹配

组帧流程 (build_frame):
1. APDU构建 - 构造应用层数据单元
2. 压缩（可选）- V.44压缩
3. 加密（可选）- AES-GCM加密
4. Wrapper封装 - 添加WPD头
"""
from datetime import datetime
from typing import Optional, Dict

from app.models.parse_result import ParseResult, ParseLogEntry
from app.models.wrapper import WrapperFrame
from app.models.cipher import CipherFrame
from app.utils.hex_utils import hex_to_bytes, bytes_to_hex

from app.services.wrapper import parse_wpd, build_wpd, is_wrapper_frame, WRAPPER_HEADER_LENGTH
from app.services.ciphering import parse_ciphered, build_ciphered, is_ciphered_apdu
from app.services.compression import decompress, compress, V44_AVAILABLE
from app.services.apdu_parser import parse_apdu, build_apdu
from app.services.datamodel import data_model_manager
from app.services.log_manager import log_manager
from app.utils.ber_encoder import decode_data, _decode_date_time


def _convert_bytes_to_hex(obj):
    """
    递归将对象中的 bytes/bytearray 转换为十六进制字符串。
    
    用于解决 Pydantic/FastAPI JSON 序列化时 bytes 类型无法序列化的问题。
    支持 dict、list、tuple、set 等嵌套结构。
    """
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    elif isinstance(obj, dict):
        return {k: _convert_bytes_to_hex(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_bytes_to_hex(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_bytes_to_hex(item) for item in obj)
    elif isinstance(obj, set):
        return {_convert_bytes_to_hex(item) for item in obj}
    return obj


def _enhance_items_with_datamodel(items):
    """
    利用数据模型信息增强数据项：
    1. 补充属性名称
    2. 用数据模型中的数据类型覆盖（如果更准确）
    3. 对于已知的特殊类型（如 date-time），进行值的转换
    
    Args:
        items: CosemDataItem 列表
        
    Returns:
        增强后的 items 列表
    """
    if not items or not data_model_manager.is_loaded:
        return items
    
    for item in items:
        try:
            # 匹配数据模型
            matched = data_model_manager.match_obis(
                class_id=item.class_id,
                obis_bytes=item.obis_bytes if item.obis_bytes else (hex_to_bytes(item.obis) if item.obis else b''),
                attribute_id=item.attribute_id,
            )
            
            if matched:
                # 补充属性名称到 description
                if matched.name and not item.description:
                    item.description = matched.name
                
                # 如果数据模型中有更准确的数据类型
                if matched.data_type:
                    model_data_type = matched.data_type.lower().replace('_', '-').replace(' ', '-')
                    
                    # 处理 octet_string[N] 格式
                    if 'octet-string' in model_data_type or 'octet_string' in model_data_type:
                        # 检查是否是 date-time 类型（12 字节 octet-string 且是 Clock 的 time 属性）
                        if item.class_id == 8 and item.attribute_id == 2:
                            # Clock time 属性 - 尝试解析为 date-time
                            try:
                                if isinstance(item.value, str):
                                    # 如果是字符串 hex
                                    val_bytes = hex_to_bytes(item.value.replace('"', '').replace(' ', ''))
                                elif isinstance(item.value, bytes):
                                    val_bytes = item.value
                                else:
                                    val_bytes = None
                                
                                if val_bytes and len(val_bytes) == 12:
                                    dt_dict = _decode_date_time(val_bytes, 12)
                                    item.value = dt_dict
                                    item.data_type = 'date-time'
                                    item.type = 'date-time'
                            except Exception:
                                pass
                        elif item.class_id == 8 and item.attribute_id in (5, 6):
                            # Clock 的 daylight_savings_begin/end 也是 date-time
                            try:
                                if isinstance(item.value, str):
                                    val_bytes = hex_to_bytes(item.value.replace('"', '').replace(' ', ''))
                                elif isinstance(item.value, bytes):
                                    val_bytes = item.value
                                else:
                                    val_bytes = None
                                
                                if val_bytes and len(val_bytes) == 12:
                                    dt_dict = _decode_date_time(val_bytes, 12)
                                    item.value = dt_dict
                                    item.data_type = 'date-time'
                                    item.type = 'date-time'
                            except Exception:
                                pass
        except Exception:
            # 单个项增强失败不影响其他项
            continue
    
    return items


def parse_frame(
    hex_data: str,
    encryption_key: Optional[str] = None,
    system_title: Optional[str] = None,
    guek: Optional[str] = None,
    gubk: Optional[str] = None,
    ak: Optional[str] = None,
    kek: Optional[str] = None,
    invocation_counter: Optional[int] = None,
) -> ParseResult:
    """
    解析DLMS帧（完整协议栈解析）

    支持多种DLMS密钥类型：
    - guek: Global Unicast Encryption Key（全局单播加密密钥，默认使用）
    - gubk: Global Unicast Broadcast Key（广播密钥）
    - ak: Authentication Key（认证密钥）
    - kek: Key Encryption Key（密钥加密密钥）
    - encryption_key: 兼容别名，映射到 guek

    根据加密帧中的 key_id 自动选择对应密钥进行解密。

    Args:
        hex_data: 十六进制帧数据
        encryption_key: 加密密钥（十六进制字符串，兼容别名，映射到guek）
        system_title: 系统标题（十六进制字符串，可选，用于解密验证）
        guek: Global Unicast Encryption Key（十六进制）
        gubk: Global Unicast Broadcast Key（十六进制）
        ak: Authentication Key（十六进制）
        kek: Key Encryption Key（十六进制）
        invocation_counter: 调用计数器（可选）

    Returns:
        ParseResult: 完整的解析结果
    """
    frame_id = log_manager.new_frame_id()
    timestamp = datetime.now().isoformat()

    result = ParseResult(
        frame_id=frame_id,
        timestamp=timestamp,
        raw_hex=hex_data.strip(),
    )

    # 构建密钥字典：guek 优先，encryption_key 作为兼容别名
    effective_guek = guek or encryption_key
    keys_dict: Dict[str, Optional[bytes]] = {}
    if effective_guek:
        keys_dict["guek"] = hex_to_bytes(effective_guek)
    if gubk:
        keys_dict["gubk"] = hex_to_bytes(gubk)
    if ak:
        keys_dict["ak"] = hex_to_bytes(ak)
    if kek:
        keys_dict["kek"] = hex_to_bytes(kek)

    # 用于向后兼容的单一密钥（GUEK）
    single_key_bytes = keys_dict.get("guek") if keys_dict else None

    try:
        # Step 1: 转换为字节
        try:
            data = hex_to_bytes(hex_data)
            log_manager.info(frame_id, "input", f"输入数据 {len(data)} 字节")
        except ValueError as e:
            log_manager.error(frame_id, "input", f"十六进制数据格式错误: {e}")
            result.errors.append(f"输入格式错误: {e}")
            result.parse_logs = _convert_logs(log_manager.get_logs(frame_id))
            return result

        # Step 2: Wrapper层解析
        try:
            if is_wrapper_frame(data):
                wrapper_frame = parse_wpd(data)
                result.wrapper = wrapper_frame
                log_manager.info(
                    frame_id, "wrapper",
                    f"Wrapper解析成功: version={wrapper_frame.version}, "
                    f"src={wrapper_frame.src_wport}, dst={wrapper_frame.dst_wport}, "
                    f"length={wrapper_frame.data_length}"
                )
                # 提取载荷用于后续解析
                payload = hex_to_bytes(wrapper_frame.payload_hex)
            else:
                # 没有Wrapper头，直接作为APDU处理
                log_manager.warn(frame_id, "wrapper", "未检测到Wrapper头，直接作为APDU处理")
                payload = data
        except Exception as e:
            log_manager.error(frame_id, "wrapper", f"Wrapper解析失败: {e}")
            result.errors.append(f"Wrapper解析失败: {e}")
            payload = data[WRAPPER_HEADER_LENGTH:] if len(data) > WRAPPER_HEADER_LENGTH else data

        # Step 3: 加密层解析
        try:
            if _is_ciphered_payload(payload):
                log_manager.info(frame_id, "ciphering", "检测到加密帧")

                has_any_key = bool(keys_dict)

                if has_any_key:
                    # 使用密钥字典，根据key_id自动选择密钥
                    # System Title 和 Invocation Counter 从帧中自动提取
                    plaintext, cipher_frame = parse_ciphered(
                        payload,
                        key=single_key_bytes,
                        keys=keys_dict if len(keys_dict) > 1 else None,
                    )
                    result.ciphering = cipher_frame

                    # 记录从帧中提取的信息
                    log_manager.info(
                        frame_id, "ciphering",
                        f"从帧中提取 System Title: {cipher_frame.system_title}"
                    )
                    log_manager.info(
                        frame_id, "ciphering",
                        f"从帧中提取 Invocation Counter: {cipher_frame.invocation_counter}"
                    )

                    # 记录使用的密钥类型
                    key_id = cipher_frame.cipher_info.key_id if cipher_frame.cipher_info else 0
                    key_type_names = {0: "GUEK (unicast)", 1: "GUBK (broadcast)", 2: "System Key"}
                    key_type = key_type_names.get(key_id, f"key_id={key_id}")
                    log_manager.info(
                        frame_id, "ciphering",
                        f"使用密钥类型: {key_type}"
                    )

                    # 记录SC字节各标志位
                    if cipher_frame.cipher_info:
                        ci = cipher_frame.cipher_info
                        flags = []
                        if ci.encrypted:
                            flags.append("加密")
                        if ci.authenticated:
                            flags.append("认证")
                        if ci.compressed:
                            flags.append("压缩")
                        if ci.ecc_signed:
                            flags.append("ECC签名")
                        if flags:
                            log_manager.info(
                                frame_id, "ciphering",
                                f"安全控制标志: {', '.join(flags)}"
                            )

                    if cipher_frame.decrypt_success:
                        log_manager.info(
                            frame_id, "ciphering",
                            f"解密成功，明文 {len(plaintext)} 字节"
                        )
                        payload = plaintext
                    else:
                        log_manager.warn(frame_id, "ciphering", "解密失败，请检查密钥")
                        result.errors.append("解密失败，请检查密钥是否正确")
                else:
                    # 没有密钥，只解析加密帧结构
                    plaintext, cipher_frame = parse_ciphered(payload, None)
                    result.ciphering = cipher_frame
                    log_manager.warn(frame_id, "ciphering", "未提供密钥，无法解密")
                    # 记录从帧中提取的信息（即使未解密也展示
                    log_manager.info(
                        frame_id, "ciphering",
                        f"从帧中提取 System Title: {cipher_frame.system_title}"
                    )
                    log_manager.info(
                        frame_id, "ciphering",
                        f"从帧中提取 Invocation Counter: {cipher_frame.invocation_counter}"
                    )
                    # 无法继续解析APDU
                    result.parse_logs = _convert_logs(log_manager.get_logs(frame_id))
                    return result
            else:
                log_manager.debug(frame_id, "ciphering", "未检测到加密")
        except Exception as e:
            log_manager.error(frame_id, "ciphering", f"加密层解析失败: {e}")
            result.errors.append(f"加密层解析失败: {e}")

        # Step 4: 压缩层检测
        try:
            if result.ciphering and result.ciphering.cipher_info and result.ciphering.cipher_info.compressed:
                log_manager.info(frame_id, "compression", "检测到压缩数据")
                if V44_AVAILABLE:
                    try:
                        decompressed = decompress(payload)
                        log_manager.info(
                            frame_id, "compression",
                            f"解压成功: {len(payload)} -> {len(decompressed)} 字节"
                        )
                        result.compression = {
                            "algorithm": "V.44",
                            "compressed_size": len(payload),
                            "original_size": len(decompressed),
                            "ratio": round(len(payload) / len(decompressed), 4) if decompressed else 0,
                            "decompressed": True,
                        }
                        payload = decompressed
                    except Exception as e:
                        log_manager.error(frame_id, "compression", f"解压失败: {e}")
                        result.errors.append(f"解压失败: {e}")
                else:
                    log_manager.warn(frame_id, "compression", "V.44模块不可用，跳过解压")
                    result.compression = {
                        "algorithm": "V.44",
                        "available": False,
                    }
        except Exception as e:
            log_manager.error(frame_id, "compression", f"压缩层处理失败: {e}")

        # Step 5: APDU解析
        try:
            apdu_obj = parse_apdu(payload)

            # 利用数据模型增强数据项（补充属性名、转换特殊类型如date-time等）
            if hasattr(apdu_obj, 'items') and apdu_obj.items:
                _enhance_items_with_datamodel(apdu_obj.items)

            # 将 bytes 转为 hex 字符串，避免 JSON 序列化失败
            result.apdu = _convert_bytes_to_hex(apdu_obj.model_dump())
            log_manager.info(
                frame_id, "apdu",
                f"APDU解析成功: type={apdu_obj.type_name} (tag={apdu_obj.tag})"
            )

            # 提取数据项并匹配数据模型
            if hasattr(apdu_obj, 'items') and apdu_obj.items:
                for item in apdu_obj.items:
                    matched = data_model_manager.match_obis(
                        class_id=item.class_id,
                        obis_bytes=item.obis_bytes if hasattr(item, 'obis_bytes') and item.obis_bytes else (hex_to_bytes(item.obis) if item.obis else b''),
                        attribute_id=item.attribute_id,
                    )
                    if matched:
                        result.matched_objects.append(matched.model_dump())

            # Step 6: Push 数据深度解析（Profile buffer 逐元素解析等）
            # 当 APDU 类型为 DataNotification 且包含 push_object_list 时，
            # 使用 PushDataResolver 结合 Capture Objects 配置深度解析
            if apdu_obj.type_name == 'DataNotification' and hasattr(apdu_obj, 'items') and apdu_obj.items:
                try:
                    from app.services.push_data_resolver import PushDataResolver
                    from app.services.profile_capture_store import get_profile_capture_store
                    from app.services.cosem_standards import get_standards_manager

                    # 从 APDU 解析结果中获取 push_object_list
                    apdu_dict = result.apdu if isinstance(result.apdu, dict) else {}
                    push_object_list = apdu_dict.get('push_object_list', [])
                    has_class40_template = apdu_dict.get('has_class40_template', False)

                    # 当存在 Class 40 模版时，push_object_list 的第一个条目是
                    # Class 40 自身（push setup 的属性2），它在 notification_items
                    # 中没有对应的值。必须跳过它，否则所有项会错位一位。
                    if has_class40_template and len(push_object_list) > 0:
                        push_object_list = push_object_list[1:]

                    if push_object_list:
                        # 构造 notification_items
                        notification_items = []
                        for item in apdu_obj.items:
                            notification_items.append({
                                'value': item.value,
                                'type': item.data_type or item.type or '',
                                'class_id': item.class_id,
                                'obis': item.obis,
                                'attribute_id': item.attribute_id,
                            })

                        # 获取依赖组件
                        profile_capture_store = get_profile_capture_store()
                        standards_manager = get_standards_manager()

                        # 执行深度解析
                        push_result = PushDataResolver.resolve_notification_items(
                            notification_items=notification_items,
                            push_object_list=push_object_list,
                            data_model=data_model_manager if data_model_manager.is_loaded else None,
                            standards_manager=standards_manager,
                            profile_capture_store=profile_capture_store,
                        )

                        result.push_resolved = _convert_bytes_to_hex(push_result)

                        profile_count = sum(
                            1 for r in push_result.get('resolved_items', [])
                            if r.get('type') == 'profile_buffer'
                        )
                        if profile_count > 0:
                            log_manager.info(
                                frame_id, "push_resolver",
                                f"Push 深度解析完成: {profile_count} 个 Profile buffer 已解析"
                            )
                except Exception as e:
                    log_manager.warn(frame_id, "push_resolver", f"Push 深度解析失败: {e}")

        except Exception as e:
            log_manager.error(frame_id, "apdu", f"APDU解析失败: {e}")
            result.errors.append(f"APDU解析失败: {e}")
            result.apdu = {"raw_hex": bytes_to_hex(payload), "parse_error": str(e)}

    except Exception as e:
        log_manager.error(frame_id, "system", f"解析过程异常: {e}")
        result.errors.append(f"系统错误: {e}")

    # 收集日志
    result.parse_logs = _convert_logs(log_manager.get_logs(frame_id))

    return result


def _is_ciphered_payload(data: bytes) -> bool:
    """
    判断载荷是否为加密数据

    通过多步启发式判断：
    1. 首先检查是否为已知的明文APDU类型（排除加密类型）
    2. 检查是否为GeneralGloCiphering等加密APDU
    3. 检查是否为原始加密数据格式（以安全控制字节开始）
    """
    if not data:
        return False

    first_byte = data[0]

    # 常见的明文APDU标签（如果匹配，大概率不是加密数据）
    # DataNotification=15, GetRequest=192, GetResponse=193,
    # SetRequest=194, SetResponse=195, EventNotification=196,
    # ActionRequest=199, ActionResponse=200, InitiateRequest=1,
    # InitiateResponse=8, ConfirmedServiceError=14
    plaintext_apdu_tags = {15, 192, 193, 194, 195, 196, 199, 200, 1, 8, 14}

    if first_byte in plaintext_apdu_tags:
        # 还需要进一步验证：检查是否真的是明文APDU
        # 对于DataNotification(15)，检查invoke_id是否合理
        if first_byte == 15 and len(data) >= 5:
            # DataNotification: tag(1) + invoke_id(4) + ...
            # invoke_id的高位字节通常是0或较小的值
            # 如果invoke_id看起来像一个合理的值，认为是明文
            invoke_id_high = data[1]
            if invoke_id_high < 0x10:  # 高位字节较小，更可能是invoke_id
                return False
        elif first_byte in (192, 193, 194, 195, 196, 199, 200):
            # Get/Set/Action类APDU: tag(1) + type(1) + invoke_id(4)
            if len(data) >= 6:
                get_type = data[1]
                # type通常是1, 2, 或3
                if get_type in (1, 2, 3):
                    return False

    # 加密APDU标签
    # GeneralGloCiphering=219, GeneralCiphering=218,
    # GeneralDedCiphering=220, GeneralSign=216
    cipher_apdu_tags = {216, 218, 219, 220}
    if first_byte in cipher_apdu_tags:
        return True

    # 检查是否为原始加密数据（从安全控制字节开始，无APDU标签）
    # 安全控制字节的特征:
    # - bit 5-7（高位3位）为0
    # - 至少设置了加密或认证位（bit 0 或 bit 1）
    # - 后面紧跟着系统标题长度指示
    if (first_byte & 0xE0) == 0 and (first_byte & 0x03):
        # 验证: 安全控制字节后应该是8字节系统标题 + 调用计数器长度字节
        if len(data) > 9:
            # 系统标题是8字节，后面是调用计数器长度(通常是4)
            ic_length_pos = 9  # 1(SC) + 8(ST) = 9
            ic_length = data[ic_length_pos]
            # 调用计数器长度通常在1-5之间
            if 1 <= ic_length <= 5:
                # 很可能是加密数据
                return True

    return False


def _convert_logs(logs: list) -> list:
    """将日志字典转换为ParseLogEntry对象列表"""
    result = []
    for log in logs:
        result.append(ParseLogEntry(
            level=log["level"],
            step=log["step"],
            message=log["message"],
            timestamp=log["timestamp"],
        ))
    return result


def build_frame(
    apdu_type: str,
    params: dict,
    src_wport: int = 1,
    dst_wport: int = 16,
    encrypt: bool = False,
    encryption_key: Optional[str] = None,
    system_title: Optional[str] = None,
    guek: Optional[str] = None,
    gubk: Optional[str] = None,
    ak: Optional[str] = None,
    kek: Optional[str] = None,
    invocation_counter: int = 1,
    key_id: int = 0,
) -> dict:
    """
    构建DLMS帧

    支持多种DLMS密钥类型：
    - guek: Global Unicast Encryption Key（全局单播加密密钥，默认使用）
    - gubk: Global Unicast Broadcast Key（广播密钥）
    - ak: Authentication Key（认证密钥）
    - kek: Key Encryption Key（密钥加密密钥）
    - encryption_key: 兼容别名，映射到 guek

    Args:
        apdu_type: APDU类型
        params: APDU参数
        src_wport: 源WPort
        dst_wport: 目的WPort
        encrypt: 是否加密
        encryption_key: 加密密钥（十六进制，兼容别名，映射到guek）
        system_title: 系统标题（十六进制）
        guek: Global Unicast Encryption Key（十六进制）
        gubk: Global Unicast Broadcast Key（十六进制）
        ak: Authentication Key（十六进制）
        kek: Key Encryption Key（十六进制）
        invocation_counter: 调用计数器
        key_id: 密钥标识 (0=unicast/GUEK, 1=broadcast/GUBK, 2=system)

    Returns:
        dict: {success, hex_data, frame_length, message}
    """
    try:
        # 构建密钥字典
        effective_guek = guek or encryption_key
        keys_dict: Dict[str, Optional[bytes]] = {}
        if effective_guek:
            keys_dict["guek"] = hex_to_bytes(effective_guek)
        if gubk:
            keys_dict["gubk"] = hex_to_bytes(gubk)
        if ak:
            keys_dict["ak"] = hex_to_bytes(ak)
        if kek:
            keys_dict["kek"] = hex_to_bytes(kek)

        # Step 1: 构建APDU
        apdu_data = build_apdu(apdu_type, params)

        # Step 2: 加密（可选）
        if encrypt:
            if not keys_dict or not system_title:
                key_type_names = {0: "GUEK", 1: "GUBK", 2: "System Key"}
                required_key = key_type_names.get(key_id, "GUEK")
                return {
                    "success": False,
                    "hex_data": "",
                    "frame_length": 0,
                    "message": f"加密需要提供{required_key}密钥和系统标题",
                }
            st_bytes = hex_to_bytes(system_title)
            try:
                apdu_data = build_ciphered(
                    apdu_data,
                    key=keys_dict.get("guek"),
                    system_title=st_bytes,
                    invocation_counter=invocation_counter,
                    encrypted=True,
                    authenticated=True,
                    compressed=False,
                    key_id=key_id,
                    keys=keys_dict if len(keys_dict) > 1 else None,
                )
            except Exception as e:
                return {
                    "success": False,
                    "hex_data": "",
                    "frame_length": 0,
                    "message": f"加密失败: {e}",
                }

        # Step 3: Wrapper封装
        frame = build_wpd(apdu_data, src_wport=src_wport, dst_wport=dst_wport)

        return {
            "success": True,
            "hex_data": bytes_to_hex(frame),
            "frame_length": len(frame),
            "message": "组帧成功",
        }

    except Exception as e:
        return {
            "success": False,
            "hex_data": "",
            "frame_length": 0,
            "message": f"组帧失败: {e}",
        }
