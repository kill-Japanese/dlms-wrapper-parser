"""
APDU模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, List


class CosemDataItem(BaseModel):
    """COSEM数据项模型"""

    class_id: int = Field(description="类ID (Class ID)")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    attribute_id: int = Field(description="属性ID")
    data_type: str = Field(default="", description="数据类型")
    value: Any = Field(default=None, description="数据值")
    raw_hex: str = Field(default="", description="原始十六进制数据")


class APDUBase(BaseModel):
    """APDU基础模型"""

    tag: int = Field(description="APDU标签")
    type_name: str = Field(description="APDU类型名称")
    raw_hex: str = Field(default="", description="原始十六进制数据")


class DataNotificationAPDU(APDUBase):
    """DataNotification APDU (tag=15)"""

    type_name: str = "DataNotification"
    invoke_id: Optional[int] = Field(default=None, description="调用ID")
    datetime: Optional[str] = Field(default=None, description="日期时间")
    items: List[CosemDataItem] = Field(default_factory=list, description="数据项列表")
    notification_body_hex: str = Field(default="", description="通知体原始数据")


class GetRequestAPDU(APDUBase):
    """GetRequest APDU (tag=192)"""

    type_name: str = "GetRequest"
    get_type: int = Field(default=1, description="Get请求类型 (1/2/3)")
    invoke_id: int = Field(default=0, description="调用ID")
    class_id: Optional[int] = Field(default=None, description="类ID")
    obis: Optional[str] = Field(default=None, description="OBIS码")
    attribute_id: Optional[int] = Field(default=None, description="属性ID")


class GetResponseAPDU(APDUBase):
    """GetResponse APDU (tag=193)"""

    type_name: str = "GetResponse"
    get_type: int = Field(default=1, description="Get响应类型 (1/2/3)")
    invoke_id: int = Field(default=0, description="调用ID")
    result: str = Field(default="", description="结果")
    data_type: Optional[str] = Field(default=None, description="数据类型")
    value: Any = Field(default=None, description="返回值")


class GeneralGloCipheringAPDU(APDUBase):
    """GeneralGloCiphering APDU (tag=217)"""

    type_name: str = "GeneralGloCiphering"
    system_title: str = Field(default="", description="系统标题")
    ciphered_data: str = Field(default="", description="加密数据")


class UnknownAPDU(APDUBase):
    """未知APDU类型"""

    type_name: str = "Unknown"
    data_hex: str = Field(default="", description="完整数据的十六进制表示")


# APDU类型映射
APDU_TYPES = {
    15: DataNotificationAPDU,
    192: GetRequestAPDU,
    193: GetResponseAPDU,
    217: GeneralGloCipheringAPDU,
}
