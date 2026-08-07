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
from app.utils.obis_utils import obis_str_to_bytes


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


def _scan_raw_data_for_descriptors(raw_bytes: bytes, result, frame_id: str):
    """
    扫描原始APDU字节流中的COSEM属性描述符模式，进行数据模型匹配。

    当APDU解析失败或APDU类型不直接携带描述符时（如GetResponse），
    通过模式匹配从原始数据中提取 class_id + OBIS + attribute_id 组合，
    并匹配数据模型。

    扫描模式:
    - octet-string(6) 模式: 09 06 XX XX XX XX XX XX (OBIS码)
      前面通常有 class_id (12 00 XX = long-unsigned) 和 structure tag (02 04)
      后面通常有 attribute_id (0f XX = integer)
    """
    if not data_model_manager.is_loaded:
        return

    if not raw_bytes or len(raw_bytes) < 10:
        return

    matched_set = set()  # 用于去重: (class_id, obis_hex, attr_id)
    # 收集已有的 (class_id, attr_id) 对，用于类级回退去重
    existing_class_attr = set()
    for obj in result.matched_objects:
        existing_class_attr.add((obj.get('class_id'), obj.get('attribute_id', 0)))

    # 模式1: 扫描 push_object_list / capture_objects 结构
    # 每个条目格式: structure(4) { long-unsigned(class_id), octet-string(6)(OBIS), integer(attr_id), long-unsigned(data_index) }
    # 字节模式: 02 04 12 00 XX 09 06 YY YY YY YY YY YY 0f ZZ 12 00 WW
    i = 0
    while i < len(raw_bytes) - 17:
        # 查找 structure(4) + long-unsigned + octet-string(6) 模式
        if (raw_bytes[i] == 0x02 and raw_bytes[i+1] == 0x04 and
            raw_bytes[i+2] == 0x12 and raw_bytes[i+3] == 0x00 and
            raw_bytes[i+5] == 0x09 and raw_bytes[i+6] == 0x06):

            class_id = raw_bytes[i+4]  # class_id (1 byte, since high byte is 0x00)
            obis_bytes = raw_bytes[i+7:i+13]  # 6 bytes OBIS

            # 查找后面的 attribute_id (0f XX = integer)
            attr_id = 2  # 默认值
            if i + 13 < len(raw_bytes) and raw_bytes[i+13] == 0x0f:
                attr_id = raw_bytes[i+14]

            # 构建唯一标识
            obis_hex = obis_bytes.hex()
            key = (class_id, obis_hex, attr_id)
            if key in matched_set:
                i += 1
                continue
            matched_set.add(key)

            try:
                matched = data_model_manager.match_obis(
                    class_id=class_id,
                    obis_bytes=obis_bytes,
                    attribute_id=attr_id,
                )
                if matched:
                    matched_dict = matched.model_dump()
                    if matched_dict not in result.matched_objects:
                        result.matched_objects.append(matched_dict)
                        existing_class_attr.add((class_id, attr_id))
                        a, b = obis_bytes[0], obis_bytes[1]
                        c, d = obis_bytes[2], obis_bytes[3]
                        e, f = obis_bytes[4], obis_bytes[5]
                        obis_str = f"{a}-{b}:{c}.{d}.{e}.{f}"
                        log_manager.info(
                            frame_id, "datamodel",
                            f"数模匹配成功(原始扫描): class={class_id}, obis={obis_str}, "
                            f"attr={attr_id} -> {matched.name}"
                        )
                elif hasattr(data_model_manager, 'match_by_class'):
                    # 类级回退匹配 - 跳过已有同class+attr的匹配
                    if (class_id, attr_id) not in existing_class_attr:
                        fallback = data_model_manager.match_by_class(class_id, attr_id)
                        if fallback:
                            fb_dict = fallback.model_dump()
                            fb_dict["is_fallback"] = True
                            a, b = obis_bytes[0], obis_bytes[1]
                            c, d = obis_bytes[2], obis_bytes[3]
                            e, f = obis_bytes[4], obis_bytes[5]
                            fb_dict["original_obis"] = f"{a}-{b}:{c}.{d}.{e}.{f}"
                            if fb_dict not in result.matched_objects:
                                result.matched_objects.append(fb_dict)
                                existing_class_attr.add((class_id, attr_id))
                            log_manager.info(
                                frame_id, "datamodel",
                                f"数模回退匹配(原始扫描): class={class_id} -> "
                                f"{fallback.name} (obis={fallback.obis})"
                            )
            except Exception:
                pass

        i += 1

    # 模式2: 扫描独立的 octet-string(6) 模式（仅OBIS，无class_id上下文）
    # 尝试从前后字节推断 class_id
    i = 0
    while i < len(raw_bytes) - 8:
        if raw_bytes[i] == 0x09 and raw_bytes[i+1] == 0x06:
            obis_bytes = raw_bytes[i+2:i+8]

            # 跳过全零或无效OBIS
            if obis_bytes == b'\x00\x00\x00\x00\x00\x00':
                i += 1
                continue

            # 尝试从前面的 long-unsigned (12 00 XX) 获取 class_id
            class_id = None
            if i >= 3 and raw_bytes[i-3] == 0x12 and raw_bytes[i-2] == 0x00:
                class_id = raw_bytes[i-1]
            # 也尝试从更前面查找 structure + long-unsigned
            elif i >= 4 and raw_bytes[i-4] == 0x02 and raw_bytes[i-3] == 0x04 and raw_bytes[i-2] == 0x12 and raw_bytes[i-1] == 0x00:
                if i >= 5:
                    class_id = raw_bytes[i-5]  # 这不对，让我重新检查

            # 如果无法确定class_id，尝试常见class_id
            class_ids_to_try = [class_id] if class_id else [1, 3, 4, 7, 8, 40]
            class_ids_to_try = [c for c in class_ids_to_try if c is not None]

            # 尝试获取 attribute_id
            attr_id = 2  # 默认
            if i + 8 < len(raw_bytes) and raw_bytes[i+8] == 0x0f:
                attr_id = raw_bytes[i+9]

            obis_hex = obis_bytes.hex()
            for cid in class_ids_to_try:
                key = (cid, obis_hex, attr_id)
                if key in matched_set:
                    continue
                matched_set.add(key)

                try:
                    matched = data_model_manager.match_obis(
                        class_id=cid,
                        obis_bytes=obis_bytes,
                        attribute_id=attr_id,
                    )
                    if matched:
                        matched_dict = matched.model_dump()
                        if matched_dict not in result.matched_objects:
                            result.matched_objects.append(matched_dict)
                            existing_class_attr.add((cid, attr_id))
                            a, b = obis_bytes[0], obis_bytes[1]
                            c, d = obis_bytes[2], obis_bytes[3]
                            e, f = obis_bytes[4], obis_bytes[5]
                            obis_str = f"{a}-{b}:{c}.{d}.{e}.{f}"
                            log_manager.info(
                                frame_id, "datamodel",
                                f"数模匹配成功(OBIS扫描): class={cid}, obis={obis_str}, "
                                f"attr={attr_id} -> {matched.name}"
                            )
                        break  # 找到匹配就停止尝试其他class_id
                    elif hasattr(data_model_manager, 'match_by_class'):
                        # 类级回退匹配 - 跳过已有同class+attr的匹配
                        if (cid, attr_id) not in existing_class_attr:
                            fallback = data_model_manager.match_by_class(cid, attr_id)
                            if fallback:
                                fb_dict = fallback.model_dump()
                                fb_dict["is_fallback"] = True
                                a, b = obis_bytes[0], obis_bytes[1]
                                c, d = obis_bytes[2], obis_bytes[3]
                                e, f = obis_bytes[4], obis_bytes[5]
                                fb_dict["original_obis"] = f"{a}-{b}:{c}.{d}.{e}.{f}"
                                if fb_dict not in result.matched_objects:
                                    result.matched_objects.append(fb_dict)
                                    existing_class_attr.add((cid, attr_id))
                                    log_manager.info(
                                        frame_id, "datamodel",
                                        f"数模回退匹配(OBIS扫描): class={cid} -> "
                                        f"{fallback.name} (obis={fallback.obis})"
                                    )
                                break  # 找到回退匹配也停止
                except Exception:
                    continue

        i += 1


def _matched_apdu_descriptors(apdu_obj, result, frame_id: str):
    """
    对 GetRequest/SetRequest/ActionRequest/EventNotification 等APDU的
    COSEM属性/方法描述符进行数据模型匹配。

    这些APDU类型在解析后直接携带 class_id, obis, attribute_id/method_id 字段，
    但不在 items 列表中。本函数提取这些字段并匹配数据模型，
    将匹配结果加入 result.matched_objects。
    """
    if not data_model_manager.is_loaded:
        return

    type_name = apdu_obj.type_name

    # 收集需要匹配的描述符列表
    descriptors_to_match = []

    if type_name == "GetRequest":
        if hasattr(apdu_obj, 'get_type') and apdu_obj.get_type == 1:
            # GetRequest-Normal: 单个描述符
            if apdu_obj.class_id is not None and apdu_obj.obis:
                descriptors_to_match.append({
                    "class_id": apdu_obj.class_id,
                    "obis": apdu_obj.obis,
                    "attribute_id": apdu_obj.attribute_id or 2,
                })
        elif hasattr(apdu_obj, 'get_type') and apdu_obj.get_type == 3:
            # GetRequest-WithList: 多个描述符
            if hasattr(apdu_obj, 'attribute_list') and apdu_obj.attribute_list:
                for desc in apdu_obj.attribute_list:
                    descriptors_to_match.append({
                        "class_id": desc.class_id,
                        "obis": desc.obis,
                        "attribute_id": desc.attribute_id,
                    })

    elif type_name == "SetRequest":
        if hasattr(apdu_obj, 'set_type') and apdu_obj.set_type == 1:
            if apdu_obj.class_id is not None and apdu_obj.obis:
                descriptors_to_match.append({
                    "class_id": apdu_obj.class_id,
                    "obis": apdu_obj.obis,
                    "attribute_id": apdu_obj.attribute_id or 2,
                })

    elif type_name == "ActionRequest":
        if hasattr(apdu_obj, 'action_type') and apdu_obj.action_type == 1:
            if apdu_obj.class_id is not None and apdu_obj.obis:
                # ActionRequest 使用 method_id 而非 attribute_id
                descriptors_to_match.append({
                    "class_id": apdu_obj.class_id,
                    "obis": apdu_obj.obis,
                    "attribute_id": getattr(apdu_obj, 'method_id', 1),  # method_id 作为 attribute_id 传入匹配
                })

    elif type_name == "EventNotification":
        if apdu_obj.class_id is not None and apdu_obj.obis:
            descriptors_to_match.append({
                "class_id": apdu_obj.class_id,
                "obis": apdu_obj.obis,
                "attribute_id": apdu_obj.attribute_id or 2,
            })

    elif type_name in ("GetResponse", "SetResponse", "ActionResponse"):
        # GetResponse/SetResponse/ActionResponse 不直接携带描述符
        # 但如果解析成功且value中包含结构化数据（如push_object_list），
        # 则通过原始数据扫描进行匹配
        raw_hex = getattr(apdu_obj, 'raw_hex', '') or getattr(apdu_obj, 'raw_data_hex', '')
        if raw_hex:
            try:
                raw_bytes = hex_to_bytes(raw_hex)
                _scan_raw_data_for_descriptors(raw_bytes, result, frame_id)
            except Exception:
                pass
        return  # 直接返回，后面的描述符匹配不适用于Response类型

    # 已匹配的 (class_id, attr_id) 对，用于类级回退去重
    matched_class_attr = set()

    def _do_match(class_id, obis_bytes_val, attr_id, obis_str_for_log=""):
        """执行精确匹配+类级回退匹配"""
        try:
            matched = data_model_manager.match_obis(
                class_id=class_id,
                obis_bytes=obis_bytes_val,
                attribute_id=attr_id,
            )
            if matched:
                matched_dict = matched.model_dump()
                if matched_dict not in result.matched_objects:
                    result.matched_objects.append(matched_dict)
                    matched_class_attr.add((class_id, attr_id))
                    log_manager.info(
                        frame_id, "datamodel",
                        f"数模匹配成功: class={class_id}, obis={obis_str_for_log}, "
                        f"attr={attr_id} -> {matched.name}"
                    )
                return True
            # 类级回退匹配
            if hasattr(data_model_manager, 'match_by_class'):
                if (class_id, attr_id) in matched_class_attr:
                    return True  # 已有同class+attr的匹配
                fallback = data_model_manager.match_by_class(class_id, attr_id)
                if fallback:
                    fb_dict = fallback.model_dump()
                    fb_dict["is_fallback"] = True
                    fb_dict["original_obis"] = obis_str_for_log
                    if fb_dict not in result.matched_objects:
                        result.matched_objects.append(fb_dict)
                        matched_class_attr.add((class_id, attr_id))
                        log_manager.info(
                            frame_id, "datamodel",
                            f"数模回退匹配: class={class_id}, obis={obis_str_for_log} -> "
                            f"使用类级匹配 {fallback.obis}: {fallback.name}"
                        )
                    return True
        except Exception:
            pass
        return False

    # 主描述符匹配（精确+类级回退）
    for desc in descriptors_to_match:
        try:
            obis_val = desc["obis"]
            if isinstance(obis_val, str):
                if "-" in obis_val or ":" in obis_val:
                    obis_bytes = obis_str_to_bytes(obis_val)
                else:
                    obis_bytes = hex_to_bytes(obis_val)
            else:
                obis_bytes = obis_val
            obis_str = desc["obis"] if isinstance(desc["obis"], str) else bytes_to_hex(obis_bytes)
            _do_match(desc["class_id"], obis_bytes, desc["attribute_id"], obis_str)
        except Exception:
            continue

    # SetRequest的value中提取capture_objects逐项匹配
    # capture_objects格式: array of structure {class_id, obis, attribute_id, data_index}
    if type_name == "SetRequest" and hasattr(apdu_obj, 'value') and isinstance(apdu_obj.value, list):
        from app.utils.obis_utils import obis_bytes_to_str as _obis_to_str
        for item in apdu_obj.value:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                co_class_id = item[0] if isinstance(item[0], int) else None
                co_obis_raw = item[1]
                co_attr_id = item[2] if isinstance(item[2], int) else 2
                if co_class_id is None:
                    continue
                # 转换OBIS为bytes
                if isinstance(co_obis_raw, str):
                    try:
                        if "-" in co_obis_raw or ":" in co_obis_raw:
                            co_obis_bytes = obis_str_to_bytes(co_obis_raw)
                        else:
                            co_obis_bytes = hex_to_bytes(co_obis_raw)
                        co_obis_str = co_obis_raw
                    except Exception:
                        continue
                elif isinstance(co_obis_raw, (bytes, bytearray)):
                    co_obis_bytes = bytes(co_obis_raw)
                    co_obis_str = _obis_to_str(co_obis_bytes)
                else:
                    continue
                _do_match(co_class_id, co_obis_bytes, co_attr_id, co_obis_str)

    # 对所有APDU类型（包括Request类型），额外扫描原始数据中的OBIS模式
    # 这对于SetRequest（value中包含capture_objects等嵌套描述符）尤为重要
    try:
        raw_hex = getattr(apdu_obj, 'raw_hex', '') or getattr(apdu_obj, 'raw_data_hex', '')
        if raw_hex:
            raw_bytes = hex_to_bytes(raw_hex)
            _scan_raw_data_for_descriptors(raw_bytes, result, frame_id)
    except Exception:
        pass


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
            # 1. DataNotification: 通过 items 列表匹配
            if hasattr(apdu_obj, 'items') and apdu_obj.items:
                for item in apdu_obj.items:
                    matched = data_model_manager.match_obis(
                        class_id=item.class_id,
                        obis_bytes=item.obis_bytes if hasattr(item, 'obis_bytes') and item.obis_bytes else (hex_to_bytes(item.obis) if item.obis else b''),
                        attribute_id=item.attribute_id,
                    )
                    if matched:
                        result.matched_objects.append(matched.model_dump())

            # 2. GetRequest/SetRequest/ActionRequest/EventNotification: 通过 descriptor 字段匹配
            #    GetResponse/SetResponse/ActionResponse: 通过原始数据扫描匹配
            _matched_apdu_descriptors(apdu_obj, result, frame_id)

            # 3. 对所有APDU类型，额外扫描原始数据中的OBIS模式进行数模匹配
            #    这可以捕获APDU解析失败或解析不完整时遗漏的描述符
            if not result.matched_objects or apdu_obj.type_name in ("GetResponse", "SetResponse", "ActionResponse"):
                _scan_raw_data_for_descriptors(payload, result, frame_id)

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

            # 即使APDU解析失败，也尝试扫描原始数据中的OBIS模式进行数模匹配
            _scan_raw_data_for_descriptors(payload, result, frame_id)

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
    # DataNotification=15(0x0F), GetRequest=192(0xC0), SetRequest=193(0xC1),
    # EventNotification=194(0xC2), ActionRequest=195(0xC3), GetResponse=196(0xC4),
    # SetResponse=197(0xC5), ActionResponse=199(0xC7), InitiateRequest=1,
    # InitiateResponse=8, ConfirmedServiceError=14
    plaintext_apdu_tags = {15, 192, 193, 194, 195, 196, 197, 199, 1, 8, 14}

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
    compress: bool = False,
    encryption_key: Optional[str] = None,
    system_title: Optional[str] = None,
    guek: Optional[str] = None,
    gubk: Optional[str] = None,
    ak: Optional[str] = None,
    kek: Optional[str] = None,
    invocation_counter: int = 1,
    key_id: int = 0,
    raw_apdu_hex: Optional[str] = None,
    with_wrapper: bool = False,
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
        compress: 是否V.44压缩（加密前压缩）
        encryption_key: 加密密钥（十六进制，兼容别名，映射到guek）
        system_title: 系统标题（十六进制）
        guek: Global Unicast Encryption Key（十六进制）
        gubk: Global Unicast Broadcast Key（十六进制）
        ak: Authentication Key（十六进制）
        kek: Key Encryption Key（十六进制）
        invocation_counter: 调用计数器
        key_id: 密钥标识 (0=unicast/GUEK, 1=broadcast/GUBK, 2=system)
        raw_apdu_hex: 原始APDU十六进制数据（如果提供，则跳过APDU构建步骤，直接使用此数据进行打包）
        with_wrapper: 是否封装Wrapper帧（默认False，仅APDU->V.44->general-glo-ciphering）

    Returns:
        dict: {success, hex_data, frame_length, message}
    }
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

        # Step 1: 获取APDU数据
        if raw_apdu_hex:
            # 使用原始APDU数据，跳过构建步骤
            apdu_data = hex_to_bytes(raw_apdu_hex)
        else:
            apdu_data = build_apdu(apdu_type, params)

        # Step 2: 压缩 + 加密（可选）
        # 打包流程: APDU -> V.44压缩 -> AES-GCM加密 -> General-Glo-Ciphering封装 -> Wrapper
        # 当 compress=True 时，SC字节会置位压缩标志(bit7)，加密后SC同时置位加密标志(bit5)
        if encrypt or compress:
            if encrypt and (not keys_dict or not system_title):
                key_type_names = {0: "GUEK", 1: "GUBK", 2: "System Key"}
                required_key = key_type_names.get(key_id, "GUEK")
                return {
                    "success": False,
                    "hex_data": "",
                    "frame_length": 0,
                    "message": f"加密需要提供{required_key}密钥和系统标题",
                }
            if compress and not encrypt:
                # 仅压缩不加密 - 使用 General-Glo-Ciphering 封装但不加密
                # SC字节只置位压缩标志
                if not system_title:
                    return {
                        "success": False,
                        "hex_data": "",
                        "frame_length": 0,
                        "message": "压缩封装需要提供系统标题",
                    }
                st_bytes = hex_to_bytes(system_title)
                try:
                    apdu_data = build_ciphered(
                        apdu_data,
                        key=keys_dict.get("guek"),
                        system_title=st_bytes,
                        invocation_counter=invocation_counter,
                        encrypted=False,
                        authenticated=False,
                        compressed=True,
                        key_id=key_id,
                        keys=keys_dict if len(keys_dict) > 1 else None,
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "hex_data": "",
                        "frame_length": 0,
                        "message": f"压缩封装失败: {e}",
                    }
            elif encrypt:
                st_bytes = hex_to_bytes(system_title) if system_title else b""
                try:
                    apdu_data = build_ciphered(
                        apdu_data,
                        key=keys_dict.get("guek"),
                        system_title=st_bytes,
                        invocation_counter=invocation_counter,
                        encrypted=True,
                        authenticated=True,
                        compressed=compress,  # 传入压缩标志
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

        # Step 3: Wrapper封装（可选）
        # 打包流程: APDU -> V.44压缩 -> general-glo-ciphering -> Wrapper封装
        # 默认不封装Wrapper，仅当 with_wrapper=True 时添加
        if with_wrapper:
            frame = build_wpd(apdu_data, src_wport=src_wport, dst_wport=dst_wport)
        else:
            frame = apdu_data

        result = {
            "success": True,
            "hex_data": bytes_to_hex(frame),
            "frame_length": len(frame),
            "message": "组帧成功",
        }

        if with_wrapper:
            # 返回 Wrapper 封装前的数据（已压缩+加密）和 Wrapper 元数据
            result["pre_wrapper_hex"] = bytes_to_hex(apdu_data)
            result["pre_wrapper_length"] = len(apdu_data)
            result["wrapper_version"] = 1
            result["wrapper_src_wport"] = src_wport
            result["wrapper_dst_wport"] = dst_wport

        return result

    except Exception as e:
        return {
            "success": False,
            "hex_data": "",
            "frame_length": 0,
            "message": f"组帧失败: {e}",
        }
