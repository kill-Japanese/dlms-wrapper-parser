"""
APDU模型定义

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
from pydantic import BaseModel, Field
from typing import Optional, Any, List


class CosemAttributeDescriptor(BaseModel):
    """COSEM属性描述符"""

    class_id: int = Field(description="类ID (Class ID)")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    obis_bytes: bytes = Field(default=b"", description="OBIS码原始字节")
    attribute_id: int = Field(description="属性ID")


class CosemDataItem(BaseModel):
    """COSEM数据项模型（用于DataNotification等）"""

    class_id: int = Field(description="类ID (Class ID)")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    obis_bytes: bytes = Field(default=b"", description="OBIS码原始字节")
    attribute_id: int = Field(description="属性ID")
    data_type: str = Field(default="", description="数据类型")
    value: Any = Field(default=None, description="数据值")
    raw_hex: str = Field(default="", description="原始十六进制数据")


class CosemMethodDescriptor(BaseModel):
    """COSEM方法描述符"""

    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码")
    method_id: int = Field(description="方法ID")


class APDUBase(BaseModel):
    """APDU基础模型"""

    tag: int = Field(description="APDU标签")
    type_name: str = Field(description="APDU类型名称")
    raw_hex: str = Field(default="", description="原始十六进制数据")


class DataNotificationAPDU(APDUBase):
    """
    DataNotification APDU (tag=0x0F, 15)

    DataNotification 是DLMS中的一种通知机制，表端主动上报数据。
    格式:
    - tag (1 byte) = 0x0F
    - long-invoke-id-and-priority (4 bytes)
    - datetime (可选, date-time类型): 时间戳
    - notification-body: array of structure
      每个structure包含:
        - cosem_attribute_descriptor (9 bytes): class_id(2)+obis(6)+attribute_id(1)
        - value: Data (BER编码)
    """

    type_name: str = "DataNotification"
    invoke_id: Optional[int] = Field(default=None, description="调用ID (long-invoke-id-and-priority)")
    datetime: Optional[dict] = Field(default=None, description="日期时间（解析后的dict）")
    datetime_raw: Optional[str] = Field(default=None, description="日期时间原始十六进制")
    items: List[CosemDataItem] = Field(default_factory=list, description="数据项列表")
    notification_body_hex: str = Field(default="", description="通知体原始数据")
    item_count: int = Field(default=0, description="数据项数量")
    push_setup_version: int = Field(default=0, description="Push Setup (Class 40) 版本 (0-3)")
    push_setup_version_name: str = Field(default="v0", description="Push Setup 版本名称")
    push_object_list: List[dict] = Field(default_factory=list, description="Push object list (Class 40 属性2的解析结果)")
    has_class40_template: bool = Field(default=False, description="是否包含Class 40属性2作为模版")


class DataNotificationConfirmAPDU(APDUBase):
    """
    DataNotification Confirm APDU

    注意: DLMS标准中DataNotification本身是单向的（confirmed=false），
    不需要确认。但在实际应用中，有时需要一个确认响应来告知发送方数据已收到。

    这里实现的是一个通用的确认APDU，可以用于:
    1. 自定义确认帧（如用EventNotification的响应形式）
    2. 或简单的ACK帧
    """

    type_name: str = "DataNotificationConfirm"
    invoke_id: int = Field(default=0, description="调用ID（对应原通知的invoke_id）")
    result: int = Field(default=0, description="结果: 0=成功, 其他=错误码")
    confirmed: bool = Field(default=False, description="是否为确认模式")


class GetRequestAPDU(APDUBase):
    """
    GetRequest APDU (tag=0xC0, 192)

    Get-Request 类型:
    - 1: Get-Request-Normal - 读取单个属性
    - 2: Get-Request-Next - 读取下一个（用于块传输）
    - 3: Get-Request-With-List - 一次读取多个属性

    Get-Request-Normal 格式:
    - tag (1 byte) = 0xC0
    - get-type (1 byte) = 1
    - invoke-id-and-priority (4 bytes)
    - cosem_attribute_descriptor (9 bytes)
    - access-selection (可选)
    """

    type_name: str = "GetRequest"
    get_type: int = Field(default=1, description="Get请求类型 (1=normal, 2=next, 3=with-list)")
    invoke_id: int = Field(default=0, description="调用ID")
    class_id: Optional[int] = Field(default=None, description="类ID (type=1时)")
    obis: Optional[str] = Field(default=None, description="OBIS码 (type=1时)")
    attribute_id: Optional[int] = Field(default=None, description="属性ID (type=1时)")
    attribute_list: List[CosemAttributeDescriptor] = Field(
        default_factory=list, description="属性列表 (type=3 with-list时)"
    )
    access_selection: int = Field(default=0, description="访问选择标志")
    block_number: Optional[int] = Field(default=None, description="块号 (type=2 next时)")


class GetResponseAPDU(APDUBase):
    """
    GetResponse APDU (tag=0xC1, 193)

    Get-Response 类型与Get-Request对应:
    - 1: Get-Response-Normal
    - 2: Get-Response-Next (with datablock)
    - 3: Get-Response-With-List

    结果标签:
    - 0: data (成功，后跟数据)
    - 1: datablock (块传输)
    - other: 错误码
    """

    type_name: str = "GetResponse"
    get_type: int = Field(default=1, description="Get响应类型 (1/2/3)")
    invoke_id: int = Field(default=0, description="调用ID")
    result: str = Field(default="", description="结果描述")
    result_code: int = Field(default=0, description="结果码")
    data_type: Optional[str] = Field(default=None, description="数据类型 (单个结果时)")
    value: Any = Field(default=None, description="返回值 (单个结果时)")
    results: List[dict] = Field(default_factory=list, description="结果列表 (with-list时)")
    is_block: bool = Field(default=False, description="是否为块传输")
    block_number: Optional[int] = Field(default=None, description="块号")
    last_block: bool = Field(default=False, description="是否为最后一块")
    raw_data_hex: str = Field(default="", description="原始数据十六进制")


class SetRequestAPDU(APDUBase):
    """SetRequest APDU (tag=0xC2, 194)"""

    type_name: str = "SetRequest"
    set_type: int = Field(default=1, description="Set请求类型")
    invoke_id: int = Field(default=0, description="调用ID")
    class_id: Optional[int] = Field(default=None, description="类ID")
    obis: Optional[str] = Field(default=None, description="OBIS码")
    attribute_id: Optional[int] = Field(default=None, description="属性ID")


class SetResponseAPDU(APDUBase):
    """SetResponse APDU (tag=0xC3, 195)"""

    type_name: str = "SetResponse"
    set_type: int = Field(default=1, description="Set响应类型")
    invoke_id: int = Field(default=0, description="调用ID")
    result: str = Field(default="", description="结果")
    result_code: int = Field(default=0, description="结果码")


class EventNotificationAPDU(APDUBase):
    """
    EventNotification APDU (tag=0xC4, 196)

    格式:
    - tag (1 byte) = 0xC4
    - time (可选, date-time)
    - cosem_attribute_descriptor (9 bytes)
    - attribute_descriptor_list (可选)
    - value: Data
    """

    type_name: str = "EventNotification"
    datetime: Optional[dict] = Field(default=None, description="时间戳")
    class_id: Optional[int] = Field(default=None, description="类ID")
    obis: Optional[str] = Field(default=None, description="OBIS码")
    attribute_id: Optional[int] = Field(default=None, description="属性ID")
    data_type: Optional[str] = Field(default=None, description="数据类型")
    value: Any = Field(default=None, description="事件值")


class ActionRequestAPDU(APDUBase):
    """ActionRequest APDU (tag=0xC7, 199)"""

    type_name: str = "ActionRequest"
    action_type: int = Field(default=1, description="Action请求类型")
    invoke_id: int = Field(default=0, description="调用ID")
    class_id: Optional[int] = Field(default=None, description="类ID")
    obis: Optional[str] = Field(default=None, description="OBIS码")
    method_id: Optional[int] = Field(default=None, description="方法ID")


class ActionResponseAPDU(APDUBase):
    """ActionResponse APDU (tag=0xC8, 200)"""

    type_name: str = "ActionResponse"
    action_type: int = Field(default=1, description="Action响应类型")
    invoke_id: int = Field(default=0, description="调用ID")
    result: str = Field(default="", description="结果")
    result_code: int = Field(default=0, description="结果码")
    data_type: Optional[str] = Field(default=None, description="返回数据类型")
    value: Any = Field(default=None, description="返回值")


class GeneralGloCipheringAPDU(APDUBase):
    """
    GeneralGloCiphering APDU (tag=0xDB, 219)

    全局加密APDU，包含加密的数据。
    实际APDU内容在解密后才能解析。

    格式:
    - tag (1 byte) = 0xDB
    - system-title (octet-string, 8 bytes)
    - data (octet-string): 加密的数据
    """

    type_name: str = "GeneralGloCiphering"
    system_title: str = Field(default="", description="系统标题 (16进制)")
    system_title_bytes: bytes = Field(default=b"", description="系统标题原始字节")
    ciphered_data: str = Field(default="", description="加密数据 (16进制)")
    ciphered_data_bytes: bytes = Field(default=b"", description="加密数据原始字节")
    ciphered_service_len: Optional[int] = Field(default=None, description="加密服务长度")


class GeneralCipheringAPDU(APDUBase):
    """GeneralCiphering APDU (tag=0xDA, 218)"""

    type_name: str = "GeneralCiphering"
    system_title: str = Field(default="", description="系统标题")
    ciphered_data: str = Field(default="", description="加密数据")


class UnknownAPDU(APDUBase):
    """未知APDU类型"""

    type_name: str = "Unknown"
    data_hex: str = Field(default="", description="完整数据的十六进制表示")


# APDU类型映射
APDU_TYPES = {
    0x0F: DataNotificationAPDU,       # 15
    0xC0: GetRequestAPDU,             # 192
    0xC1: GetResponseAPDU,            # 193
    0xC2: SetRequestAPDU,             # 194
    0xC3: SetResponseAPDU,            # 195
    0xC4: EventNotificationAPDU,      # 196
    0xC7: ActionRequestAPDU,          # 199
    0xC8: ActionResponseAPDU,         # 200
    0xDA: GeneralCipheringAPDU,       # 218
    0xDB: GeneralGloCipheringAPDU,    # 219
}
