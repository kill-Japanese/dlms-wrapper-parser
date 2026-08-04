"""
Wrapper层单元测试

测试内容:
1. parse_wpd - 解析Wrapper帧头
2. build_wpd - 构建Wrapper帧
3. 往返测试 - 构建后再解析
4. 边界条件测试
"""
import unittest
import struct

from app.services.wrapper import (
    parse_wpd,
    build_wpd,
    is_wrapper_frame,
    WRAPPER_HEADER_LENGTH,
    WPORT_CLIENT,
    WPORT_METER,
)
from app.utils.hex_utils import hex_to_bytes, bytes_to_hex


class TestWrapperParsing(unittest.TestCase):
    """Wrapper层解析测试"""

    def test_parse_basic_frame(self):
        """测试基本的Wrapper帧解析"""
        # 构造一个简单的Wrapper帧
        # version=1, src=1, dst=16, length=4, payload=0x12345678
        payload = bytes([0x12, 0x34, 0x56, 0x78])
        frame = build_wpd(payload, src_wport=1, dst_wport=16, version=1)

        # 解析
        result = parse_wpd(frame)

        self.assertEqual(result.version, 1)
        self.assertEqual(result.src_wport, 1)
        self.assertEqual(result.dst_wport, 16)
        self.assertEqual(result.data_length, 4)
        self.assertEqual(result.payload_hex, "12345678")

    def test_parse_known_frame(self):
        """测试已知的DLMS Wrapper帧"""
        # 一个典型的DLMS Wrapper帧头部示例
        # 0001 0001 0010 000f = version=1, src=1, dst=16, length=15
        hex_frame = "000100010010000f" + "c001c0010000200502000800000000"  # 15字节载荷
        data = hex_to_bytes(hex_frame)

        result = parse_wpd(data)

        self.assertEqual(result.version, 1)
        self.assertEqual(result.src_wport, 1)
        self.assertEqual(result.dst_wport, 16)
        self.assertEqual(result.data_length, 15)

    def test_parse_empty_payload(self):
        """测试空载荷的Wrapper帧"""
        frame = build_wpd(b"", src_wport=1, dst_wport=16)
        result = parse_wpd(frame)

        self.assertEqual(result.data_length, 0)
        self.assertEqual(result.payload_hex, "")

    def test_parse_too_short_data(self):
        """测试数据不足的情况"""
        # 少于8字节
        with self.assertRaises(ValueError):
            parse_wpd(b"\x00\x01\x00")

    def test_parse_insufficient_payload(self):
        """测试载荷不完整的情况"""
        # 头部声明有10字节载荷，但实际只有5字节
        header = struct.pack(">HHHH", 1, 1, 16, 10)
        incomplete = header + b"\x00\x01\x02\x03\x04"  # 只有5字节载荷

        with self.assertRaises(ValueError):
            parse_wpd(incomplete)


class TestWrapperBuilding(unittest.TestCase):
    """Wrapper层构建测试"""

    def test_build_basic_frame(self):
        """测试基本的Wrapper帧构建"""
        payload = bytes([0x01, 0x02, 0x03, 0x04])
        frame = build_wpd(payload, src_wport=1, dst_wport=16, version=1)

        # 验证总长度
        self.assertEqual(len(frame), WRAPPER_HEADER_LENGTH + len(payload))

        # 解析回来验证
        result = parse_wpd(frame)
        self.assertEqual(result.version, 1)
        self.assertEqual(result.src_wport, 1)
        self.assertEqual(result.dst_wport, 16)
        self.assertEqual(result.data_length, len(payload))
        self.assertEqual(hex_to_bytes(result.payload_hex), payload)

    def test_build_default_ports(self):
        """测试使用默认端口构建"""
        payload = b"\x00" * 20
        frame = build_wpd(payload)

        result = parse_wpd(frame)
        self.assertEqual(result.src_wport, WPORT_CLIENT)
        self.assertEqual(result.dst_wport, WPORT_METER)

    def test_build_large_payload(self):
        """测试大载荷构建"""
        payload = bytes(range(256))  # 256字节
        frame = build_wpd(payload)

        result = parse_wpd(frame)
        self.assertEqual(result.data_length, 256)
        self.assertEqual(len(hex_to_bytes(result.payload_hex)), 256)


class TestWrapperRoundtrip(unittest.TestCase):
    """Wrapper层往返测试"""

    def test_roundtrip_simple(self):
        """简单往返测试"""
        original_payload = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        frame = build_wpd(original_payload, src_wport=40, dst_wport=1, version=1)
        parsed = parse_wpd(frame)

        self.assertEqual(hex_to_bytes(parsed.payload_hex), original_payload)
        self.assertEqual(parsed.src_wport, 40)
        self.assertEqual(parsed.dst_wport, 1)

    def test_roundtrip_various_sizes(self):
        """测试不同大小的载荷往返"""
        for size in [0, 1, 2, 4, 8, 16, 32, 100, 255, 1000]:
            payload = bytes([i % 256 for i in range(size)])
            frame = build_wpd(payload)
            parsed = parse_wpd(frame)
            self.assertEqual(
                hex_to_bytes(parsed.payload_hex),
                payload,
                f"Roundtrip failed for size {size}"
            )


class TestWrapperDetection(unittest.TestCase):
    """Wrapper帧检测测试"""

    def test_is_wrapper_frame_valid(self):
        """测试有效的Wrapper帧检测"""
        frame = build_wpd(b"\x00" * 10)
        self.assertTrue(is_wrapper_frame(frame))

    def test_is_wrapper_frame_too_short(self):
        """测试太短的数据"""
        self.assertFalse(is_wrapper_frame(b"\x00\x01"))

    def test_is_wrapper_frame_wrong_version(self):
        """测试版本号不正确的情况"""
        # 构造一个version=99的帧
        header = struct.pack(">HHHH", 99, 1, 16, 4)
        frame = header + b"\x00\x00\x00\x00"
        self.assertFalse(is_wrapper_frame(frame))


if __name__ == "__main__":
    unittest.main()
