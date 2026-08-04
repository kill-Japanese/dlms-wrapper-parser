"""
APDU解析器单元测试

测试内容:
1. BER/A-XDR 编解码器测试 - 各种数据类型的编码和解码
2. DataNotification 解析测试 - 构建真实数据并解析
3. DataNotification 构建测试 - 构建后再解析（往返测试）
4. DataNotification Confirm 构建测试
5. GetRequest 构建测试 - Normal / With-List
6. GetRequest 解析测试
7. GetResponse 构建和解析测试
8. GetResponse With-List 测试
9. 顶层 parse_apdu 测试
10. 边界条件和错误处理
"""
import unittest
import struct

from app.services.apdu_parser import (
    APDUParser,
    parse_apdu,
    build_apdu,
    build_get_request,
    build_get_response,
    build_data_notification,
    build_data_notification_confirm,
    build_set_request,
)
from app.utils.ber_encoder import (
    decode_data,
    encode_data,
    DATA_TYPES,
    DATA_TYPE_NAMES,
    _decode_length,
    _encode_length,
)
from app.utils.hex_utils import hex_to_bytes, bytes_to_hex
from app.utils.obis_utils import obis_str_to_bytes, obis_bytes_to_str
from app.models.apdu import (
    DataNotificationAPDU,
    DataNotificationConfirmAPDU,
    GetRequestAPDU,
    GetResponseAPDU,
    CosemDataItem,
    CosemAttributeDescriptor,
)


# ============================================================================
# BER/A-XDR 编解码器测试
# ============================================================================

class TestBEREncoderBasics(unittest.TestCase):
    """BER编解码器基础测试"""

    def test_length_encoding_short(self):
        """测试短格式长度编码"""
        for length in [0, 1, 50, 127]:
            encoded = _encode_length(length)
            self.assertEqual(len(encoded), 1)
            decoded, offset = _decode_length(encoded, 0)
            self.assertEqual(decoded, length)
            self.assertEqual(offset, 1)

    def test_length_encoding_long_1byte(self):
        """测试长格式长度编码（1字节长度值）"""
        for length in [128, 200, 255]:
            encoded = _encode_length(length)
            self.assertEqual(len(encoded), 2)
            self.assertEqual(encoded[0], 0x81)
            decoded, offset = _decode_length(encoded, 0)
            self.assertEqual(decoded, length)
            self.assertEqual(offset, 2)

    def test_length_encoding_long_2bytes(self):
        """测试长格式长度编码（2字节长度值）"""
        for length in [256, 1000, 65535]:
            encoded = _encode_length(length)
            self.assertEqual(len(encoded), 3)
            self.assertEqual(encoded[0], 0x82)
            decoded, offset = _decode_length(encoded, 0)
            self.assertEqual(decoded, length)
            self.assertEqual(offset, 3)

    def test_data_types_mapping(self):
        """测试数据类型映射"""
        # 验证关键类型的标签值
        self.assertEqual(DATA_TYPE_NAMES["null-data"], 0x00)
        self.assertEqual(DATA_TYPE_NAMES["array"], 0x01)
        self.assertEqual(DATA_TYPE_NAMES["structure"], 0x02)
        self.assertEqual(DATA_TYPE_NAMES["boolean"], 0x03)
        self.assertEqual(DATA_TYPE_NAMES["bit-string"], 0x04)
        self.assertEqual(DATA_TYPE_NAMES["double-long"], 0x05)
        self.assertEqual(DATA_TYPE_NAMES["double-long-unsigned"], 0x06)
        self.assertEqual(DATA_TYPE_NAMES["octet-string"], 0x09)
        self.assertEqual(DATA_TYPE_NAMES["visible-string"], 0x0a)
        self.assertEqual(DATA_TYPE_NAMES["utf8-string"], 0x0b)
        self.assertEqual(DATA_TYPE_NAMES["integer"], 0x0f)
        self.assertEqual(DATA_TYPE_NAMES["long"], 0x10)
        self.assertEqual(DATA_TYPE_NAMES["unsigned"], 0x11)
        self.assertEqual(DATA_TYPE_NAMES["long-unsigned"], 0x12)
        self.assertEqual(DATA_TYPE_NAMES["compact-array"], 0x13)
        self.assertEqual(DATA_TYPE_NAMES["long64"], 0x14)
        self.assertEqual(DATA_TYPE_NAMES["long64-unsigned"], 0x15)
        self.assertEqual(DATA_TYPE_NAMES["enum"], 0x16)
        self.assertEqual(DATA_TYPE_NAMES["float32"], 0x17)
        self.assertEqual(DATA_TYPE_NAMES["float64"], 0x18)
        self.assertEqual(DATA_TYPE_NAMES["date-time"], 0x19)
        self.assertEqual(DATA_TYPE_NAMES["date"], 0x1a)
        self.assertEqual(DATA_TYPE_NAMES["time"], 0x1b)
        self.assertEqual(DATA_TYPE_NAMES["dont-care"], 0xff)


class TestBEREncoderNumericTypes(unittest.TestCase):
    """数值类型编解码测试"""

    def test_null_data(self):
        """测试null-data类型"""
        enc = encode_data(None, "null-data")
        self.assertEqual(enc[0], 0x00)
        val, off, tn = decode_data(enc, 0)
        self.assertIsNone(val)
        self.assertEqual(tn, "null-data")

    def test_dont_care(self):
        """测试dont-care类型"""
        enc = encode_data(None, "dont-care")
        self.assertEqual(enc[0], 0xFF)
        val, off, tn = decode_data(enc, 0)
        self.assertIsNone(val)
        self.assertEqual(tn, "dont-care")

    def test_boolean_true(self):
        """测试boolean true"""
        enc = encode_data(True, "boolean")
        val, off, tn = decode_data(enc, 0)
        self.assertTrue(val)
        self.assertEqual(tn, "boolean")

    def test_boolean_false(self):
        """测试boolean false"""
        enc = encode_data(False, "boolean")
        val, off, tn = decode_data(enc, 0)
        self.assertFalse(val)
        self.assertEqual(tn, "boolean")

    def test_integer_int8(self):
        """测试integer (int8)"""
        test_values = [0, 1, -1, 127, -128]
        for val in test_values:
            enc = encode_data(val, "integer")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val, f"Failed for value {val}")
            self.assertEqual(tn, "integer")

    def test_long_int16(self):
        """测试long (int16)"""
        test_values = [0, 1, -1, 32767, -32768, 256, -256]
        for val in test_values:
            enc = encode_data(val, "long")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val, f"Failed for value {val}")
            self.assertEqual(tn, "long")

    def test_double_long_int32(self):
        """测试double-long (int32)"""
        test_values = [0, 1, -1, 2147483647, -2147483648, 1000000, -1000000]
        for val in test_values:
            enc = encode_data(val, "double-long")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val, f"Failed for value {val}")
            self.assertEqual(tn, "double-long")

    def test_long64_int64(self):
        """测试long64 (int64)"""
        test_values = [0, 1, -1, 9223372036854775807, -9223372036854775808]
        for val in test_values:
            enc = encode_data(val, "long64")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val, f"Failed for value {val}")
            self.assertEqual(tn, "long64")

    def test_unsigned_uint8(self):
        """测试unsigned (uint8)"""
        for val in [0, 1, 100, 255]:
            enc = encode_data(val, "unsigned")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val)
            self.assertEqual(tn, "unsigned")

    def test_long_unsigned_uint16(self):
        """测试long-unsigned (uint16)"""
        for val in [0, 1, 1000, 65535]:
            enc = encode_data(val, "long-unsigned")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val)
            self.assertEqual(tn, "long-unsigned")

    def test_double_long_unsigned_uint32(self):
        """测试double-long-unsigned (uint32)"""
        for val in [0, 1, 100000, 4294967295]:
            enc = encode_data(val, "double-long-unsigned")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val)
            self.assertEqual(tn, "double-long-unsigned")

    def test_long64_unsigned_uint64(self):
        """测试long64-unsigned (uint64)"""
        for val in [0, 1, 1000000, 18446744073709551615]:
            enc = encode_data(val, "long64-unsigned")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val)
            self.assertEqual(tn, "long64-unsigned")

    def test_enum(self):
        """测试enum类型"""
        for val in [0, 1, 10, 255]:
            enc = encode_data(val, "enum")
            decoded, off, tn = decode_data(enc, 0)
            self.assertEqual(decoded, val)
            self.assertEqual(tn, "enum")

    def test_float32(self):
        """测试float32类型"""
        test_values = [0.0, 1.0, -1.0, 3.14, 1e10, -1e10]
        for val in test_values:
            enc = encode_data(val, "float32")
            decoded, off, tn = decode_data(enc, 0)
            self.assertAlmostEqual(decoded, val, places=5)
            self.assertEqual(tn, "float32")

    def test_float64(self):
        """测试float64类型"""
        test_values = [0.0, 1.0, -1.0, 3.14159265358979, 1e100, -1e100]
        for val in test_values:
            enc = encode_data(val, "float64")
            decoded, off, tn = decode_data(enc, 0)
            self.assertAlmostEqual(decoded, val, places=10)
            self.assertEqual(tn, "float64")


class TestBEREncoderStringTypes(unittest.TestCase):
    """字符串类型编解码测试"""

    def test_octet_string_empty(self):
        """测试空octet-string"""
        enc = encode_data(b"", "octet-string")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, b"")
        self.assertEqual(tn, "octet-string")

    def test_octet_string_bytes(self):
        """测试octet-string (bytes输入)"""
        test_data = [
            b"\x00",
            b"\x01\x02\x03\x04",
            bytes(range(256)),
            b"hello world",
        ]
        for data in test_data:
            enc = encode_data(data, "octet-string")
            val, off, tn = decode_data(enc, 0)
            self.assertEqual(val, data)
            self.assertEqual(tn, "octet-string")

    def test_octet_string_hex_input(self):
        """测试octet-string (十六进制字符串输入)"""
        enc = encode_data("01020304", "octet-string")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, b"\x01\x02\x03\x04")

    def test_visible_string(self):
        """测试visible-string"""
        test_strings = ["", "hello", "Hello, World!", "1234567890"]
        for s in test_strings:
            enc = encode_data(s, "visible-string")
            val, off, tn = decode_data(enc, 0)
            self.assertEqual(val, s)
            self.assertEqual(tn, "visible-string")

    def test_utf8_string(self):
        """测试utf8-string"""
        test_strings = ["", "hello", "你好世界", "Hello, 世界！", "🎉🚀"]
        for s in test_strings:
            enc = encode_data(s, "utf8-string")
            val, off, tn = decode_data(enc, 0)
            self.assertEqual(val, s)
            self.assertEqual(tn, "utf8-string")

    def test_long_octet_string(self):
        """测试长octet-string（长格式长度）"""
        data = bytes(range(256)) + bytes(range(256))  # 512 bytes
        enc = encode_data(data, "octet-string")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, data)
        self.assertEqual(tn, "octet-string")


class TestBEREncoderDateTypes(unittest.TestCase):
    """日期时间类型编解码测试"""

    def test_date_time_encode_decode(self):
        """测试date-time编解码"""
        dt = {
            "year": 2024,
            "month": 6,
            "day": 15,
            "weekday": 6,
            "hour": 14,
            "minute": 30,
            "second": 45,
            "hundredths": 50,
            "deviation": 480,  # UTC+8 (in minutes)
            "status": 0,
        }
        enc = encode_data(dt, "date-time")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "date-time")
        self.assertEqual(val["year"], 2024)
        self.assertEqual(val["month"], 6)
        self.assertEqual(val["day"], 15)
        self.assertEqual(val["hour"], 14)
        self.assertEqual(val["minute"], 30)
        self.assertEqual(val["second"], 45)
        self.assertEqual(val["hundredths"], 50)
        self.assertEqual(val["deviation"], 480)
        self.assertEqual(val["status"], 0)
        self.assertIn("iso", val)

    def test_date_encode_decode(self):
        """测试date编解码"""
        d = {
            "year": 2024,
            "month": 12,
            "day": 25,
            "weekday": 3,
        }
        enc = encode_data(d, "date")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "date")
        self.assertEqual(val["year"], 2024)
        self.assertEqual(val["month"], 12)
        self.assertEqual(val["day"], 25)
        self.assertEqual(val["weekday"], 3)

    def test_time_encode_decode(self):
        """测试time编解码"""
        t = {
            "hour": 23,
            "minute": 59,
            "second": 59,
            "hundredths": 99,
        }
        enc = encode_data(t, "time")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "time")
        self.assertEqual(val["hour"], 23)
        self.assertEqual(val["minute"], 59)
        self.assertEqual(val["second"], 59)
        self.assertEqual(val["hundredths"], 99)


class TestBEREncoderStructureTypes(unittest.TestCase):
    """结构类型（array/structure）编解码测试"""

    def test_structure_simple(self):
        """测试简单structure"""
        items = [100, "hello", True]
        # 使用显式类型
        typed_items = [
            (100, "integer"),
            ("hello", "utf8-string"),
            (True, "boolean"),
        ]
        enc = encode_data(typed_items, "structure")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "structure")
        self.assertIsInstance(val, list)
        self.assertEqual(len(val), 3)
        self.assertEqual(val[0], 100)
        self.assertEqual(val[1], "hello")
        self.assertEqual(val[2], True)

    def test_structure_nested(self):
        """测试嵌套structure"""
        inner = [(42, "long-unsigned"), ("test", "visible-string")]
        outer = [
            (1, "integer"),
            (inner, "structure"),
            (True, "boolean"),
        ]
        enc = encode_data(outer, "structure")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "structure")
        self.assertEqual(val[0], 1)
        self.assertIsInstance(val[1], list)
        self.assertEqual(len(val[1]), 2)
        self.assertEqual(val[1][0], 42)
        self.assertEqual(val[1][1], "test")
        self.assertEqual(val[2], True)

    def test_array_simple(self):
        """测试简单array"""
        items = [(i, "integer") for i in range(5)]
        enc = encode_data(items, "array")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "array")
        self.assertEqual(len(val), 5)
        for i in range(5):
            self.assertEqual(val[i], i)

    def test_array_of_structures(self):
        """测试array of structure（类似DataNotification body）"""
        items = []
        for i in range(3):
            struct_items = [
                (i + 1, "long-unsigned"),  # class_id
                (bytes([0, 0, 1, i, 0, 255]), "octet-string"),  # obis
                (2, "unsigned"),  # attribute_id
                (i * 100, "double-long-unsigned"),  # value
            ]
            items.append((struct_items, "structure"))

        enc = encode_data(items, "array")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "array")
        self.assertEqual(len(val), 3)

        for i, struct_val in enumerate(val):
            self.assertIsInstance(struct_val, list)
            self.assertEqual(struct_val[0], i + 1)  # class_id
            self.assertEqual(struct_val[2], 2)  # attribute_id
            self.assertEqual(struct_val[3], i * 100)  # value

    def test_structure_empty(self):
        """测试空structure"""
        enc = encode_data([], "structure")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "structure")
        self.assertEqual(val, [])

    def test_structure_with_dict_type_spec(self):
        """测试使用dict指定类型的structure"""
        items = [
            {"type": "double-long-unsigned", "value": 12345},
            {"type": "utf8-string", "value": "test"},
        ]
        enc = encode_data(items, "structure")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(len(val), 2)
        self.assertEqual(val[0], 12345)
        self.assertEqual(val[1], "test")

    def test_bit_string(self):
        """测试bit-string类型"""
        bit_data = {"bytes": b"\xff\x00", "unused_bits": 0}
        enc = encode_data(bit_data, "bit-string")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "bit-string")
        self.assertEqual(val["bytes"], b"\xff\x00")
        self.assertEqual(val["unused_bits"], 0)
        self.assertEqual(val["bit_count"], 16)


class TestBEREncoderAutoInference(unittest.TestCase):
    """类型自动推断测试"""

    def test_auto_null(self):
        """测试自动推断None"""
        enc = encode_data(None)
        val, off, tn = decode_data(enc, 0)
        self.assertIsNone(val)
        self.assertEqual(tn, "null-data")

    def test_auto_bool(self):
        """测试自动推断bool"""
        enc = encode_data(True)
        val, off, tn = decode_data(enc, 0)
        self.assertTrue(val)
        self.assertEqual(tn, "boolean")

    def test_auto_small_int(self):
        """测试自动推断小整数"""
        enc = encode_data(100)  # fits in int8
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, 100)

    def test_auto_large_int(self):
        """测试自动推断大整数"""
        enc = encode_data(100000)  # fits in int32
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, 100000)

    def test_auto_float(self):
        """测试自动推断float"""
        enc = encode_data(3.14)
        val, off, tn = decode_data(enc, 0)
        self.assertAlmostEqual(val, 3.14, places=10)
        self.assertEqual(tn, "float64")

    def test_auto_bytes(self):
        """测试自动推断bytes"""
        enc = encode_data(b"\x01\x02\x03")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, b"\x01\x02\x03")
        self.assertEqual(tn, "octet-string")

    def test_auto_string(self):
        """测试自动推断str"""
        enc = encode_data("hello")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, "hello")
        self.assertEqual(tn, "utf8-string")

    def test_auto_list_structure(self):
        """测试自动推断list为structure"""
        enc = encode_data([1, 2, 3])
        val, off, tn = decode_data(enc, 0)
        self.assertIsInstance(val, list)
        self.assertEqual(tn, "structure")


# ============================================================================
# DataNotification 测试
# ============================================================================

class TestDataNotificationParsing(unittest.TestCase):
    """DataNotification解析测试"""

    def test_parse_basic_notification(self):
        """测试基本DataNotification解析"""
        dn = build_data_notification({
            "invoke_id": 100,
            "items": [
                {
                    "class_id": 3,
                    "obis": "1-0:1.8.0.255",
                    "attribute_id": 2,
                    "value": 12345678,
                    "data_type": "double-long-unsigned",
                },
            ]
        })

        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)
        self.assertEqual(result.tag, 0x0F)
        self.assertEqual(result.type_name, "DataNotification")
        self.assertEqual(result.invoke_id, 100)
        self.assertEqual(result.item_count, 1)
        self.assertEqual(len(result.items), 1)

        item = result.items[0]
        self.assertEqual(item.class_id, 3)
        self.assertEqual(item.obis, "1-0:1.8.0.255")
        self.assertEqual(item.attribute_id, 2)
        self.assertEqual(item.value, 12345678)

    def test_parse_notification_with_datetime(self):
        """测试带datetime的DataNotification解析"""
        dt = {
            "year": 2024, "month": 6, "day": 15, "weekday": 6,
            "hour": 14, "minute": 30, "second": 0, "hundredths": 0,
            "deviation": 480, "status": 0,
        }
        dn = build_data_notification({
            "invoke_id": 200,
            "datetime": dt,
            "items": [
                {
                    "class_id": 1,
                    "obis": "0-0:1.0.0.255",
                    "attribute_id": 2,
                    "value": "test",
                    "data_type": "visible-string",
                },
            ]
        })

        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)
        self.assertEqual(result.invoke_id, 200)
        self.assertIsNotNone(result.datetime)
        self.assertEqual(result.datetime["year"], 2024)
        self.assertEqual(result.datetime["month"], 6)
        self.assertEqual(result.datetime["day"], 15)
        self.assertEqual(result.item_count, 1)
        self.assertEqual(result.items[0].value, "test")

    def test_parse_multiple_items(self):
        """测试多数据项DataNotification"""
        items = []
        for i in range(5):
            items.append({
                "class_id": 3,
                "obis": f"1-0:{i+1}.8.0.255",
                "attribute_id": 2,
                "value": i * 1000,
                "data_type": "double-long-unsigned",
            })

        dn = build_data_notification({
            "invoke_id": 300,
            "items": items,
        })

        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)
        self.assertEqual(result.item_count, 5)
        self.assertEqual(len(result.items), 5)

        for i, item in enumerate(result.items):
            self.assertEqual(item.class_id, 3)
            self.assertEqual(item.attribute_id, 2)
            self.assertEqual(item.value, i * 1000)

    def test_parse_different_data_types(self):
        """测试不同数据类型的DataNotification项"""
        items = [
            {"class_id": 1, "obis": "0-0:1.0.0.255", "attribute_id": 2,
             "value": True, "data_type": "boolean"},
            {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2,
             "value": 12345, "data_type": "double-long-unsigned"},
            {"class_id": 8, "obis": "0-0:96.1.0.255", "attribute_id": 2,
             "value": "Meter001", "data_type": "visible-string"},
            {"class_id": 9, "obis": "0-0:1.0.0.255", "attribute_id": 2,
             "value": b"\x00\x01\x02\x03", "data_type": "octet-string"},
        ]

        dn = build_data_notification({
            "invoke_id": 400,
            "items": items,
        })

        result = parse_apdu(dn)
        self.assertEqual(result.item_count, 4)
        self.assertTrue(isinstance(result.items[0].value, bool))
        self.assertEqual(result.items[1].value, 12345)
        self.assertEqual(result.items[2].value, "Meter001")
        self.assertEqual(result.items[3].value, b"\x00\x01\x02\x03")

    def test_parse_empty_notification(self):
        """测试空DataNotification（无数据项）"""
        dn = build_data_notification({
            "invoke_id": 500,
            "items": [],
        })

        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)
        self.assertEqual(result.item_count, 0)
        self.assertEqual(len(result.items), 0)


# ============================================================================
# DataNotification Confirm 测试
# ============================================================================

class TestDataNotificationConfirm(unittest.TestCase):
    """DataNotification确认帧测试"""

    def test_build_confirm_event_type(self):
        """测试构建event类型确认帧"""
        confirm = build_data_notification_confirm({
            "confirm_type": "event",
            "invoke_id": 100,
            "result": 0,
            "class_id": 8,
            "obis": "0-0:96.11.8.255",
            "attribute_id": 1,
        })

        self.assertEqual(confirm[0], 0xC4)  # EventNotification tag
        # 验证长度大于0
        self.assertGreater(len(confirm), 1)

    def test_build_confirm_ack_type(self):
        """测试构建ack类型确认帧"""
        confirm = build_data_notification_confirm({
            "confirm_type": "ack",
            "invoke_id": 200,
            "result": 0,
        })

        self.assertEqual(confirm[0], 0x0E)  # 自定义ACK tag
        # invoke_id (4 bytes)
        invoke_id = int.from_bytes(confirm[1:5], "big")
        self.assertEqual(invoke_id, 200)
        # result (1 byte)
        self.assertEqual(confirm[5], 0)
        self.assertEqual(len(confirm), 6)

    def test_build_confirm_action_type(self):
        """测试构建action类型确认帧"""
        confirm = build_data_notification_confirm({
            "confirm_type": "action",
            "invoke_id": 300,
            "result": 0,
            "action_type": 1,
        })

        self.assertEqual(confirm[0], 0xC8)  # ActionResponse tag
        self.assertEqual(confirm[1], 1)  # action_type
        invoke_id = int.from_bytes(confirm[2:6], "big")
        self.assertEqual(invoke_id, 300)
        self.assertEqual(confirm[6], 0)  # result

    def test_build_confirm_with_value(self):
        """测试带返回值的确认帧"""
        confirm = build_data_notification_confirm({
            "confirm_type": "action",
            "invoke_id": 400,
            "result": 0,
            "value": "OK",
            "data_type": "visible-string",
        })

        self.assertEqual(confirm[0], 0xC8)
        # 解析验证
        result = parse_apdu(confirm)
        self.assertEqual(result.type_name, "ActionResponse")
        self.assertEqual(result.invoke_id, 400)
        self.assertEqual(result.result_code, 0)

    def test_build_confirm_default_type(self):
        """测试默认confirm_type"""
        confirm = build_data_notification_confirm({
            "invoke_id": 500,
            "result": 0,
        })

        # 默认应该是event类型
        self.assertEqual(confirm[0], 0xC4)

    def test_build_apdu_confirm_via_generic(self):
        """测试通过build_apdu泛型函数构建confirm"""
        confirm = build_apdu("confirm", {
            "confirm_type": "ack",
            "invoke_id": 600,
            "result": 0,
        })

        self.assertEqual(confirm[0], 0x0E)
        invoke_id = int.from_bytes(confirm[1:5], "big")
        self.assertEqual(invoke_id, 600)


# ============================================================================
# GetRequest 测试
# ============================================================================

class TestGetRequestBuilding(unittest.TestCase):
    """GetRequest构建测试"""

    def test_build_get_request_normal(self):
        """测试构建Get-Request-Normal"""
        req = build_get_request({
            "get_type": 1,
            "invoke_id": 1,
            "class_id": 3,
            "obis": "1-0:1.8.0.255",
            "attribute_id": 2,
        })

        self.assertEqual(req[0], 0xC0)  # GetRequest tag
        self.assertEqual(req[1], 1)  # get_type = normal
        invoke_id = int.from_bytes(req[2:6], "big")
        self.assertEqual(invoke_id, 1)
        # class_id (2 bytes)
        class_id = int.from_bytes(req[6:8], "big")
        self.assertEqual(class_id, 3)
        # obis (6 bytes)
        obis = obis_bytes_to_str(req[8:14])
        self.assertEqual(obis, "1-0:1.8.0.255")
        # attribute_id (1 byte)
        self.assertEqual(req[14], 2)
        # access-selection (1 byte)
        self.assertEqual(req[15], 0)

    def test_build_get_request_normal_with_access_selection(self):
        """测试带access-selection的Get-Request-Normal"""
        req = build_get_request({
            "get_type": 1,
            "invoke_id": 2,
            "class_id": 1,
            "obis": "0-0:1.0.0.255",
            "attribute_id": 2,
            "access_selection": 1,
        })

        self.assertEqual(req[15], 1)  # access_selection

    def test_build_get_request_with_list(self):
        """测试构建Get-Request-With-List"""
        req = build_get_request({
            "get_type": 3,
            "invoke_id": 3,
            "attribute_list": [
                {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2},
                {"class_id": 3, "obis": "1-0:2.8.0.255", "attribute_id": 2},
                {"class_id": 1, "obis": "0-0:1.0.0.255", "attribute_id": 2},
            ]
        })

        self.assertEqual(req[0], 0xC0)
        self.assertEqual(req[1], 3)  # get_type = with-list
        invoke_id = int.from_bytes(req[2:6], "big")
        self.assertEqual(invoke_id, 3)
        # 列表长度
        self.assertEqual(req[6], 3)

    def test_build_get_request_with_list_tuple_format(self):
        """测试使用tuple格式构建Get-Request-With-List"""
        req = build_get_request({
            "get_type": 3,
            "invoke_id": 4,
            "attribute_list": [
                (3, "1-0:1.8.0.255", 2),
                (3, "1-0:2.8.0.255", 2),
            ]
        })

        self.assertEqual(req[0], 0xC0)
        self.assertEqual(req[1], 3)
        self.assertEqual(req[6], 2)  # 2 items

    def test_build_get_request_next(self):
        """测试构建Get-Request-Next"""
        req = build_get_request({
            "get_type": 2,
            "invoke_id": 5,
            "block_number": 1,
        })

        self.assertEqual(req[0], 0xC0)
        self.assertEqual(req[1], 2)  # get_type = next
        invoke_id = int.from_bytes(req[2:6], "big")
        self.assertEqual(invoke_id, 5)
        block_num = int.from_bytes(req[6:10], "big")
        self.assertEqual(block_num, 1)

    def test_build_get_request_default_params(self):
        """测试默认参数构建GetRequest"""
        req = build_get_request({})

        self.assertEqual(req[0], 0xC0)
        self.assertEqual(req[1], 1)  # 默认 get_type=1
        invoke_id = int.from_bytes(req[2:6], "big")
        self.assertEqual(invoke_id, 0)  # 默认 invoke_id=0

    def test_build_get_request_bytes_obis(self):
        """测试使用bytes类型的OBIS构建"""
        obis_bytes = bytes([1, 0, 1, 8, 0, 255])
        req = build_get_request({
            "get_type": 1,
            "invoke_id": 6,
            "class_id": 3,
            "obis": obis_bytes,
            "attribute_id": 2,
        })

        self.assertEqual(req[8:14], obis_bytes)

    def test_build_apdu_get_request_generic(self):
        """测试通过build_apdu泛型函数构建GetRequest"""
        req = build_apdu("get-request", {
            "get_type": 1,
            "invoke_id": 7,
            "class_id": 3,
            "obis": "1-0:1.8.0.255",
            "attribute_id": 2,
        })

        self.assertEqual(req[0], 0xC0)
        self.assertEqual(req[1], 1)


class TestGetRequestParsing(unittest.TestCase):
    """GetRequest解析测试"""

    def test_parse_get_request_normal(self):
        """测试解析Get-Request-Normal"""
        req = build_get_request({
            "get_type": 1,
            "invoke_id": 100,
            "class_id": 3,
            "obis": "1-0:1.8.0.255",
            "attribute_id": 2,
        })

        result = parse_apdu(req)
        self.assertIsInstance(result, GetRequestAPDU)
        self.assertEqual(result.tag, 0xC0)
        self.assertEqual(result.get_type, 1)
        self.assertEqual(result.invoke_id, 100)
        self.assertEqual(result.class_id, 3)
        self.assertEqual(result.obis, "1-0:1.8.0.255")
        self.assertEqual(result.attribute_id, 2)

    def test_parse_get_request_with_list(self):
        """测试解析Get-Request-With-List"""
        req = build_get_request({
            "get_type": 3,
            "invoke_id": 200,
            "attribute_list": [
                {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2},
                {"class_id": 3, "obis": "1-0:2.8.0.255", "attribute_id": 3},
            ]
        })

        result = parse_apdu(req)
        self.assertIsInstance(result, GetRequestAPDU)
        self.assertEqual(result.get_type, 3)
        self.assertEqual(result.invoke_id, 200)
        self.assertEqual(len(result.attribute_list), 2)

        self.assertEqual(result.attribute_list[0].class_id, 3)
        self.assertEqual(result.attribute_list[0].obis, "1-0:1.8.0.255")
        self.assertEqual(result.attribute_list[0].attribute_id, 2)

        self.assertEqual(result.attribute_list[1].class_id, 3)
        self.assertEqual(result.attribute_list[1].obis, "1-0:2.8.0.255")
        self.assertEqual(result.attribute_list[1].attribute_id, 3)

    def test_parse_get_request_next(self):
        """测试解析Get-Request-Next"""
        req = build_get_request({
            "get_type": 2,
            "invoke_id": 300,
            "block_number": 5,
        })

        result = parse_apdu(req)
        self.assertIsInstance(result, GetRequestAPDU)
        self.assertEqual(result.get_type, 2)
        self.assertEqual(result.invoke_id, 300)
        self.assertEqual(result.block_number, 5)

    def test_get_request_roundtrip_normal(self):
        """测试Get-Request-Normal往返（构建后解析）"""
        test_cases = [
            {"class_id": 1, "obis": "0-0:1.0.0.255", "attribute_id": 2},
            {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2},
            {"class_id": 8, "obis": "0-0:96.1.0.255", "attribute_id": 2},
        ]

        for i, tc in enumerate(test_cases):
            req = build_get_request({
                "get_type": 1,
                "invoke_id": i + 1,
                **tc,
            })
            result = parse_apdu(req)
            self.assertEqual(result.class_id, tc["class_id"],
                             f"Failed for class_id={tc['class_id']}")
            self.assertEqual(result.obis, tc["obis"],
                             f"Failed for obis={tc['obis']}")
            self.assertEqual(result.attribute_id, tc["attribute_id"],
                             f"Failed for attribute_id={tc['attribute_id']}")

    def test_get_request_roundtrip_with_list(self):
        """测试Get-Request-With-List往返"""
        attr_list = [
            {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2},
            {"class_id": 3, "obis": "1-0:2.8.0.255", "attribute_id": 2},
            {"class_id": 3, "obis": "1-0:3.8.0.255", "attribute_id": 2},
        ]

        req = build_get_request({
            "get_type": 3,
            "invoke_id": 999,
            "attribute_list": attr_list,
        })

        result = parse_apdu(req)
        self.assertEqual(len(result.attribute_list), 3)

        for i, attr in enumerate(result.attribute_list):
            self.assertEqual(attr.class_id, attr_list[i]["class_id"])
            self.assertEqual(attr.obis, attr_list[i]["obis"])
            self.assertEqual(attr.attribute_id, attr_list[i]["attribute_id"])


# ============================================================================
# GetResponse 测试
# ============================================================================

class TestGetResponseBuilding(unittest.TestCase):
    """GetResponse构建测试"""

    def test_build_get_response_normal_data(self):
        """测试构建带数据的Get-Response-Normal"""
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 1,
            "result_code": 0,
            "value": 12345,
            "data_type": "double-long-unsigned",
        })

        self.assertEqual(resp[0], 0xC1)  # GetResponse tag
        self.assertEqual(resp[1], 1)  # get_type = normal
        invoke_id = int.from_bytes(resp[2:6], "big")
        self.assertEqual(invoke_id, 1)
        self.assertEqual(resp[6], 0)  # result_code = data

    def test_build_get_response_error(self):
        """测试构建错误GetResponse"""
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 2,
            "result_code": 2,  # hardware fault
        })

        self.assertEqual(resp[0], 0xC1)
        self.assertEqual(resp[6], 2)  # error code
        # 错误响应不应有数据
        self.assertEqual(len(resp), 7)  # tag + type + invoke_id + result_code

    def test_build_get_response_datablock(self):
        """测试构建datablock类型GetResponse"""
        raw_data = b"\x01\x02\x03\x04\x05"
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 3,
            "result_code": 1,  # datablock
            "last_block": True,
            "block_number": 1,
            "raw_data": raw_data,
        })

        self.assertEqual(resp[0], 0xC1)
        self.assertEqual(resp[6], 1)  # result_code = datablock
        self.assertEqual(resp[7], 1)  # last_block = True
        block_num = int.from_bytes(resp[8:12], "big")
        self.assertEqual(block_num, 1)

    def test_build_get_response_with_list(self):
        """测试构建Get-Response-With-List"""
        resp = build_get_response({
            "get_type": 3,
            "invoke_id": 4,
            "results": [
                {"success": True, "value": 100, "data_type": "long-unsigned"},
                {"success": True, "value": "ok", "data_type": "visible-string"},
                {"success": False, "result_code": 2},
            ]
        })

        self.assertEqual(resp[0], 0xC1)
        self.assertEqual(resp[1], 3)  # get_type = with-list
        invoke_id = int.from_bytes(resp[2:6], "big")
        self.assertEqual(invoke_id, 4)
        self.assertEqual(resp[6], 3)  # 3 results

    def test_build_get_response_auto_type(self):
        """测试自动推断数据类型构建GetResponse"""
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 5,
            "result_code": 0,
            "value": 999,
            # 不指定data_type，自动推断
        })

        self.assertEqual(resp[0], 0xC1)
        self.assertEqual(resp[6], 0)
        # 验证数据部分
        val, off, tn = decode_data(resp, 7)
        self.assertEqual(val, 999)

    def test_build_apdu_get_response_generic(self):
        """测试通过build_apdu泛型函数构建GetResponse"""
        resp = build_apdu("get-response", {
            "get_type": 1,
            "invoke_id": 6,
            "result_code": 0,
            "value": True,
            "data_type": "boolean",
        })

        self.assertEqual(resp[0], 0xC1)


class TestGetResponseParsing(unittest.TestCase):
    """GetResponse解析测试"""

    def test_parse_get_response_data(self):
        """测试解析带数据的GetResponse"""
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 100,
            "result_code": 0,
            "value": 54321,
            "data_type": "double-long-unsigned",
        })

        result = parse_apdu(resp)
        self.assertIsInstance(result, GetResponseAPDU)
        self.assertEqual(result.tag, 0xC1)
        self.assertEqual(result.get_type, 1)
        self.assertEqual(result.invoke_id, 100)
        self.assertEqual(result.result_code, 0)
        self.assertEqual(result.result, "success")
        self.assertEqual(result.data_type, "double-long-unsigned")
        self.assertEqual(result.value, 54321)

    def test_parse_get_response_error(self):
        """测试解析错误GetResponse"""
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 200,
            "result_code": 2,  # hardware fault
        })

        result = parse_apdu(resp)
        self.assertIsInstance(result, GetResponseAPDU)
        self.assertEqual(result.result_code, 2)
        self.assertIn("error", result.result)

    def test_parse_get_response_datablock(self):
        """测试解析datablock类型GetResponse"""
        raw_data = bytes(range(20))
        resp = build_get_response({
            "get_type": 1,
            "invoke_id": 300,
            "result_code": 1,  # datablock
            "last_block": False,
            "block_number": 3,
            "raw_data": raw_data,
        })

        result = parse_apdu(resp)
        self.assertIsInstance(result, GetResponseAPDU)
        self.assertTrue(result.is_block)
        self.assertFalse(result.last_block)
        self.assertEqual(result.block_number, 3)
        self.assertEqual(result.value, raw_data)

    def test_parse_get_response_with_list(self):
        """测试解析Get-Response-With-List"""
        resp = build_get_response({
            "get_type": 3,
            "invoke_id": 400,
            "results": [
                {"success": True, "value": 1000, "data_type": "double-long-unsigned"},
                {"success": True, "value": "hello", "data_type": "visible-string"},
                {"success": False, "result_code": 3},
            ]
        })

        result = parse_apdu(resp)
        self.assertIsInstance(result, GetResponseAPDU)
        self.assertEqual(result.get_type, 3)
        self.assertEqual(len(result.results), 3)

        self.assertTrue(result.results[0]["success"])
        self.assertEqual(result.results[0]["value"], 1000)
        self.assertEqual(result.results[0]["data_type"], "double-long-unsigned")

        self.assertTrue(result.results[1]["success"])
        self.assertEqual(result.results[1]["value"], "hello")

        self.assertFalse(result.results[2]["success"])
        self.assertEqual(result.results[2]["result_code"], 3)

    def test_get_response_roundtrip_various_types(self):
        """测试不同数据类型的GetResponse往返"""
        test_cases = [
            (100, "integer"),
            (1000, "long-unsigned"),
            (100000, "double-long-unsigned"),
            (True, "boolean"),
            (False, "boolean"),
            ("test string", "visible-string"),
            ("utf8测试", "utf8-string"),
            (b"\x01\x02\x03", "octet-string"),
            (3.14, "float64"),
        ]

        for value, data_type in test_cases:
            resp = build_get_response({
                "get_type": 1,
                "invoke_id": 999,
                "result_code": 0,
                "value": value,
                "data_type": data_type,
            })

            result = parse_apdu(resp)
            self.assertEqual(result.result_code, 0, f"Failed for {data_type}")

            if isinstance(value, float):
                self.assertAlmostEqual(result.value, value, places=5)
            else:
                self.assertEqual(result.value, value,
                                 f"Failed for {data_type}: expected {value}, got {result.value}")

    def test_get_response_with_list_roundtrip(self):
        """测试Get-Response-With-List往返"""
        results = [
            {"success": True, "value": 100, "data_type": "integer"},
            {"success": True, "value": "OK", "data_type": "visible-string"},
            {"success": True, "value": True, "data_type": "boolean"},
            {"success": True, "value": b"\xaa\xbb", "data_type": "octet-string"},
        ]

        resp = build_get_response({
            "get_type": 3,
            "invoke_id": 777,
            "results": results,
        })

        result = parse_apdu(resp)
        self.assertEqual(len(result.results), 4)

        for i, expected in enumerate(results):
            self.assertEqual(result.results[i]["success"], expected["success"])
            if expected["success"]:
                self.assertEqual(result.results[i]["value"], expected["value"])


# ============================================================================
# 其他APDU类型测试
# ============================================================================

class TestOtherAPDUTypes(unittest.TestCase):
    """其他APDU类型测试"""

    def test_parse_unknown_apdu(self):
        """测试解析未知APDU类型"""
        data = bytes([0x99, 0x01, 0x02, 0x03])
        result = parse_apdu(data)
        self.assertEqual(result.type_name.split("(")[0], "Unknown")
        self.assertEqual(result.tag, 0x99)

    def test_parse_general_glo_ciphering(self):
        """测试解析GeneralGloCiphering"""
        # 构造一个简单的GeneralGloCiphering
        system_title = bytes(range(8))
        ciphered = b"\x00\x01\x02\x03\x04"

        data = bytes([0xDB])  # tag
        data += bytes([8]) + system_title  # system-title
        data += bytes([len(ciphered)]) + ciphered  # ciphered-data

        result = parse_apdu(data)
        self.assertEqual(result.type_name, "GeneralGloCiphering")
        self.assertEqual(result.system_title, system_title.hex())
        self.assertEqual(result.ciphered_data, ciphered.hex())

    def test_parse_event_notification(self):
        """测试解析EventNotification"""
        from app.utils.ber_encoder import encode_data

        data = bytes([0xC4])  # tag
        # cosem_attribute_descriptor (9 bytes raw)
        data += (3).to_bytes(2, "big")  # class_id
        data += bytes([1, 0, 1, 8, 0, 255])  # obis
        data += bytes([2])  # attribute_id
        # value
        data += encode_data(12345, "long-unsigned")

        result = parse_apdu(data)
        self.assertEqual(result.type_name, "EventNotification")
        self.assertEqual(result.class_id, 3)
        self.assertEqual(result.obis, "1-0:1.8.0.255")
        self.assertEqual(result.attribute_id, 2)
        self.assertEqual(result.value, 12345)

    def test_build_set_request(self):
        """测试构建SetRequest"""
        req = build_set_request({
            "set_type": 1,
            "invoke_id": 50,
            "class_id": 3,
            "obis": "1-0:1.8.0.255",
            "attribute_id": 2,
            "value": 99999,
            "data_type": "double-long-unsigned",
        })

        self.assertEqual(req[0], 0xC2)
        self.assertEqual(req[1], 1)
        invoke_id = int.from_bytes(req[2:6], "big")
        self.assertEqual(invoke_id, 50)

        # 解析验证
        result = parse_apdu(req)
        self.assertEqual(result.type_name, "SetRequest")
        self.assertEqual(result.class_id, 3)
        self.assertEqual(result.obis, "1-0:1.8.0.255")
        self.assertEqual(result.attribute_id, 2)


# ============================================================================
# 顶层函数和边界条件测试
# ============================================================================

class TestParseAPDUTopLevel(unittest.TestCase):
    """顶层parse_apdu函数测试"""

    def test_parse_empty_data(self):
        """测试空数据"""
        with self.assertRaises(ValueError):
            parse_apdu(b"")

    def test_parse_single_byte(self):
        """测试单字节数据"""
        # 只有tag，没有内容
        result = parse_apdu(b"\x00")
        self.assertIn("Unknown", result.type_name)

    def test_parse_all_known_types(self):
        """测试所有已知类型的tag"""
        # 为每种已知类型构造最小有效数据
        # 注意：由于parse_apdu会捕获异常，即使数据不完整，只要tag能识别，就应返回正确类型
        test_cases = [
            # (tag, expected_type, data_builder)
            (0x0F, "DataNotification",
             lambda t: bytes([t, 0, 0, 0, 1, 0x01, 0x00])),  # invoke_id + empty array
            (0xC0, "GetRequest",
             lambda t: bytes([t, 1, 0, 0, 0, 1]) + bytes(9) + b'\x00'),  # normal + 9 byte desc + access_sel
            (0xC1, "GetResponse",
             lambda t: bytes([t, 1, 0, 0, 0, 1, 0]) + encode_data(0, "integer")),  # normal + result=0 + int data
            (0xC2, "SetRequest",
             lambda t: bytes([t, 1, 0, 0, 0, 1]) + bytes(9) + b'\x00' + encode_data(0, "integer")),
            (0xC3, "SetResponse",
             lambda t: bytes([t, 1, 0, 0, 0, 1, 0])),  # normal + result=0
            (0xC4, "EventNotification",
             lambda t: bytes([t]) + bytes(9) + encode_data(0, "integer")),  # 9 byte desc + value
            (0xC7, "ActionRequest",
             lambda t: bytes([t, 1, 0, 0, 0, 1]) + bytes(9) + encode_data(None, "null-data")),
            (0xC8, "ActionResponse",
             lambda t: bytes([t, 1, 0, 0, 0, 1, 0]) + encode_data(None, "null-data")),
            (0xDA, "GeneralCiphering",
             lambda t: bytes([t, 0x08]) + bytes(8) + bytes([0])),  # 8-byte system title + empty data
            (0xDB, "GeneralGloCiphering",
             lambda t: bytes([t, 0x08]) + bytes(8) + bytes([0])),  # 8-byte system title + empty data
        ]

        for tag, expected_type, data_builder in test_cases:
            data = data_builder(tag)
            result = parse_apdu(data)
            self.assertEqual(result.type_name, expected_type,
                             f"Tag 0x{tag:02X}: expected {expected_type}, got {result.type_name}")
            self.assertEqual(result.tag, tag)

    def test_parse_apdu_returns_correct_types(self):
        """测试parse_apdu返回正确的模型类型"""
        # GetRequest
        req = build_get_request({"get_type": 1, "class_id": 3, "obis": "1-0:1.8.0.255"})
        result = parse_apdu(req)
        self.assertIsInstance(result, GetRequestAPDU)

        # GetResponse
        resp = build_get_response({"result_code": 0, "value": 123, "data_type": "long-unsigned"})
        result = parse_apdu(resp)
        self.assertIsInstance(result, GetResponseAPDU)

        # DataNotification
        dn = build_data_notification({"items": [
            {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2,
             "value": 100, "data_type": "long-unsigned"}
        ]})
        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)


class TestEdgeCases(unittest.TestCase):
    """边界条件和错误处理测试"""

    def test_ber_encode_unknown_type(self):
        """测试编码未知类型"""
        with self.assertRaises(ValueError):
            encode_data(123, "nonexistent-type")

    def test_ber_decode_insufficient_data(self):
        """测试解码数据不足"""
        # 不完整的double-long (只给了tag和length，没有数据)
        with self.assertRaises(ValueError):
            decode_data(b"\x05\x04\x00\x00")

    def test_ber_decode_bad_length_long(self):
        """测试解码错误的长格式长度"""
        # tag + long length (2 bytes), 但数据不足
        with self.assertRaises(ValueError):
            decode_data(b"\x09\x82\x01\x00\x00")  # 声明256字节，实际只有1字节

    def test_get_request_with_list_empty_error(self):
        """测试空attribute_list的GetRequest构建"""
        with self.assertRaises(ValueError):
            build_get_request({
                "get_type": 3,
                "invoke_id": 1,
                "attribute_list": [],
            })

    def test_get_response_with_list_empty_error(self):
        """测试空results的GetResponse构建"""
        with self.assertRaises(ValueError):
            build_get_response({
                "get_type": 3,
                "invoke_id": 1,
                "results": [],
            })

    def test_large_octet_string_roundtrip(self):
        """测试大octet-string往返"""
        # 超过127字节，触发长格式长度编码
        data = bytes(range(200))
        enc = encode_data(data, "octet-string")
        # 验证长度编码是长格式
        self.assertEqual(enc[1], 0x81)  # 1字节长度值
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(val, data)
        self.assertEqual(tn, "octet-string")

    def test_complex_nested_structure(self):
        """测试复杂嵌套结构"""
        # 模拟一个profile generic buffer entry
        entry = [
            ({"year": 2024, "month": 1, "day": 1, "weekday": 1,
              "hour": 0, "minute": 0, "second": 0, "hundredths": 0,
              "deviation": 0, "status": 0}, "date-time"),
            (12345, "double-long-unsigned"),
            (67890, "double-long-unsigned"),
        ]

        entries = [entry for _ in range(3)]
        enc = encode_data(entries, "array")
        val, off, tn = decode_data(enc, 0)
        self.assertEqual(tn, "array")
        self.assertEqual(len(val), 3)
        self.assertEqual(len(val[0]), 3)  # 每个entry有3个字段
        self.assertIsInstance(val[0][0], dict)  # date-time
        self.assertIn("year", val[0][0])
        self.assertEqual(val[0][1], 12345)
        self.assertEqual(val[0][2], 67890)


# ============================================================================
# 真实场景测试
# ============================================================================

class TestRealWorldScenarios(unittest.TestCase):
    """真实场景测试"""

    def test_full_data_notification_workflow(self):
        """测试完整的DataNotification工作流"""
        # 模拟电表上报数据
        notification_items = [
            # 电压
            {"class_id": 3, "obis": "1-0:32.7.0.255", "attribute_id": 2,
             "value": 230.5, "data_type": "float64"},
            # 电流
            {"class_id": 3, "obis": "1-0:31.7.0.255", "attribute_id": 2,
             "value": 10.2, "data_type": "float64"},
            # 有功电能
            {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2,
             "value": 12345678, "data_type": "double-long-unsigned"},
            # 表号
            {"class_id": 8, "obis": "0-0:96.1.0.255", "attribute_id": 2,
             "value": "METER-001", "data_type": "visible-string"},
        ]

        # 构建通知
        dn = build_data_notification({
            "invoke_id": 12345,
            "datetime": {
                "year": 2024, "month": 6, "day": 15, "weekday": 6,
                "hour": 14, "minute": 30, "second": 0, "hundredths": 0,
                "deviation": 480, "status": 1,
            },
            "items": notification_items,
        })

        # 解析通知
        result = parse_apdu(dn)
        self.assertIsInstance(result, DataNotificationAPDU)
        self.assertEqual(result.invoke_id, 12345)
        self.assertEqual(result.item_count, 4)

        # 验证各数据项
        self.assertAlmostEqual(result.items[0].value, 230.5, places=5)
        self.assertAlmostEqual(result.items[1].value, 10.2, places=5)
        self.assertEqual(result.items[2].value, 12345678)
        self.assertEqual(result.items[3].value, "METER-001")

        # 验证datetime
        self.assertEqual(result.datetime["year"], 2024)
        self.assertEqual(result.datetime["month"], 6)
        self.assertEqual(result.datetime["day"], 15)
        self.assertEqual(result.datetime["hour"], 14)

        # 发送确认
        confirm = build_data_notification_confirm({
            "confirm_type": "event",
            "invoke_id": 12345,
            "result": 0,
            "class_id": 8,
            "obis": "0-0:96.11.8.255",
            "attribute_id": 1,
            "value": 0,
            "data_type": "unsigned",
        })

        self.assertEqual(confirm[0], 0xC4)

    def test_full_get_request_response_workflow(self):
        """测试完整的Get请求/响应工作流"""
        # 客户端发送Get-Request-With-List
        req = build_get_request({
            "get_type": 3,
            "invoke_id": 42,
            "attribute_list": [
                {"class_id": 3, "obis": "1-0:1.8.0.255", "attribute_id": 2},
                {"class_id": 3, "obis": "1-0:2.8.0.255", "attribute_id": 2},
                {"class_id": 1, "obis": "0-0:1.0.0.255", "attribute_id": 2},
            ]
        })

        # 服务器端解析请求
        parsed_req = parse_apdu(req)
        self.assertEqual(len(parsed_req.attribute_list), 3)

        # 服务器构建响应
        resp = build_get_response({
            "get_type": 3,
            "invoke_id": 42,
            "results": [
                {"success": True, "value": 10000, "data_type": "double-long-unsigned"},
                {"success": True, "value": 5000, "data_type": "double-long-unsigned"},
                {"success": True, "value": "OK", "data_type": "visible-string"},
            ]
        })

        # 客户端解析响应
        parsed_resp = parse_apdu(resp)
        self.assertEqual(parsed_resp.get_type, 3)
        self.assertEqual(parsed_resp.invoke_id, 42)
        self.assertEqual(len(parsed_resp.results), 3)
        self.assertEqual(parsed_resp.results[0]["value"], 10000)
        self.assertEqual(parsed_resp.results[1]["value"], 5000)
        self.assertEqual(parsed_resp.results[2]["value"], "OK")


if __name__ == "__main__":
    unittest.main()
