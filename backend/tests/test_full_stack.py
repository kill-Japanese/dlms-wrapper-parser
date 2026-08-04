"""
完整协议栈集成测试

测试完整的DLMS协议栈解包/打包流程：
- 测试1: 明文DataNotification解包（Wrapper -> APDU）
- 测试2: 加密DataNotification解包（Wrapper -> 解密 -> APDU）
- 测试3: 加密+压缩DataNotification解包（Wrapper -> 解密 -> 解压 -> APDU）
- 测试4: GetRequest打包（APDU -> Wrapper）
- 测试5: 往返测试：打包 -> 解包，验证数据一致性
"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.dlms_stack import parse_frame, build_frame
from app.services.wrapper import parse_wpd, build_wpd
from app.services.ciphering import parse_ciphered, build_ciphered
from app.services.compression import compress, decompress, V44_AVAILABLE
from app.services.apdu_parser import parse_apdu, build_apdu
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes

from tests.test_data.test_frames import (
    get_plain_wrapper_frame,
    get_encrypted_wrapper_frame,
    get_encrypted_compressed_wrapper_frame,
    get_get_request_wrapper_frame,
    get_get_response_wrapper_frame,
    get_plain_data_notification_apdu,
    get_get_request_apdu,
    get_get_response_apdu,
    build_data_notification_apdu,
    TEST_BLOCK_CIPHER_KEY,
    TEST_SYSTEM_TITLE,
    TEST_INVOCATION_COUNTER,
)


class TestPlainDataNotificationUnpack(unittest.TestCase):
    """测试1: 明文DataNotification解包（Wrapper -> APDU）"""

    def test_wrapper_layer_parse(self):
        """测试Wrapper层解析"""
        frame = get_plain_wrapper_frame()
        result = parse_wpd(frame)

        self.assertEqual(result.version, 1)
        self.assertEqual(result.src_wport, 1)
        self.assertEqual(result.dst_wport, 16)
        self.assertGreater(result.data_length, 0)
        self.assertEqual(len(hex_to_bytes(result.payload_hex)), result.data_length)

    def test_apdu_layer_parse(self):
        """测试APDU层解析（DataNotification）"""
        frame = get_plain_wrapper_frame()
        wrapper = parse_wpd(frame)
        payload = hex_to_bytes(wrapper.payload_hex)

        apdu = parse_apdu(payload)

        self.assertEqual(apdu.tag, 15)  # DataNotification
        self.assertEqual(apdu.type_name, "DataNotification")
        self.assertIsNotNone(apdu.invoke_id)

    def test_full_stack_parse_plain(self):
        """测试完整协议栈解析明文帧"""
        frame = get_plain_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(hex_data)

        # 验证Wrapper层
        self.assertIsNotNone(result.wrapper)
        self.assertEqual(result.wrapper.version, 1)

        # 验证APDU层
        self.assertIsNotNone(result.apdu)
        self.assertEqual(result.apdu["tag"], 15)
        self.assertEqual(result.apdu["type_name"], "DataNotification")

        # 验证无加密层
        self.assertIsNone(result.ciphering)

        # 验证无错误
        self.assertEqual(len(result.errors), 0,
                         f"解析错误: {result.errors}")

    def test_parse_result_has_logs(self):
        """测试解析结果包含日志"""
        frame = get_plain_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(hex_data)

        self.assertGreater(len(result.parse_logs), 0)
        # 验证日志包含各层信息
        steps = [log.step for log in result.parse_logs]
        self.assertIn("input", steps)
        self.assertIn("wrapper", steps)
        self.assertIn("apdu", steps)


class TestEncryptedDataNotificationUnpack(unittest.TestCase):
    """测试2: 加密DataNotification解包（Wrapper -> 解密 -> APDU）"""

    def test_wrapper_layer_parse_encrypted(self):
        """测试加密帧的Wrapper层解析"""
        frame = get_encrypted_wrapper_frame()
        result = parse_wpd(frame)

        self.assertEqual(result.version, 1)
        self.assertEqual(result.src_wport, 1)
        self.assertEqual(result.dst_wport, 16)
        self.assertGreater(result.data_length, 0)

    def test_cipher_layer_decrypt(self):
        """测试加密层解密"""
        frame = get_encrypted_wrapper_frame()
        wrapper = parse_wpd(frame)
        payload = hex_to_bytes(wrapper.payload_hex)

        plaintext, cipher_frame = parse_ciphered(payload, TEST_BLOCK_CIPHER_KEY)

        self.assertTrue(cipher_frame.decrypt_success)
        self.assertGreater(len(plaintext), 0)
        self.assertEqual(cipher_frame.system_title, bytes_to_hex(TEST_SYSTEM_TITLE))
        self.assertEqual(cipher_frame.invocation_counter, TEST_INVOCATION_COUNTER)

        # 验证解密后是有效的DataNotification APDU
        apdu = parse_apdu(plaintext)
        self.assertEqual(apdu.tag, 15)  # DataNotification

    def test_full_stack_parse_encrypted_with_key(self):
        """测试完整协议栈解析加密帧（带密钥）"""
        frame = get_encrypted_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(
            hex_data,
            encryption_key=bytes_to_hex(TEST_BLOCK_CIPHER_KEY),
            system_title=bytes_to_hex(TEST_SYSTEM_TITLE),
        )

        # 验证Wrapper层
        self.assertIsNotNone(result.wrapper)

        # 验证加密层
        self.assertIsNotNone(result.ciphering)
        self.assertTrue(result.ciphering.decrypt_success)
        self.assertEqual(result.ciphering.cipher_info.encrypted, True)
        self.assertEqual(result.ciphering.cipher_info.authenticated, True)

        # 验证APDU层（解密后解析成功）
        self.assertIsNotNone(result.apdu)
        self.assertEqual(result.apdu["tag"], 15)
        self.assertEqual(result.apdu["type_name"], "DataNotification")

        # 验证无错误
        self.assertEqual(len(result.errors), 0,
                         f"解析错误: {result.errors}")

    def test_full_stack_parse_encrypted_without_key(self):
        """测试完整协议栈解析加密帧（无密钥）"""
        frame = get_encrypted_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(hex_data)

        # 验证加密层结构仍然被解析
        self.assertIsNotNone(result.ciphering)
        self.assertFalse(result.ciphering.decrypt_success)

        # 无密钥时APDU不应被解析（因为无法解密）
        # 注意：根据实现，无密钥时可能直接返回，不解析APDU

    def test_full_stack_parse_encrypted_wrong_key(self):
        """测试完整协议栈解析加密帧（错误密钥）"""
        frame = get_encrypted_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        # 使用错误的密钥
        wrong_key = "00000000000000000000000000000000"

        result = parse_frame(
            hex_data,
            encryption_key=wrong_key,
            system_title=bytes_to_hex(TEST_SYSTEM_TITLE),
        )

        # 验证加密层解析成功但解密失败
        self.assertIsNotNone(result.ciphering)
        self.assertFalse(result.ciphering.decrypt_success)

        # 解密失败应该有错误
        self.assertTrue(any("解密失败" in e for e in result.errors) or len(result.errors) > 0)


class TestCompressedDataNotificationUnpack(unittest.TestCase):
    """测试3: 加密+压缩DataNotification解包（Wrapper -> 解密 -> 解压 -> APDU）"""

    @unittest.skipUnless(V44_AVAILABLE, "V.44模块不可用")
    def test_compression_roundtrip(self):
        """测试V.44压缩/解压往返"""
        original_data = build_data_notification_apdu()
        compressed = compress(original_data)
        decompressed = decompress(compressed)

        self.assertEqual(decompressed, original_data)
        # 验证压缩比（数据量足够时应该有压缩效果）
        self.assertLess(len(compressed), len(original_data) + 10)  # 允许少量开销

    @unittest.skipUnless(V44_AVAILABLE, "V.44模块不可用")
    def test_decrypt_then_decompress(self):
        """测试先解密再解压"""
        frame = get_encrypted_compressed_wrapper_frame()
        wrapper = parse_wpd(frame)
        payload = hex_to_bytes(wrapper.payload_hex)

        # 解密
        plaintext, cipher_frame = parse_ciphered(payload, TEST_BLOCK_CIPHER_KEY)
        self.assertTrue(cipher_frame.decrypt_success)
        self.assertTrue(cipher_frame.cipher_info.compressed)

        # 解压
        decompressed = decompress(plaintext)
        self.assertGreater(len(decompressed), 0)

        # 验证解压后是有效的DataNotification APDU
        apdu = parse_apdu(decompressed)
        self.assertEqual(apdu.tag, 15)  # DataNotification

    @unittest.skipUnless(V44_AVAILABLE, "V.44模块不可用")
    def test_full_stack_parse_compressed(self):
        """测试完整协议栈解析加密压缩帧"""
        frame = get_encrypted_compressed_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(
            hex_data,
            encryption_key=bytes_to_hex(TEST_BLOCK_CIPHER_KEY),
            system_title=bytes_to_hex(TEST_SYSTEM_TITLE),
        )

        # 验证Wrapper层
        self.assertIsNotNone(result.wrapper)

        # 验证加密层
        self.assertIsNotNone(result.ciphering)
        self.assertTrue(result.ciphering.decrypt_success)
        self.assertTrue(result.ciphering.cipher_info.compressed)

        # 验证压缩层
        self.assertIsNotNone(result.compression)
        self.assertEqual(result.compression["algorithm"], "V.44")
        self.assertGreater(result.compression["original_size"], 0)
        self.assertGreater(result.compression["compressed_size"], 0)

        # 验证APDU层
        self.assertIsNotNone(result.apdu)
        self.assertEqual(result.apdu["tag"], 15)
        self.assertEqual(result.apdu["type_name"], "DataNotification")

        # 验证无错误
        self.assertEqual(len(result.errors), 0,
                         f"解析错误: {result.errors}")


class TestGetRequestPack(unittest.TestCase):
    """测试4: GetRequest打包（APDU -> Wrapper）"""

    def test_build_get_request_apdu(self):
        """测试构建GetRequest APDU"""
        apdu = build_apdu("getrequest", {
            "get_type": 1,
            "invoke_id": 1,
            "class_id": 3,
            "obis": "0-0:1.0.0.255",
            "attribute_id": 2,
        })

        self.assertEqual(apdu[0], 192)  # GetRequest tag
        self.assertEqual(len(apdu), 16)  # 1(tag) + 1(get_type) + 4(invoke_id) + 9(descriptor) + 1(access_selection)

    def test_build_frame_get_request(self):
        """测试完整组帧流程（GetRequest）"""
        result = build_frame(
            apdu_type="getrequest",
            params={
                "class_id": 3,
                "obis": "0-0:1.0.0.255",
                "attribute_id": 2,
            },
            src_wport=1,
            dst_wport=16,
        )

        self.assertTrue(result["success"])
        self.assertGreater(result["frame_length"], 0)
        self.assertGreater(len(result["hex_data"]), 0)

        # 验证生成的帧可以被解析
        parsed = parse_frame(result["hex_data"])
        self.assertIsNotNone(parsed.wrapper)
        self.assertIsNotNone(parsed.apdu)
        self.assertEqual(parsed.apdu["tag"], 192)
        self.assertEqual(parsed.apdu["type_name"], "GetRequest")

    def test_get_request_wrapper_parse(self):
        """测试GetRequest Wrapper帧解析"""
        frame = get_get_request_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(hex_data)

        self.assertIsNotNone(result.wrapper)
        self.assertIsNotNone(result.apdu)
        self.assertEqual(result.apdu["tag"], 192)
        self.assertEqual(result.apdu["type_name"], "GetRequest")
        self.assertEqual(result.apdu["class_id"], 3)
        self.assertEqual(result.apdu["obis"], "0-0:1.0.0.255")
        self.assertEqual(result.apdu["attribute_id"], 2)

    def test_get_response_wrapper_parse(self):
        """测试GetResponse Wrapper帧解析"""
        frame = get_get_response_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result = parse_frame(hex_data)

        self.assertIsNotNone(result.wrapper)
        self.assertIsNotNone(result.apdu)
        self.assertEqual(result.apdu["tag"], 193)
        self.assertEqual(result.apdu["type_name"], "GetResponse")
        self.assertEqual(result.apdu["result"], "success")
        self.assertEqual(result.apdu["data_type"], "double-long-unsigned")
        self.assertEqual(result.apdu["value"], 230000)


class TestRoundtrip(unittest.TestCase):
    """测试5: 往返测试：打包 -> 解包，验证数据一致性"""

    def test_get_request_roundtrip(self):
        """GetRequest往返测试：打包 -> 解包"""
        # 打包
        build_result = build_frame(
            apdu_type="getrequest",
            params={
                "get_type": 1,
                "invoke_id": 42,
                "class_id": 3,
                "obis": "1-0:1.8.0.255",
                "attribute_id": 2,
            },
            src_wport=1,
            dst_wport=16,
        )

        self.assertTrue(build_result["success"])

        # 解包
        parse_result = parse_frame(build_result["hex_data"])

        # 验证数据一致性
        self.assertIsNotNone(parse_result.wrapper)
        self.assertEqual(parse_result.wrapper.src_wport, 1)
        self.assertEqual(parse_result.wrapper.dst_wport, 16)

        self.assertIsNotNone(parse_result.apdu)
        self.assertEqual(parse_result.apdu["tag"], 192)
        self.assertEqual(parse_result.apdu["get_type"], 1)
        self.assertEqual(parse_result.apdu["invoke_id"], 42)
        self.assertEqual(parse_result.apdu["class_id"], 3)
        self.assertEqual(parse_result.apdu["obis"], "1-0:1.8.0.255")
        self.assertEqual(parse_result.apdu["attribute_id"], 2)

    def test_wrapper_roundtrip_arbitrary_payload(self):
        """Wrapper层任意载荷往返测试"""
        test_payloads = [
            b"",
            b"\x00",
            b"\x00\x01\x02\x03",
            bytes(range(256)),
            b"\xff" * 1000,
        ]

        for payload in test_payloads:
            with self.subTest(payload_len=len(payload)):
                frame = build_wpd(payload, src_wport=40, dst_wport=1)
                parsed = parse_wpd(frame)
                self.assertEqual(hex_to_bytes(parsed.payload_hex), payload)
                self.assertEqual(parsed.src_wport, 40)
                self.assertEqual(parsed.dst_wport, 1)

    def test_cipher_roundtrip(self):
        """加密层往返测试：加密 -> 解密"""
        test_data = get_plain_data_notification_apdu()

        # 加密
        encrypted = build_ciphered(
            apdu=test_data,
            key=TEST_BLOCK_CIPHER_KEY,
            system_title=TEST_SYSTEM_TITLE,
            invocation_counter=TEST_INVOCATION_COUNTER,
            encrypted=True,
            authenticated=True,
            compressed=False,
        )

        # 解密
        decrypted, cipher_info = parse_ciphered(encrypted, TEST_BLOCK_CIPHER_KEY)

        self.assertTrue(cipher_info.decrypt_success)
        self.assertEqual(decrypted, test_data)

    @unittest.skipUnless(V44_AVAILABLE, "V.44模块不可用")
    def test_full_compress_encrypt_roundtrip(self):
        """完整往返测试：压缩 -> 加密 -> 解密 -> 解压"""
        original_data = build_data_notification_apdu(
            invoke_id=12345,
            data_items=[
                (3, "1-0:1.8.0.255", 2, "double-long-unsigned", 12345678),
                (3, "1-0:2.8.0.255", 2, "double-long-unsigned", 87654321),
                (1, "0-0:96.1.0.255", 2, "octet-string", b"TEST_SERIAL_123"),
            ],
        )

        # 压缩
        compressed = compress(original_data)

        # 加密（设置压缩标志）
        encrypted = build_ciphered(
            apdu=compressed,
            key=TEST_BLOCK_CIPHER_KEY,
            system_title=TEST_SYSTEM_TITLE,
            invocation_counter=100,
            encrypted=True,
            authenticated=True,
            compressed=True,
        )

        # 解密
        decrypted, cipher_info = parse_ciphered(encrypted, TEST_BLOCK_CIPHER_KEY)
        self.assertTrue(cipher_info.decrypt_success)
        self.assertTrue(cipher_info.cipher_info.compressed)

        # 解压
        decompressed = decompress(decrypted)

        # 验证数据一致性
        self.assertEqual(decompressed, original_data)

        # 验证APDU解析
        apdu = parse_apdu(decompressed)
        self.assertEqual(apdu.tag, 15)
        self.assertEqual(apdu.invoke_id, 12345)


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def test_empty_input(self):
        """测试空输入"""
        result = parse_frame("")
        self.assertGreater(len(result.errors), 0)

    def test_invalid_hex(self):
        """测试无效的十六进制输入"""
        result = parse_frame("ZZXXYY")
        self.assertGreater(len(result.errors), 0)

    def test_short_frame(self):
        """测试过短的帧"""
        result = parse_frame("0001")  # 只有2字节
        # 短于Wrapper头，应作为APDU处理或报错
        self.assertIsNotNone(result)

    def test_get_response_roundtrip_consistency(self):
        """测试GetResponse解析一致性"""
        frame = get_get_response_wrapper_frame()
        hex_data = bytes_to_hex(frame)

        result1 = parse_frame(hex_data)
        result2 = parse_frame(hex_data)

        # 两次解析结果应一致（frame_id和timestamp除外）
        self.assertEqual(result1.wrapper.data_length, result2.wrapper.data_length)
        self.assertEqual(result1.apdu["value"], result2.apdu["value"])
        self.assertEqual(result1.apdu["data_type"], result2.apdu["data_type"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
