"""
APDU解析器 (Application Layer Protocol Data Unit)

DLMS/COSEM APDU 类型和标签:
- DataNotification: tag = 0x0F (15)
- GetRequest: tag = 0xC0 (192)
- GetResponse: tag = 0xC1 (193)
- SetRequest: tag = 0xC2 (194)
- SetResponse: tag = 0xC3 (195)
- EventNotification: tag = 0xC4 (196)
- ActionRequest: tag = 0xC7 (199)
- ActionResponse: tag = 0xC8 (200)
- GeneralGloCiphering: tag = 0xDB (219)
- GeneralCiphering: tag = 0xDA (218)
"""
from typing import Optional, Any, List, Tuple

from app.models.apdu import (
    APDUBase,
    DataNotificationAPDU,
    DataNotificationConfirmAPDU,
    GetRequestAPDU,
    GetResponseAPDU,
    SetRequestAPDU,
    SetResponseAPDU,
    EventNotificationAPDU,
    ActionRequestAPDU,
    ActionResponseAPDU,
    GeneralGloCipheringAPDU,
    GeneralCipheringAPDU,
    UnknownAPDU,
    CosemDataItem,
    CosemAttributeDescriptor,
    APDU_TYPES,
)
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes
from app.utils.obis_utils import obis_bytes_to_str, obis_str_to_bytes
from app.utils.ber_encoder import decode_data, encode_data, DATA_TYPES


class APDUParser:
    """APDU解析器"""

    # ---------- 基础解析工具 ----------

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
    def _parse_int32(data: bytes, offset: int) -> tuple[int, int]:
        """解析int32 (大端)"""
        val = int.from_bytes(data[offset:offset + 4], "big", signed=True)
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
        格式: class_id(2) + instance_id/obis(6) + attribute_id(1) = 9字节
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

    # ---------- DataNotification 解析 ----------

    @classmethod
    def parse_data_notification(cls, data: bytes) -> DataNotificationAPDU:
        """
        解析 DataNotification APDU (tag=0x0F, 15)

        DLMS标准格式 (IEC 62056-53):
        DataNotification ::= SEQUENCE
        {
            long-invoke-id-and-priority  Long-Invoke-Id-And-Priority,
            date-time                    [0] IMPLICIT Date-Time OPTIONAL,
            notification-body            NotificationBody
        }

        NotificationBody ::= SEQUENCE OF DataNotification-Body
        DataNotification-Body ::= SEQUENCE
        {
            cosem-attribute-descriptor  CosemAttributeDescriptor,
            value                       Data
        }

        CosemAttributeDescriptor ::= SEQUENCE
        {
            class-id        ClassId,          (2 bytes)
            instance-id     InstanceId,       (6 bytes = OBIS)
            attribute-id    AttributeId       (1 byte)
        }

        Args:
            data: 完整的APDU数据（第一个字节是tag）

        Returns:
            DataNotificationAPDU: 解析后的DataNotification对象
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0x0F:
            raise ValueError(f"不是DataNotification APDU，tag={tag} (0x{tag:02X})")

        # long-invoke-id-and-priority (4 bytes)
        invoke_id, offset = cls._parse_uint32(data, offset)

        # 检查可选的date-time字段
        # date-time 在DataNotification中是 [0] IMPLICIT Date-Time OPTIONAL
        # 支持多种格式：
        # 1. 标准BER date-time (tag=0x19)
        # 2. context tag [0] constructed (0xA0) IMPLICIT Date-Time
        # 3. context tag [0] primitive (0x80) - octet-string 方式
        # 4. null-data (0x00) - date-time 为 null
        # 5. dont-care (0xFF) - date-time 不存在
        datetime_dict = None
        datetime_raw = None
        parse_warnings = []

        if offset < len(data):
            next_byte = data[offset]
            try:
                if next_byte == 0x19:  # date-time tag
                    dt_value, new_offset, _ = decode_data(data, offset)
                    datetime_dict = dt_value
                    datetime_raw = bytes_to_hex(data[offset:new_offset])
                    offset = new_offset
                elif next_byte == 0xA0:  # context tag [0] constructed
                    dt_length, dt_offset = cls._parse_variable_length(data, offset + 1)
                    from app.utils.ber_encoder import _decode_date_time
                    dt_bytes = data[dt_offset:dt_offset + dt_length]
                    datetime_dict = _decode_date_time(dt_bytes, dt_length)
                    datetime_raw = bytes_to_hex(data[offset:dt_offset + dt_length])
                    offset = dt_offset + dt_length
                elif next_byte == 0x80:  # context tag [0] primitive (octet-string方式)
                    dt_length, dt_offset = cls._parse_variable_length(data, offset + 1)
                    from app.utils.ber_encoder import _decode_date_time
                    dt_bytes = data[dt_offset:dt_offset + dt_length]
                    datetime_dict = _decode_date_time(dt_bytes, dt_length)
                    datetime_raw = bytes_to_hex(data[offset:dt_offset + dt_length])
                    offset = dt_offset + dt_length
                elif next_byte == 0x00:  # null-data - date-time 为 null
                    datetime_dict = None
                    datetime_raw = "00"
                    offset += 1
                    parse_warnings.append("date-time is null (0x00)")
                elif next_byte == 0xFF:  # dont-care - date-time 不存在
                    datetime_dict = None
                    datetime_raw = "FF"
                    offset += 1
                    parse_warnings.append("date-time is dont-care (0xFF)")
            except Exception as e:
                parse_warnings.append(f"date-time parse error: {str(e)}")

        # 记录notification-body的起始位置
        body_start = offset
        notification_body_hex = bytes_to_hex(data[offset:]) if offset < len(data) else ""

        # 解析notification-body (array of structure)
        items: List[CosemDataItem] = []

        if offset < len(data):
            try:
                items = cls._parse_notification_body(data, offset)
                # 计算body实际占用的字节（所有item的raw data）
            except Exception as e:
                # 解析失败，保留空items
                pass

        return DataNotificationAPDU(
            tag=tag,
            type_name="DataNotification",
            invoke_id=invoke_id,
            datetime=datetime_dict,
            datetime_raw=datetime_raw,
            items=items,
            item_count=len(items),
            notification_body_hex=notification_body_hex,
            raw_hex=bytes_to_hex(data),
            parse_warnings=parse_warnings if 'parse_warnings' in dir() else [],
        )

    @classmethod
    def _parse_notification_body(cls, data: bytes, offset: int) -> List[CosemDataItem]:
        """
        解析notification-body（多策略尝试）

        支持多种格式：
        1. 标准BER编码: array of structure { ber-descriptor, value }
        2. 外层structure + 内层array + 裸9字节描述符
        3. 扁平结构: 直接序列的 描述符+值
        4. OBIS搜索模式: 搜索所有 octet-string(6字节) 作为OBIS

        Args:
            data: 完整数据
            offset: notification-body 起始位置

        Returns:
            List[CosemDataItem]: 解析出的数据项列表
        """
        items: List[CosemDataItem] = []

        if offset >= len(data):
            return items

        # 策略1: 标准BER编码
        try:
            items_ber = cls._parse_notification_body_ber(data, offset)
            if items_ber and len(items_ber) > 0:
                return items_ber
        except Exception:
            pass

        # 策略2: 手动解析 - 裸9字节描述符
        try:
            items_raw = cls._parse_notification_body_raw(data, offset)
            if items_raw and len(items_raw) > 0:
                return items_raw
        except Exception:
            pass

        # 策略3: OBIS搜索模式 - 搜索所有 09 06 模式
        try:
            items_search = cls._parse_notification_body_search(data, offset)
            if items_search and len(items_search) > 0:
                return items_search
        except Exception:
            pass

        # 所有策略都失败，返回空列表
        return items

    @classmethod
    def _parse_notification_body_ber(cls, data: bytes, offset: int) -> List[CosemDataItem]:
        """策略1: 标准BER编码解析"""
        items: List[CosemDataItem] = []

        # 处理外层（可能是 array 或 structure）
        start_offset = offset
        tag = data[offset]

        if tag in (0x01, 0x02):  # array 或 structure
            from app.utils.ber_encoder import _decode_length
            outer_len, outer_start = _decode_length(data, offset + 1)
            outer_end = outer_start + outer_len

            # 如果外层是 structure，内部可能是 array
            if tag == 0x02 and outer_start < outer_end and data[outer_start] == 0x01:
                inner_len, inner_start = _decode_length(data, outer_start + 1)
                inner_end = inner_start + inner_len
                array_start = inner_start
                array_end = inner_end
            else:
                array_start = outer_start
                array_end = outer_end

            # 遍历 array 元素
            pos = array_start
            while pos < array_end:
                if pos >= len(data):
                    break

                if data[pos] == 0x02:  # structure = DataNotification-Body
                    struct_len, struct_start = _decode_length(data, pos + 1)
                    struct_end = struct_start + struct_len

                    if struct_end > len(data):
                        break

                    # 解析 structure 内部
                    item = cls._parse_single_body_ber(data, struct_start, struct_end)
                    if item:
                        items.append(item)

                    pos = struct_end
                else:
                    # 尝试直接 BER 解码
                    try:
                        _, new_pos, _ = decode_data(data, pos)
                        pos = new_pos
                    except:
                        pos += 1
        else:
            # 直接是值？尝试解码
            try:
                _, _, _ = decode_data(data, offset)
            except:
                pass

        return items

    @classmethod
    def _parse_single_body_ber(cls, data: bytes, start: int, end: int) -> Optional[CosemDataItem]:
        """解析单个 DataNotification-Body (BER 格式)"""
        pos = start
        desc = None
        value = None
        value_type = ""

        # 第一个元素: descriptor
        if pos < end:
            if data[pos] == 0x02:  # BER-encoded descriptor structure
                from app.utils.ber_encoder import _decode_length
                desc_len, desc_start = _decode_length(data, pos + 1)
                desc_end = desc_start + desc_len
                desc = cls._parse_ber_descriptor(data, desc_start, desc_end)
                pos = desc_end
            elif data[pos] == 0x09:  # octet-string descriptor (9字节)
                from app.utils.ber_encoder import _decode_length
                os_len, os_start = _decode_length(data, pos + 1)
                os_end = os_start + os_len
                if os_len == 9:
                    desc_bytes = data[os_start:os_end]
                    desc = {
                        "class_id": int.from_bytes(desc_bytes[0:2], "big"),
                        "obis": obis_bytes_to_str(desc_bytes[2:8]),
                        "obis_bytes": desc_bytes[2:8],
                        "attribute_id": desc_bytes[8],
                    }
                pos = os_end
            else:
                # 尝试解码并跳过
                try:
                    _, new_pos, _ = decode_data(data, pos)
                    pos = new_pos
                except:
                    pos += 1

        # 第二个元素: value
        if pos < end:
            try:
                value, val_end, value_type = decode_data(data, pos)
            except:
                value = data[pos:end].hex()
                value_type = "raw"

        if desc:
            return CosemDataItem(
                class_id=desc["class_id"],
                obis=desc["obis"],
                obis_bytes=desc["obis_bytes"],
                attribute_id=desc["attribute_id"],
                data_type=value_type,
                type=value_type,  # 兼容前端
                value=value,
                raw_hex=data[start:end].hex(),
            )
        return None

    @classmethod
    def _parse_ber_descriptor(cls, data: bytes, start: int, end: int) -> Optional[dict]:
        """解析 BER-encoded 的描述符 structure"""
        class_id = 0
        obis_bytes = b""
        attribute_id = 0
        pos = start
        field_idx = 0

        while pos < end and field_idx < 3:
            tag = data[pos]

            if tag == 0x12:  # long-unsigned = class_id
                from app.utils.ber_encoder import _decode_length
                val_len, val_start = _decode_length(data, pos + 1)
                class_id = int.from_bytes(data[val_start:val_start + val_len], "big")
                pos = val_start + val_len
                field_idx += 1
            elif tag == 0x09:  # octet-string = obis
                from app.utils.ber_encoder import _decode_length
                val_len, val_start = _decode_length(data, pos + 1)
                obis_bytes = data[val_start:val_start + val_len]
                pos = val_start + val_len
                field_idx += 1
            elif tag == 0x0F:  # integer = attribute_id
                from app.utils.ber_encoder import _decode_length
                val_len, val_start = _decode_length(data, pos + 1)
                attribute_id = int.from_bytes(
                    data[val_start:val_start + val_len], "big", signed=True
                )
                pos = val_start + val_len
                field_idx += 1
            else:
                # 未知 tag，尝试解码跳过
                try:
                    _, new_pos, _ = decode_data(data, pos)
                    pos = new_pos
                except:
                    pos += 1

        if len(obis_bytes) == 6:
            return {
                "class_id": class_id,
                "obis": obis_bytes_to_str(obis_bytes),
                "obis_bytes": obis_bytes,
                "attribute_id": attribute_id,
            }
        return None

    @classmethod
    def _parse_notification_body_raw(cls, data: bytes, offset: int) -> List[CosemDataItem]:
        """策略2: 裸9字节描述符 + BER值"""
        items: List[CosemDataItem] = []
        from app.utils.ber_encoder import _decode_length

        pos = offset
        end = len(data)

        # 跳过外层 structure/array
        if pos < end and data[pos] == 0x02:
            outer_len, outer_start = _decode_length(data, pos + 1)
            outer_end = outer_start + outer_len
            if outer_end <= len(data):
                if outer_start < outer_end and data[outer_start] == 0x01:
                    inner_len, inner_start = _decode_length(data, outer_start + 1)
                    inner_end = inner_start + inner_len
                    parse_start = inner_start
                    parse_end = inner_end
                else:
                    parse_start = outer_start
                    parse_end = outer_end
            else:
                parse_start = pos
                parse_end = end
        elif pos < end and data[pos] == 0x01:
            outer_len, outer_start = _decode_length(data, pos + 1)
            parse_start = outer_start
            parse_end = outer_start + outer_len
        else:
            parse_start = pos
            parse_end = end

        # 在解析范围内查找条目
        pos = parse_start
        while pos + 9 < parse_end:
            # 检查当前位置是不是 structure tag
            if data[pos] == 0x02:
                struct_len, struct_start = _decode_length(data, pos + 1)
                struct_end = struct_start + struct_len

                if struct_end > parse_end or struct_end > len(data):
                    break

                # 尝试裸9字节描述符
                if struct_start + 9 <= struct_end:
                    class_id = int.from_bytes(data[struct_start:struct_start+2], "big")
                    obis_bytes = data[struct_start+2:struct_start+8]
                    attr_id = data[struct_start+8]

                    # 合理性检查
                    if 1 <= class_id <= 500 and 1 <= attr_id <= 100:
                        val_pos = struct_start + 9
                        value = None
                        value_type = ""
                        try:
                            value, val_end, value_type = decode_data(data, val_pos)
                        except:
                            value = data[val_pos:struct_end].hex()
                            value_type = "raw"

                        obis_str = obis_bytes_to_str(obis_bytes)
                        items.append(CosemDataItem(
                            class_id=class_id,
                            obis=obis_str,
                            obis_bytes=obis_bytes,
                            attribute_id=attr_id,
                            data_type=value_type,
                            type=value_type,
                            value=value,
                            raw_hex=data[pos:struct_end].hex(),
                        ))

                pos = struct_end
            else:
                pos += 1

        return items

    @classmethod
    def _parse_notification_body_search(cls, data: bytes, offset: int) -> List[CosemDataItem]:
        """策略3: 搜索所有 OBIS (09 06) 模式，向前向后推断描述符
        
        DLMS 紧凑 BER 描述符结构（13字节）:
        - long-unsigned (tag=0x12 + 2字节值) = class_id (3字节)
        - octet-string (tag=0x09 + length + 6字节值) = OBIS (8字节)
        - integer (tag=0x0F + 1字节值) = attribute_id (2字节)
        """
        items: List[CosemDataItem] = []

        # 搜索所有 09 06 模式（OBIS 的 tag+length）
        pos = offset
        while pos < len(data) - 8:
            if data[pos] == 0x09 and data[pos+1] == 0x06:
                obis_bytes = data[pos+2:pos+8]
                obis_str = obis_bytes_to_str(obis_bytes)

                # 向前找 class_id
                # long-unsigned (tag=0x12) 在 OBIS tag 前 3 字节
                # class_id 值是 tag 后面的 2 字节
                class_id = 0
                if pos >= 3 and data[pos-3] == 0x12:
                    class_id = int.from_bytes(data[pos-2:pos], "big")
                elif pos >= 2:
                    # 回退：直接取前 2 字节
                    class_id = int.from_bytes(data[pos-2:pos], "big")

                # 向后找 attribute_id
                # integer (tag=0x0F) 在 OBIS 值结束后
                # attribute_id 值是 tag 后面的 1 字节（有符号）
                attr_id = 0
                obis_end = pos + 8  # OBIS TLV 结束位置
                if obis_end < len(data) and data[obis_end] == 0x0F:
                    # integer tag 后面的 1 字节是值（有符号）
                    if obis_end + 1 < len(data):
                        attr_raw = data[obis_end + 1]
                        # 转换为有符号 8 位整数
                        attr_id = attr_raw if attr_raw < 128 else attr_raw - 256
                elif obis_end < len(data):
                    # 回退：直接取 OBIS 后面的字节
                    attr_id = data[obis_end]

                # 向后找值（attribute_id 之后）
                value = None
                value_type = ""
                val_start = obis_end + 2  # 跳过 integer tag + value
                if val_start < len(data):
                    try:
                        value, val_end, value_type = decode_data(data, val_start)
                    except:
                        pass

                # 合理性检查
                if 1 <= class_id <= 500 and 1 <= attr_id <= 50 and len(obis_bytes) == 6:
                    items.append(CosemDataItem(
                        class_id=class_id,
                        obis=obis_str,
                        obis_bytes=obis_bytes,
                        attribute_id=attr_id,
                        data_type=value_type,
                        type=value_type,
                        value=value,
                        raw_hex="",
                    ))

            pos += 1

        return items

    # ---------- GetRequest 解析 ----------

    @classmethod
    def parse_get_request(cls, data: bytes) -> GetRequestAPDU:
        """
        解析 GetRequest APDU (tag=0xC0, 192)

        Get-Request-Normal (type=1):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            cosem-attribute-descriptor  CosemAttributeDescriptor,
            access-selection        AccessSelection OPTIONAL
        }

        Get-Request-Next (type=2):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            datablock               DataBlock-G
        }

        Get-Request-With-List (type=3):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            cosem-attribute-descriptor-list  SEQUENCE OF CosemAttributeDescriptor,
            access-selection-list   SEQUENCE OF AccessSelection OPTIONAL
        }
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC0:
            raise ValueError(f"不是GetRequest APDU，tag={tag}")

        get_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        class_id = None
        obis = None
        attribute_id = None
        attribute_list: List[CosemAttributeDescriptor] = []
        access_selection = 0
        block_number = None

        if get_type == 1:  # Get-Request-Normal
            # COSEM attribute descriptor
            desc, offset = cls._parse_cosem_attribute_descriptor(data, offset)
            class_id = desc["class_id"]
            obis = desc["obis"]
            attribute_id = desc["attribute_id"]
            # access-selection (可选，通常1字节，0表示无)
            if offset < len(data):
                access_selection = data[offset]
                offset += 1

        elif get_type == 2:  # Get-Request-Next (datablock)
            # DataBlock-G = {block-number uint32, raw-data octet-string}
            block_number, offset = cls._parse_uint32(data, offset)
            # 后面还有数据块内容

        elif get_type == 3:  # Get-Request-With-List
            # 读取 attribute descriptor list
            # 格式: length(1 byte) + 多个 attribute descriptor (9 bytes each)
            if offset < len(data):
                list_len = data[offset]
                offset += 1
                for _ in range(list_len):
                    if offset + 9 > len(data):
                        break
                    desc, offset = cls._parse_cosem_attribute_descriptor(data, offset)
                    attribute_list.append(CosemAttributeDescriptor(**desc))

        return GetRequestAPDU(
            tag=tag,
            type_name="GetRequest",
            get_type=get_type,
            invoke_id=invoke_id,
            class_id=class_id,
            obis=obis,
            attribute_id=attribute_id,
            attribute_list=attribute_list,
            access_selection=access_selection,
            block_number=block_number,
            raw_hex=bytes_to_hex(data),
        )

    # ---------- GetResponse 解析 ----------

    @classmethod
    def parse_get_response(cls, data: bytes) -> GetResponseAPDU:
        """
        解析 GetResponse APDU (tag=0xC1, 193)

        Get-Response-Normal (type=1):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            result                  CHOICE
            {
                data                Data,
                datablock           DataBlock-G-A,
                [other]             DataAccessError
            }
        }

        Get-Response-Next (type=2):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            result                  CHOICE
            {
                datablock           DataBlock-G-A,
                [other]             DataAccessError
            }
        }

        Get-Response-With-List (type=3):
        {
            invoke-id-and-priority  Invoke-Id-And-Priority,
            result                  SEQUENCE OF CHOICE
            {
                data                Data,
                [other]             DataAccessError
            }
        }

        Result CHOICE tags (in Get-Response):
        - 0: data
        - 1: datablock
        - 2-250: DataAccessError (various)
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC1:
            raise ValueError(f"不是GetResponse APDU，tag={tag}")

        get_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        result_desc = "success"
        result_code = 0
        data_type = None
        value = None
        results: List[dict] = []
        is_block = False
        block_number = None
        last_block = False
        raw_data_hex = ""

        try:
            if get_type == 1:  # Get-Response-Normal
                # 解析单个result (CHOICE)
                result_tag = data[offset]
                offset += 1
                result_code = result_tag

                if result_tag == 0:  # data
                    val, new_offset, type_name = decode_data(data, offset)
                    data_type = type_name
                    value = val
                    raw_data_hex = bytes_to_hex(data[offset:new_offset])
                    offset = new_offset
                    result_desc = "success"

                elif result_tag == 1:  # datablock (DataBlock-G-A)
                    is_block = True
                    # DataBlock-G-A:
                    # last-block (1 byte, boolean)
                    # block-number (4 bytes, uint32)
                    # raw-data (octet-string)
                    last_block = data[offset] != 0
                    offset += 1
                    block_number, offset = cls._parse_uint32(data, offset)
                    # raw-data (octet-string with BER length)
                    rd_len, rd_offset = cls._parse_variable_length(data, offset)
                    raw_data_hex = bytes_to_hex(data[rd_offset:rd_offset + rd_len])
                    value = data[rd_offset:rd_offset + rd_len]
                    offset = rd_offset + rd_len
                    result_desc = "datablock"

                else:
                    # DataAccessError
                    result_desc = f"error({result_tag})"
                    value = None

            elif get_type == 2:  # Get-Response-Next
                result_tag = data[offset]
                offset += 1
                result_code = result_tag

                if result_tag == 1:  # datablock
                    is_block = True
                    last_block = data[offset] != 0
                    offset += 1
                    block_number, offset = cls._parse_uint32(data, offset)
                    rd_len, rd_offset = cls._parse_variable_length(data, offset)
                    raw_data_hex = bytes_to_hex(data[rd_offset:rd_offset + rd_len])
                    value = data[rd_offset:rd_offset + rd_len]
                    offset = rd_offset + rd_len
                    result_desc = "datablock"
                else:
                    result_desc = f"error({result_tag})"

            elif get_type == 3:  # Get-Response-With-List
                # 结果列表
                # 格式: length(1 byte) + 多个 result CHOICE
                list_len = data[offset]
                offset += 1

                for i in range(list_len):
                    if offset >= len(data):
                        break
                    item_result_tag = data[offset]
                    offset += 1

                    if item_result_tag == 0:  # data
                        val, new_offset, type_name = decode_data(data, offset)
                        results.append({
                            "index": i,
                            "success": True,
                            "data_type": type_name,
                            "value": val,
                            "result_code": 0,
                        })
                        offset = new_offset
                    else:
                        results.append({
                            "index": i,
                            "success": False,
                            "data_type": None,
                            "value": None,
                            "result_code": item_result_tag,
                            "error": f"error({item_result_tag})",
                        })

                result_desc = "with-list"
                if results:
                    success_count = sum(1 for r in results if r["success"])
                    result_desc = f"with-list({success_count}/{len(results)} success)"

        except Exception as e:
            result_desc = f"parse_error: {str(e)}"
            raw_data_hex = bytes_to_hex(data[offset:]) if offset < len(data) else ""

        return GetResponseAPDU(
            tag=tag,
            type_name="GetResponse",
            get_type=get_type,
            invoke_id=invoke_id,
            result=result_desc,
            result_code=result_code,
            data_type=data_type,
            value=value,
            results=results,
            is_block=is_block,
            block_number=block_number,
            last_block=last_block,
            raw_data_hex=raw_data_hex,
            raw_hex=bytes_to_hex(data),
        )

    # ---------- SetRequest/Response 解析 (简化) ----------

    @classmethod
    def parse_set_request(cls, data: bytes) -> SetRequestAPDU:
        """解析SetRequest APDU (tag=0xC2)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC2:
            raise ValueError(f"不是SetRequest APDU，tag={tag}")

        set_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        class_id = None
        obis = None
        attribute_id = None

        if set_type == 1 and offset + 9 <= len(data):
            desc, offset = cls._parse_cosem_attribute_descriptor(data, offset)
            class_id = desc["class_id"]
            obis = desc["obis"]
            attribute_id = desc["attribute_id"]

        return SetRequestAPDU(
            tag=tag,
            type_name="SetRequest",
            set_type=set_type,
            invoke_id=invoke_id,
            class_id=class_id,
            obis=obis,
            attribute_id=attribute_id,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_set_response(cls, data: bytes) -> SetResponseAPDU:
        """解析SetResponse APDU (tag=0xC3)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC3:
            raise ValueError(f"不是SetResponse APDU，tag={tag}")

        set_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        result_code = 0
        result_desc = "success"
        if offset < len(data):
            result_code = data[offset]
            if result_code != 0:
                result_desc = f"error({result_code})"

        return SetResponseAPDU(
            tag=tag,
            type_name="SetResponse",
            set_type=set_type,
            invoke_id=invoke_id,
            result=result_desc,
            result_code=result_code,
            raw_hex=bytes_to_hex(data),
        )

    # ---------- EventNotification 解析 ----------

    @classmethod
    def parse_event_notification(cls, data: bytes) -> EventNotificationAPDU:
        """解析EventNotification APDU (tag=0xC4)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC4:
            raise ValueError(f"不是EventNotification APDU，tag={tag}")

        datetime_dict = None
        class_id = None
        obis = None
        attribute_id = None
        data_type = None
        value = None

        try:
            # 检查可选的time字段（date-time）
            if offset < len(data) and data[offset] == 0x19:
                dt_val, new_offset, _ = decode_data(data, offset)
                datetime_dict = dt_val
                offset = new_offset

            # COSEM attribute descriptor
            if offset + 9 <= len(data):
                desc, offset = cls._parse_cosem_attribute_descriptor(data, offset)
                class_id = desc["class_id"]
                obis = desc["obis"]
                attribute_id = desc["attribute_id"]

            # value (Data)
            if offset < len(data):
                val, new_offset, type_name = decode_data(data, offset)
                data_type = type_name
                value = val

        except Exception:
            pass

        return EventNotificationAPDU(
            tag=tag,
            type_name="EventNotification",
            datetime=datetime_dict,
            class_id=class_id,
            obis=obis,
            attribute_id=attribute_id,
            data_type=data_type,
            value=value,
            raw_hex=bytes_to_hex(data),
        )

    # ---------- ActionRequest/Response 解析 (简化) ----------

    @classmethod
    def parse_action_request(cls, data: bytes) -> ActionRequestAPDU:
        """解析ActionRequest APDU (tag=0xC7)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC7:
            raise ValueError(f"不是ActionRequest APDU，tag={tag}")

        action_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        class_id = None
        obis = None
        method_id = None

        if action_type == 1 and offset + 9 <= len(data):
            # Action-Request-Normal: method_descriptor + method_invocation_parameters
            class_id, offset = cls._parse_uint16(data, offset)
            obis_bytes, offset = cls._parse_octet_string(data, offset, 6)
            obis = obis_bytes_to_str(obis_bytes)
            method_id, offset = cls._parse_uint8(data, offset)

        return ActionRequestAPDU(
            tag=tag,
            type_name="ActionRequest",
            action_type=action_type,
            invoke_id=invoke_id,
            class_id=class_id,
            obis=obis,
            method_id=method_id,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_action_response(cls, data: bytes) -> ActionResponseAPDU:
        """解析ActionResponse APDU (tag=0xC8)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xC8:
            raise ValueError(f"不是ActionResponse APDU，tag={tag}")

        action_type = data[offset]
        offset += 1

        invoke_id, offset = cls._parse_uint32(data, offset)

        result_desc = "success"
        result_code = 0
        data_type = None
        value = None

        if offset < len(data):
            result_code = data[offset]
            offset += 1
            if result_code == 0:
                # action-result (Data)
                if offset < len(data):
                    val, new_offset, type_name = decode_data(data, offset)
                    data_type = type_name
                    value = val
            else:
                result_desc = f"error({result_code})"

        return ActionResponseAPDU(
            tag=tag,
            type_name="ActionResponse",
            action_type=action_type,
            invoke_id=invoke_id,
            result=result_desc,
            result_code=result_code,
            data_type=data_type,
            value=value,
            raw_hex=bytes_to_hex(data),
        )

    # ---------- 加密APDU解析 ----------

    @classmethod
    def parse_general_glo_ciphering(cls, data: bytes) -> GeneralGloCipheringAPDU:
        """
        解析 GeneralGloCiphering APDU (tag=0xDB, 219)

        格式:
        - tag (1 byte) = 0xDB
        - system-title (octet-string, 8 bytes, with BER length)
        - data (octet-string, with BER length)
          data 内包含:
            - security-control-byte (1 byte)
            - invocation-counter (4 bytes)
            - ciphered-service (encrypted APDU)
        """
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xDB:
            raise ValueError(f"不是GeneralGloCiphering APDU，tag={tag}")

        system_title = ""
        system_title_bytes = b""
        ciphered_data = ""
        ciphered_data_bytes = b""
        ciphered_service_len = None

        try:
            # system-title (octet-string)
            st_length, offset = cls._parse_variable_length(data, offset)
            st_bytes = data[offset:offset + st_length]
            system_title = bytes_to_hex(st_bytes)
            system_title_bytes = st_bytes
            offset += st_length

            # ciphered-service (octet-string)
            cs_length, cs_offset = cls._parse_variable_length(data, offset)
            cs_bytes = data[cs_offset:cs_offset + cs_length]
            ciphered_data = bytes_to_hex(cs_bytes)
            ciphered_data_bytes = cs_bytes
            ciphered_service_len = cs_length
        except Exception:
            pass

        return GeneralGloCipheringAPDU(
            tag=tag,
            type_name="GeneralGloCiphering",
            system_title=system_title,
            system_title_bytes=system_title_bytes,
            ciphered_data=ciphered_data,
            ciphered_data_bytes=ciphered_data_bytes,
            ciphered_service_len=ciphered_service_len,
            raw_hex=bytes_to_hex(data),
        )

    @classmethod
    def parse_general_ciphering(cls, data: bytes) -> GeneralCipheringAPDU:
        """解析GeneralCiphering APDU (tag=0xDA)"""
        offset = 0
        tag = data[offset]
        offset += 1

        if tag != 0xDA:
            raise ValueError(f"不是GeneralCiphering APDU，tag={tag}")

        system_title = ""
        ciphered_data = ""

        try:
            st_length, offset = cls._parse_variable_length(data, offset)
            st_bytes = data[offset:offset + st_length]
            system_title = bytes_to_hex(st_bytes)
            offset += st_length

            cs_length, cs_offset = cls._parse_variable_length(data, offset)
            cs_bytes = data[cs_offset:cs_offset + cs_length]
            ciphered_data = bytes_to_hex(cs_bytes)
        except Exception:
            pass

        return GeneralCipheringAPDU(
            tag=tag,
            type_name="GeneralCiphering",
            system_title=system_title,
            ciphered_data=ciphered_data,
            raw_hex=bytes_to_hex(data),
        )


# ---------- 顶层解析入口 ----------

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
        if tag == 0x0F:  # DataNotification
            return APDUParser.parse_data_notification(data)
        elif tag == 0xC0:  # GetRequest
            return APDUParser.parse_get_request(data)
        elif tag == 0xC1:  # GetResponse
            return APDUParser.parse_get_response(data)
        elif tag == 0xC2:  # SetRequest
            return APDUParser.parse_set_request(data)
        elif tag == 0xC3:  # SetResponse
            return APDUParser.parse_set_response(data)
        elif tag == 0xC4:  # EventNotification
            return APDUParser.parse_event_notification(data)
        elif tag == 0xC7:  # ActionRequest
            return APDUParser.parse_action_request(data)
        elif tag == 0xC8:  # ActionResponse
            return APDUParser.parse_action_response(data)
        elif tag == 0xDA:  # GeneralCiphering
            return APDUParser.parse_general_ciphering(data)
        elif tag == 0xDB:  # GeneralGloCiphering
            return APDUParser.parse_general_glo_ciphering(data)
        else:
            # 未知/未实现的APDU类型
            return UnknownAPDU(
                tag=tag,
                type_name=f"Unknown(0x{tag:02X})",
                data_hex=bytes_to_hex(data),
                raw_hex=bytes_to_hex(data),
            )
    except Exception as e:
        # 解析失败，返回未知APDU
        return UnknownAPDU(
            tag=tag,
            type_name=f"Unknown(0x{tag:02X})",
            data_hex=bytes_to_hex(data),
            raw_hex=bytes_to_hex(data),
        )


# ---------- APDU构建函数 ----------

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
    apdu_type = apdu_type.lower().replace("_", "-").replace(" ", "")

    if apdu_type in ("getrequest", "get-request"):
        return build_get_request(params)
    elif apdu_type in ("getresponse", "get-response"):
        return build_get_response(params)
    elif apdu_type in ("datanotification", "data-notification"):
        return build_data_notification(params)
    elif apdu_type in ("datanotificationconfirm", "data-notification-confirm",
                        "dataconfirm", "data-confirm", "confirm"):
        return build_data_notification_confirm(params)
    elif apdu_type in ("setrequest", "set-request"):
        return build_set_request(params)
    elif apdu_type in ("generalglociphering", "general-glo-ciphering"):
        raise NotImplementedError("GeneralGloCiphering组帧在ciphering层完成")
    else:
        raise NotImplementedError(f"暂不支持的APDU类型: {apdu_type}")


# ---------- GetRequest 构建 ----------

def build_get_request(params: dict) -> bytes:
    """
    构建GetRequest APDU

    Args:
        params: 参数字典:
            - get_type: 1/2/3 (默认1)
            - invoke_id: 调用ID (默认0)
            - class_id: 类ID (type=1时)
            - obis: OBIS码（字符串或字节）(type=1时)
            - attribute_id: 属性ID (type=1时)
            - attribute_list: 属性列表 (type=3时)
              [{"class_id": ..., "obis": ..., "attribute_id": ...}, ...]
            - access_selection: 访问选择 (默认0)
            - block_number: 块号 (type=2时)

    Returns:
        bytes: GetRequest APDU数据
    """
    get_type = params.get("get_type", 1)
    invoke_id = params.get("invoke_id", 0)

    # tag
    result = bytes([0xC0])  # GetRequest

    # get-type
    result += bytes([get_type])

    # invoke-id-and-priority (4 bytes)
    result += invoke_id.to_bytes(4, "big")

    if get_type == 1:  # normal
        # COSEM attribute descriptor
        class_id = params.get("class_id", 0)
        obis_str = params.get("obis", "0-0:0.0.0.0")
        attribute_id = params.get("attribute_id", 2)
        access_selection = params.get("access_selection", 0)

        result += class_id.to_bytes(2, "big")
        if isinstance(obis_str, (bytes, bytearray)):
            obis_bytes = bytes(obis_str)
        else:
            obis_bytes = obis_str_to_bytes(obis_str)
        if len(obis_bytes) != 6:
            raise ValueError(f"OBIS码必须为6字节，当前: {len(obis_bytes)}")
        result += obis_bytes
        result += bytes([attribute_id])

        # access-selection
        result += bytes([access_selection])

    elif get_type == 2:  # next (with datablock)
        # DataBlock-G: block-number + raw-data
        block_number = params.get("block_number", 0)
        result += block_number.to_bytes(4, "big")
        # 这里简化，不包含raw-data
        # 实际使用时可能需要补充raw-data字段

    elif get_type == 3:  # with-list
        # attribute-descriptor-list
        attribute_list = params.get("attribute_list", [])
        if not attribute_list:
            raise ValueError("get_type=3需要提供attribute_list")

        # 列表长度 (1 byte)
        list_len = len(attribute_list)
        if list_len > 255:
            raise ValueError(f"attribute_list长度不能超过255，当前: {list_len}")
        result += bytes([list_len])

        # 每个attribute descriptor
        for attr in attribute_list:
            if isinstance(attr, dict):
                cid = attr.get("class_id", 0)
                obis_val = attr.get("obis", "0-0:0.0.0.0")
                aid = attr.get("attribute_id", 2)
            elif isinstance(attr, (list, tuple)) and len(attr) >= 3:
                cid, obis_val, aid = attr[0], attr[1], attr[2]
            else:
                raise ValueError(f"无效的attribute描述符: {attr}")

            result += cid.to_bytes(2, "big")
            if isinstance(obis_val, (bytes, bytearray)):
                obis_bytes = bytes(obis_val)
            else:
                obis_bytes = obis_str_to_bytes(obis_val)
            result += obis_bytes
            result += bytes([aid])

        # access-selection-list (简化: 0 = no access selection)
        result += bytes([0])

    else:
        raise ValueError(f"不支持的get_type: {get_type}")

    return result


# ---------- GetResponse 构建 ----------

def build_get_response(params: dict) -> bytes:
    """
    构建GetResponse APDU

    Args:
        params: 参数字典:
            - get_type: 1/2/3 (默认1)
            - invoke_id: 调用ID (默认0)
            - result_code: 结果码 (默认0=data, 1=datablock, 其他=error)
            - value: 返回值 (result_code=0时)
            - data_type: 数据类型名称 (result_code=0时，用于编码value)
            - is_block: 是否为数据块 (默认False)
            - last_block: 是否为最后一块 (默认False)
            - block_number: 块号
            - raw_data: 块数据（字节）
            - results: 结果列表 (get_type=3时)
              [{"success": bool, "value": ..., "data_type": ..., "result_code": ...}, ...]

    Returns:
        bytes: GetResponse APDU数据
    """
    get_type = params.get("get_type", 1)
    invoke_id = params.get("invoke_id", 0)

    # tag
    result = bytes([0xC1])  # GetResponse

    # get-type
    result += bytes([get_type])

    # invoke-id-and-priority (4 bytes)
    result += invoke_id.to_bytes(4, "big")

    if get_type == 1:  # normal
        result_code = params.get("result_code", 0)
        result += bytes([result_code])

        if result_code == 0:  # data
            value = params.get("value")
            data_type = params.get("data_type")
            if data_type:
                result += encode_data(value, data_type)
            elif value is not None:
                result += encode_data(value)  # 自动推断
            else:
                result += encode_data(None, "null-data")

        elif result_code == 1:  # datablock
            last_block = params.get("last_block", False)
            block_number = params.get("block_number", 0)
            raw_data = params.get("raw_data", b"")

            result += bytes([1 if last_block else 0])
            result += block_number.to_bytes(4, "big")
            # raw-data (octet-string)
            rd_len = len(raw_data)
            from app.utils.ber_encoder import _encode_length
            result += _encode_length(rd_len)
            result += raw_data

        # else: error, 不需要额外数据

    elif get_type == 2:  # next (datablock)
        result_code = params.get("result_code", 1)  # 默认datablock
        result += bytes([result_code])

        if result_code == 1:  # datablock
            last_block = params.get("last_block", False)
            block_number = params.get("block_number", 0)
            raw_data = params.get("raw_data", b"")

            result += bytes([1 if last_block else 0])
            result += block_number.to_bytes(4, "big")
            from app.utils.ber_encoder import _encode_length
            result += _encode_length(len(raw_data))
            result += raw_data

    elif get_type == 3:  # with-list
        results = params.get("results", [])
        if not results:
            raise ValueError("get_type=3需要提供results")

        list_len = len(results)
        if list_len > 255:
            raise ValueError(f"results长度不能超过255，当前: {list_len}")
        result += bytes([list_len])

        for item in results:
            if isinstance(item, dict):
                success = item.get("success", True)
                item_result_code = item.get("result_code", 0 if success else 2)
                item_value = item.get("value")
                item_data_type = item.get("data_type")
            else:
                # 简单值，默认成功
                item_result_code = 0
                item_value = item
                item_data_type = None

            result += bytes([item_result_code])
            if item_result_code == 0:
                if item_data_type:
                    result += encode_data(item_value, item_data_type)
                else:
                    result += encode_data(item_value)

    else:
        raise ValueError(f"不支持的get_type: {get_type}")

    return result


# ---------- DataNotification 构建 ----------

def build_data_notification(params: dict) -> bytes:
    """
    构建DataNotification APDU

    Args:
        params: 参数字典:
            - invoke_id: 调用ID (默认0)
            - datetime: 可选，日期时间dict或bytes
            - items: 数据项列表
              [{"class_id": ..., "obis": ..., "attribute_id": ...,
                "value": ..., "data_type": ...}, ...]

    Returns:
        bytes: DataNotification APDU数据
    """
    invoke_id = params.get("invoke_id", 0)

    # tag
    result = bytes([0x0F])  # DataNotification

    # long-invoke-id-and-priority (4 bytes)
    result += invoke_id.to_bytes(4, "big")

    # 可选的date-time
    dt = params.get("datetime")
    if dt is not None:
        # 使用 date-time tag (0x19)
        if isinstance(dt, dict):
            result += encode_data(dt, "date-time")
        elif isinstance(dt, (bytes, bytearray)):
            result += bytes([0x19]) + bytes([len(dt)]) + bytes(dt)
        else:
            # 默认为当前时间的简单表示
            result += encode_data({"year": 2024, "month": 1, "day": 1,
                                    "weekday": 1, "hour": 0, "minute": 0,
                                    "second": 0, "hundredths": 0,
                                    "deviation": 0, "status": 0}, "date-time")

    # notification-body (array of structure)
    items = params.get("items", [])

    # 构建每个数据项的structure
    item_bytes = b""
    for item in items:
        if isinstance(item, dict):
            class_id = item.get("class_id", 0)
            obis_val = item.get("obis", "0-0:0.0.0.0")
            attribute_id = item.get("attribute_id", 2)
            value = item.get("value")
            data_type = item.get("data_type")
        else:
            raise ValueError(f"无效的数据项: {item}")

        # 构建cosem_attribute_descriptor (structure of 3 elements)
        # class_id (double-long-unsigned 或 long-unsigned) - 用2字节
        # obis (octet-string 6 bytes)
        # attribute_id (integer 或 unsigned) - 用1字节
        if isinstance(obis_val, (bytes, bytearray)):
            obis_bytes = bytes(obis_val)
        else:
            obis_bytes = obis_str_to_bytes(obis_val)

        # cosem_attribute_descriptor 是一个独立的structure (tag=0x02)
        # 包含3个元素: class_id(long-unsigned) + obis(octet-string) + attribute_id(unsigned)
        desc_content = (
            # class_id: long-unsigned (0x12)
            encode_data(class_id, "long-unsigned") +
            # obis: octet-string (0x09)
            encode_data(obis_bytes, "octet-string") +
            # attribute_id: unsigned (0x11)
            encode_data(attribute_id, "unsigned")
        )
        desc_struct = bytes([0x02]) + _encode_len(len(desc_content)) + desc_content

        # value
        if data_type:
            val_bytes = encode_data(value, data_type)
        else:
            val_bytes = encode_data(value)

        # 每个数据项是一个structure (descriptor + value)
        item_content = desc_struct + val_bytes
        item_bytes += bytes([0x02]) + _encode_len(len(item_content)) + item_content

    # 外层array
    result += bytes([0x01]) + _encode_len(len(item_bytes)) + item_bytes

    return result


def _encode_len(length: int) -> bytes:
    """辅助函数：编码BER长度"""
    if length < 0x80:
        return bytes([length])
    elif length <= 0xFF:
        return bytes([0x81, length])
    elif length <= 0xFFFF:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])


# ---------- DataNotification Confirm 构建 ----------

def build_data_notification_confirm(params: dict) -> bytes:
    """
    构建DataNotification确认帧

    注意: DLMS标准中，DataNotification默认是未确认模式(confirmed=false)，
    不需要确认。但在某些应用场景中，可能需要自定义确认机制。

    这里实现几种可能的确认方式:

    方式1 - EventNotification形式 (tag=0xC4):
      使用EventNotification作为确认响应，发送方发送一个事件表示已收到通知。

    方式2 - 简单ACK帧 (自定义):
      一个极简的确认帧，包含invoke_id和结果码。

    方式3 - 使用ActionResponse (tag=0xC8):
      如果通知是通过Action触发的，用ActionResponse确认。

    默认使用方式1（EventNotification形式）。

    Args:
        params: 参数字典:
            - confirm_type: "event" / "ack" / "action" (默认"event")
            - invoke_id: 调用ID (对应原通知的invoke_id)
            - result: 结果码 (0=成功, 默认0)
            - class_id: 事件类ID (默认0, event方式)
            - obis: 事件OBIS (默认"0-0:0.0.0.0", event方式)
            - attribute_id: 事件属性ID (默认2, event方式)
            - value: 确认载荷值 (可选)
            - data_type: 载荷数据类型 (可选)

    Returns:
        bytes: 确认帧数据
    """
    confirm_type = params.get("confirm_type", "event").lower()
    invoke_id = params.get("invoke_id", 0)
    result_code = params.get("result", 0)

    if confirm_type == "event":
        # 方式1: 使用EventNotification作为确认
        # EventNotification格式: tag(0xC4) + time(optional) + cosem_attr_desc + value
        class_id = params.get("class_id", 0)
        obis_val = params.get("obis", "0-0:0.0.0.0")
        attribute_id = params.get("attribute_id", 2)
        value = params.get("value", result_code)
        data_type = params.get("data_type", "unsigned")

        result = bytes([0xC4])  # EventNotification tag

        # 不含time字段
        # cosem_attribute_descriptor (裸9字节，无BER tag)
        result += class_id.to_bytes(2, "big")
        if isinstance(obis_val, (bytes, bytearray)):
            result += bytes(obis_val)
        else:
            result += obis_str_to_bytes(obis_val)
        result += bytes([attribute_id])

        # value
        result += encode_data(value, data_type)

        return result

    elif confirm_type == "ack":
        # 方式2: 极简ACK帧
        # 格式: tag(自定义) + invoke_id(4) + result(1)
        # 使用0x0E作为自定义ACK tag（DLMS中未使用的邻近值）
        # 注意: 这不是标准DLMS帧，仅用于自定义通信
        result = bytes([0x0E])  # 自定义ACK tag
        result += invoke_id.to_bytes(4, "big")
        result += bytes([result_code])
        return result

    elif confirm_type == "action":
        # 方式3: ActionResponse形式
        action_type = params.get("action_type", 1)
        result = bytes([0xC8])  # ActionResponse tag
        result += bytes([action_type])
        result += invoke_id.to_bytes(4, "big")
        result += bytes([result_code])  # result (0=success)
        if result_code == 0:
            # 可选的返回数据
            value = params.get("value")
            data_type = params.get("data_type")
            if value is not None:
                if data_type:
                    result += encode_data(value, data_type)
                else:
                    result += encode_data(value)
        return result

    else:
        raise ValueError(f"不支持的confirm_type: {confirm_type}")


# ---------- SetRequest 构建 ----------

def build_set_request(params: dict) -> bytes:
    """
    构建SetRequest APDU (简化版)

    Args:
        params: 参数字典:
            - set_type: 1/2/3 (默认1)
            - invoke_id: 调用ID (默认0)
            - class_id: 类ID
            - obis: OBIS码
            - attribute_id: 属性ID
            - value: 设置值
            - data_type: 数据类型

    Returns:
        bytes: SetRequest APDU数据
    """
    set_type = params.get("set_type", 1)
    invoke_id = params.get("invoke_id", 0)

    result = bytes([0xC2])  # SetRequest
    result += bytes([set_type])
    result += invoke_id.to_bytes(4, "big")

    if set_type == 1:  # normal
        class_id = params.get("class_id", 0)
        obis_val = params.get("obis", "0-0:0.0.0.0")
        attribute_id = params.get("attribute_id", 2)
        value = params.get("value")
        data_type = params.get("data_type")

        # cosem_attribute_descriptor (9 bytes)
        result += class_id.to_bytes(2, "big")
        if isinstance(obis_val, (bytes, bytearray)):
            result += bytes(obis_val)
        else:
            result += obis_str_to_bytes(obis_val)
        result += bytes([attribute_id])

        # access-selection (1 byte)
        result += bytes([0])

        # value
        if data_type:
            result += encode_data(value, data_type)
        elif value is not None:
            result += encode_data(value)
        else:
            result += encode_data(None, "null-data")

    return result
