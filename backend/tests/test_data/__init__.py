"""
测试数据模块

包含DLMS协议各层的测试数据生成函数和预定义测试帧。
"""
from .test_frames import (
    # 测试密钥和参数
    TEST_BLOCK_CIPHER_KEY,
    TEST_SYSTEM_TITLE,
    TEST_INVOCATION_COUNTER,
    TEST_SECURITY_CONTROL_AUTH_ENC,
    TEST_SECURITY_CONTROL_AUTH_ENC_COMP,

    # DataNotification APDU 构造
    build_data_notification_apdu,
    get_data_notification_plain_apdu,

    # Wrapper帧
    get_plain_wrapper_frame,
    get_encrypted_wrapper_frame,
    get_encrypted_compressed_wrapper_frame,
    get_get_request_wrapper_frame,
    get_get_response_wrapper_frame,

    # 原始APDU数据
    get_plain_data_notification_apdu,
    get_get_request_apdu,
    get_get_response_apdu,

    # 辅助函数
    hex_str,
    byte_str,
    generate_test_frame,
)

__all__ = [
    "TEST_BLOCK_CIPHER_KEY",
    "TEST_SYSTEM_TITLE",
    "TEST_INVOCATION_COUNTER",
    "TEST_SECURITY_CONTROL_AUTH_ENC",
    "TEST_SECURITY_CONTROL_AUTH_ENC_COMP",
    "build_data_notification_apdu",
    "get_data_notification_plain_apdu",
    "get_plain_wrapper_frame",
    "get_encrypted_wrapper_frame",
    "get_encrypted_compressed_wrapper_frame",
    "get_get_request_wrapper_frame",
    "get_get_response_wrapper_frame",
    "get_plain_data_notification_apdu",
    "get_get_request_apdu",
    "get_get_response_apdu",
    "hex_str",
    "byte_str",
    "generate_test_frame",
]
