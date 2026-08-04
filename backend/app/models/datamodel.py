"""
数据模型对象定义 (COSEM对象模型)
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CosemObject(BaseModel):
    """COSEM对象模型"""

    class_id: int = Field(description="类ID (Class ID)")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    name: str = Field(default="", description="对象名称")
    data_type: str = Field(default="", description="数据类型")
    description: str = Field(default="", description="描述")
    attribute_id: Optional[int] = Field(default=None, description="属性ID")
    unit: str = Field(default="", description="单位")
    scaler: float = Field(default=1.0, description="倍率")
    version: str = Field(default="", description="类版本")

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": 3,
                "obis": "1-0:1.8.0.255",
                "name": "正向有功总电能",
                "data_type": "double-long-unsigned",
                "description": "当前正向有功总电能累计值",
                "attribute_id": 2,
                "unit": "kWh",
                "scaler": 0.01,
            }
        }
    }


class DataModelUploadResponse(BaseModel):
    """数据模型上传响应"""

    success: bool = Field(description="是否成功")
    total_objects: int = Field(default=0, description="总对象数")
    classes: List[int] = Field(default_factory=list, description="包含的类ID列表")
    message: str = Field(default="", description="消息")


class DataModelSearchResponse(BaseModel):
    """数据模型搜索响应"""

    results: List[CosemObject] = Field(default_factory=list, description="搜索结果")
    total: int = Field(default=0, description="总匹配数")


class CosemAttribute(BaseModel):
    """COSEM属性"""

    attribute_id: int = Field(description="属性ID")
    name: str = Field(default="", description="属性名称")
    data_type: str = Field(default="", description="数据类型")
    description: str = Field(default="", description="描述")
    unit: str = Field(default="", description="单位")
    scaler: float = Field(default=1.0, description="倍率")


class CosemMethod(BaseModel):
    """COSEM方法"""

    method_id: int = Field(description="方法ID")
    name: str = Field(default="", description="方法名称")
    data_type: str = Field(default="", description="返回类型")
    description: str = Field(default="", description="描述")


class CosemObjectDetail(BaseModel):
    """COSEM对象完整详情（含所有属性和方法）"""

    class_id: int = Field(description="类ID (Class ID)")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    name: str = Field(default="", description="对象名称")
    version: str = Field(default="", description="类版本")
    description: str = Field(default="", description="描述")
    attributes: List[CosemAttribute] = Field(default_factory=list, description="属性列表")
    methods: List[CosemMethod] = Field(default_factory=list, description="方法列表")
