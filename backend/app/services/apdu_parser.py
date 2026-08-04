"""
APDU解析器 (Application Layer Protocol Data Unit)

DLMS/COSEM APDU 类型和标签:
- DataNotification: tag = 15 (0x0F)
- GetRequest: tag = 192 (0xC0)
- GetResponse: tag = 193 (0xC1)
- SetRequest: tag = 194 (0xC2)
- SetResponse: tag = 195 (0xC3)
- EventNotification: tag = 196 (0xC4)
- ActionRequest: tag = 199 (0xC7)
- ActionResponse: tag = 200 (0xC8)
- GeneralGloCiphering: tag = 219 (0xDB)
- GeneralCiphering: tag = 218 (0xDA)
"""
from typing import Optional, Any

from app.models.apdu import (
    APDUBase,
    DataNotificationAPDU,
    GetRequestAPDU,
    GetResponseAPDU,
    GeneralGloCipheringAPDU,
    UnknownAPDU,
    CosemDataItem,
    APDU_TYPES,
)
from app.utils.hex_utils import bytes_to_hex
from app.utils.obis_utils import obis_bytes_to_str
from app.utils.ber_encoder import decode_data, DATA_TYPES


class APDUParser:
    """APDU解析器"""

    @staticmethod
    def _parse_uint8(data: bytes, offset: int) -> tuple[int, int]:
        """解析uint8"""
        return data[offset], offset + 1

    @staticmethod
    def _parse_uint16(data: bytes, offset: int) -> tuple[int, int]:
        """解析uint16 (大端)"""
        val = int.from_bytes(data[offset:offset + 2], "big")
        return val, offset + 2

    @staticmethod
    def _parse_uint32(data: bytes, offset: int) -> tuple[int, int]:
        """解析uint32 (大端)"""
        val = int.from_bytes(data[offset:offset + 4], "big")
        return val, offset + 4

    @staticmethod
    def _parse_octet_string(data: bytes, offset: int, length: int) -> tuple[bytes, int]:
        """解析固定长度的octet-string"""
        val = data[offset:offset + length]
        return val, offset + length

    @staticmethod
    def _parse_variable_length(data: bytes, offset: int) -> tuple[int, int]:
        """
        解析可变长度字段（BER长度编码）
        长度字节最高位为1表示长格式
        """
        first = data[offset]
        offset += 1
        if first & 0x80:
            # 长格式
            num_bytes = first & 0x7F
            length = 0
            for _ in range(num_bytes):
                length = (length << 8) | data[offset]
                offset += 1
            return length, offset
        else:
            return first, offset

    @classmethod
    def _parse_cosem_attribute_descriptor(cls, data: bytes, offset: int) -> tuple[dict, int]:
        """
        解析COSEM属性描述符
        格式: class_id(2) + instance_id(6) + attribute_id(1)
        """
        if len(data) < offset + 9:
            raise ValueError("数据不足，无法解析COSEM属性描述符")

        class_id, offset = cls._parse_uint16(data, offset)
        obis_bytes, offset = cls._parse_octet_string(data, offset, 6)
        attribute_id, offset = cls._parse_uint8(data, offset)

        return {
            "class_id": class_id,
            "obis": obis_bytes_to_str(obis_bytes),
            "obis_bytes": obis_bytes,
            "attribute_id": attribute_id,
        }, offset

    @classmethod
    def parse_data_notification(cls, data: bytes) -> DataNotificationAPDU:
        """
        解析 DataNotification APDU (tag=15)

        格式:
        - tag (1 byte) = 15
        - long-invoke-id-and-priority (4 bytes): 调用ID
        - datetime (optional, 12 bytes): 日期时间
        - notification-body: 通知体（可变）

        notification-body 包含:
        - 数据项列表，每个项通常是一个结构(structure)
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 15:
            raise ValueError(f"不是DataNotification APDU，tag={tag}")

        # long-invoke-id-and-priority (4 bytes)
        invoke_id, offset = cls._parse_uint32(data, offset)

        # 检查是否有日期时间（如果有，接下来的tag是date-time类型）
        datetime_str = None
        items = []

        try:
            # 尝试解析date-time (tag=21是date-time)
            # 但DataNotification中datetime通常是可选的
            # 需要根据实际数据判断
            # 这里简化处理：如果下一个字节是21 (date-time)，则解析
            if offset < len(data) and data[offset] == 21:  # date-time tag
                dt_length, new_offset = cls._parse_variable_length(data, offset + 1)
                dt_data = data[offset + 1 + (new_offset - offset - 1):offset + 1 + (new_offset - offset - 1) + dt_length]
                datetime_str = bytes_to_hex(dt_data)
                offset = offset + 1 + (new_offset - offset - 1) + dt_length
        except Exception:
            pass

        # 解析notification body
        # 通常是一个array of structure
        notification_body_hex = bytes_to_hex(data[offset:])

        try:
            # 尝试解析数据项列表
            # notification body 通常是一个 array
            if offset < len(data):
                value, new_offset, type_name = decode_data(data, offset)
                if isinstance(value, list):
                    # 遍历数组，每个元素是一个数据项结构
                    for item in value:
                        if isinstance(item, list) and len(item) >= 3:
                            # 结构通常包含: class_id, obis, attribute_id, value
                            # 但格式可能不同，这里做简化处理
                            items.append(CosemDataItem(
                                class_id=0,
                                obis="",
                                attribute_id=0,
                                data_type="structure",
                                value=str(item),
                                raw_hex="",
                            ))
                offset = new_offset
        except Exception:
            # 解析失败，保留原始数据
            pass

        return DataNotificationAPDU(
            tag=tag,
            type_name="DataNotification",
            invoke_id=invoke_id,
            datetime=datetime_str,
            items=items,
            notification_body_hex=notification_body_hex,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_get_request(cls, data: bytes) -> GetRequestAPDU:
        """
        解析 GetRequest APDU (tag=192)

        格式:
        - tag (1 byte) = 192
        - get-type (1 byte): 1=normal, 2=next, 3=with-list
        - invoke-id-and-priority (4 bytes)
        - 根据get-type不同，后续内容不同
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 192:
            raise ValueError(f"不是GetRequest APDU，tag={tag}")

        get_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        class_id = None
        obis = None
        attribute_id = None

        try:
            if get_type == 1:  # Get-Request-Normal
                # COSEM attribute descriptor
                desc, offset = cls._parse_cosem_attribute_descriptor(data, offset)
                class_id = desc["class_id"]
                obis = desc["obis"]
                attribute_id = desc["attribute_id"]
                # 后面还有access-selection (可选)
        except Exception:
            pass

        return GetRequestAPDU(
            tag=tag,
            type_name="GetRequest",
            get_type=get_type,
            invoke_id=invoke_id,
            class_id=class_id,
            obis=obis,
            attribute_id=attribute_id,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_get_response(cls, data: bytes) -> GetResponseAPDU:
        """
        解析 GetResponse APDU (tag=193)
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 193:
            raise ValueError(f"不是GetResponse APDU，tag={tag}")

        get_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        result = "success"
        data_type = None
        value = None

        try:
            # 结果标签
            result_tag = data[offset]
            offset += 1

            if result_tag == 0:  # data
                # 解析数据
                val, new_offset, type_name = decode_data(data, offset)
                value = val if not isinstance(val, bytes) else bytes_to_hex(val)
                data_type = type_name
                offset = new_offset
            else:
                result = f"error({result_tag})"
        except Exception:
            result = "parse_error"

        return GetResponseAPDU(
            tag=tag,
            type_name="GetResponse",
            get_type=get_type,
            invoke_id=invoke_id,
            result=result,
            data_type=data_type,
            value=value,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_general_glo_ciphering(cls, data: bytes) -> GeneralGloCipheringAPDU:
        """
        解析 GeneralGloCiphering APDU (tag=219)

        这是全局加密的APDU，包含加密数据。
        实际解密在ciphering层完成。
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 219:
            raise ValueError(f"不是GeneralGloCiphering APDU，tag={tag}")

        system_title = ""
        ciphered_data = ""

        try:
            # system-title (8 bytes octet-string)
            st_length, offset = cls._parse_variable_length(data, offset)
            st_bytes = data[offset:offset + st_length]
            system_title = bytes_to_hex(st_bytes)
            offset += st_length

            # ciphered-service (octet-string)
            cs_length, offset = cls._parse_variable_length(data, offset)
            cs_bytes = data[offset:offset + cs_length]
            ciphered_data = bytes_to_hex(cs_bytes)
        except Exception:
            pass

        return GeneralGloCipheringAPDU(
            tag=tag,
            type_name="GeneralGloCiphering",
            system_title=system_title,
            ciphered_data=ciphered_data,
            raw_hex=bytes_to_hex(data),
        )


def parse_apdu(data: bytes) -> APDUBase:
    """
    解析APDU数据

    Args:
        data: APDU数据（第一个字节是tag）

    Returns:
        APDUBase: 解析后的APDU对象（具体类型由tag决定）

    Raises:
        ValueError: 解析失败
    """
    if not data:
        raise ValueError("APDU数据为空")

    tag = data[0]

    try:
        if tag == 15:  # DataNotification
            return APDUParser.parse_data_notification(data)
        elif tag == 192:  # GetRequest
            return APDUParser.parse_get_request(data)
        elif tag == 193:  # GetResponse
            return APDUParser.parse_get_response(data)
        elif tag == 219:  # GeneralGloCiphering
            return APDUParser.parse_general_glo_ciphering(data)
        else:
            # 未知/未实现的APDU类型
            return UnknownAPDU(
                tag=tag,
                type_name="Unknown",
                data_hex=bytes_to_hex(data),
                raw_hex=bytes_to_hex(data),
            )
    except Exception as e:
        # 解析失败，返回未知APDU
        return UnknownAPDU(
            tag=tag,
            type_name="Unknown",
            data_hex=bytes_to_hex(data),
            raw_hex=bytes_to_hex(data),
        )


def build_apdu(apdu_type: str, params: dict) -> bytes:
    """
    构建APDU

    Args:
        apdu_type: APDU类型名称
        params: APDU参数字典

    Returns:
        bytes: 构建的APDU数据

    Raises:
        NotImplementedError: 暂不支持的APDU类型
        ValueError: 参数错误
    """
    apdu_type = apdu_type.lower()

    if apdu_type == "getrequest" or apdu_type == "get-request":
        return _build_get_request(params)
    elif apdu_type == "datanotification" or apdu_type == "data-notification":
        raise NotImplementedError("DataNotification组帧暂未实现")
    elif apdu_type == "generalglociphering" or apdu_type == "general-glo-ciphering":
        raise NotImplementedError("GeneralGloCiphering组帧在ciphering层完成")
    else:
        raise NotImplementedError(f"暂不支持的APDU类型: {apdu_type}")


def _build_get_request(params: dict) -> bytes:
    """
    构建GetRequest APDU

    Args:
        params: 参数字典，包含:
            - get_type: 1/2/3 (默认1)
            - invoke_id: 调用ID (默认0)
            - class_id: 类ID
            - obis: OBIS码（字符串或字节）
            - attribute_id: 属性ID

    Returns:
        bytes: GetRequest APDU数据
    """
    from app.utils.hex_utils import hex_to_bytes
    from app.utils.obis_utils import obis_str_to_bytes

    get_type = params.get("get_type", 1)
    invoke_id = params.get("invoke_id", 0)
    class_id = params.get("class_id", 0)
    obis_str = params.get("obis", "0-0:0.0.0.0")
    attribute_id = params.get("attribute_id", 2)

    # tag
    result = bytes([192])  # GetRequest

    # get-type
    result += bytes([get_type])

    # invoke-id-and-priority (4 bytes)
    result += invoke_id.to_bytes(4, "big")

    if get_type == 1:  # normal
        # COSEM attribute descriptor
        result += class_id.to_bytes(2, "big")
        obis_bytes = obis_str_to_bytes(obis_str) if isinstance(obis_str, str) else obis_str
        result += obis_bytes
        result += bytes([attribute_id])

        # access-selection = 0 (无选择)
        result += bytes([0])

    return result
