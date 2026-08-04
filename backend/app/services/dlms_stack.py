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
from typing import Optional

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


def parse_frame(
    hex_data: str,
    encryption_key: Optional[str] = None,
    system_title: Optional[str] = None,
) -> ParseResult:
    """
    解析DLMS帧（完整协议栈解析）

    Args:
        hex_data: 十六进制帧数据
        encryption_key: 加密密钥（十六进制字符串，可选）
        system_title: 系统标题（十六进制字符串，可选，用于解密验证）

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

                key_bytes = hex_to_bytes(encryption_key) if encryption_key else None

                if key_bytes:
                    plaintext, cipher_frame = parse_ciphered(payload, key_bytes)
                    result.ciphering = cipher_frame

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
            result.apdu = apdu_obj.model_dump()
            log_manager.info(
                frame_id, "apdu",
                f"APDU解析成功: type={apdu_obj.type_name} (tag={apdu_obj.tag})"
            )

            # 提取数据项并匹配数据模型
            if hasattr(apdu_obj, 'items') and apdu_obj.items:
                for item in apdu_obj.items:
                    matched = data_model_manager.match_obis(
                        class_id=item.class_id,
                        obis_bytes=hex_to_bytes(item.obis) if item.obis else b'',
                        attribute_id=item.attribute_id,
                    )
                    if matched:
                        result.matched_objects.append(matched.model_dump())
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

    通过检查第一个字节（安全控制字节）来判断。
    加密APDU通常以 GeneralGloCiphering(219) 或类似标签开始。
    但如果是在加密层内部，第一个字节是Security Control。

    这里做一个启发式判断：
    - 如果第一个字节是常见的安全控制字节值，则认为是加密的
    """
    if not data:
        return False

    first_byte = data[0]

    # 常见的安全控制字节值:
    # 0x00 - 无加密无认证（少见）
    # 0x01 - 仅加密
    # 0x02 - 仅认证
    # 0x03 - 加密+认证
    # 0x05 - 加密+压缩
    # 0x07 - 加密+认证+压缩
    # 0x10 - 0x1F 不同key_id的组合

    # 检查是否像安全控制字节（低3位组合合理）
    # 如果是GeneralGloCiphering APDU，tag是219
    if first_byte == 219:  # GeneralGloCiphering
        return True

    # 如果直接是加密数据（从安全控制字节开始）
    # 安全控制字节的bit 5-7通常为0
    if (first_byte & 0xE0) == 0:  # 高3位为0
        # 且至少有加密或认证位
        if first_byte & 0x03:
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
) -> dict:
    """
    构建DLMS帧

    Args:
        apdu_type: APDU类型
        params: APDU参数
        src_wport: 源WPort
        dst_wport: 目的WPort
        encrypt: 是否加密
        encryption_key: 加密密钥（十六进制）
        system_title: 系统标题（十六进制）

    Returns:
        dict: {success, hex_data, frame_length, message}
    """
    try:
        # Step 1: 构建APDU
        apdu_data = build_apdu(apdu_type, params)

        # Step 2: 加密（可选）
        if encrypt:
            if not encryption_key or not system_title:
                return {
                    "success": False,
                    "hex_data": "",
                    "frame_length": 0,
                    "message": "加密需要提供密钥和系统标题",
                }
            key_bytes = hex_to_bytes(encryption_key)
            st_bytes = hex_to_bytes(system_title)
            # TODO: 调用加密层
            # apdu_data = build_ciphered(apdu_data, key_bytes, st_bytes, invocation_counter=1)
            return {
                "success": False,
                "hex_data": "",
                "frame_length": 0,
                "message": "加密组帧暂未完全实现",
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
