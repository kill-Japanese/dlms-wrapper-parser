"""
Push Setup (Class 40) 多版本支持模块

根据 DLMS 蓝皮书 (IEC 62056-6-2)，Push Setup class 有多个版本：
- Version 0: 基础版本，只有 Push object list
- Version 1: 增加 Send destination and method
- Version 2: 增加 Communication window 和 Repetition delay
- Version 3: 最新版本，增强功能

本模块提供：
1. 各版本 Push object list 结构定义
2. 自动识别 Class 40 版本的逻辑
3. 根据版本解析 Push object list
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PushObjectDefinition:
    """Push object list 中的单个对象定义"""
    class_id: int
    obis: str
    obis_bytes: bytes
    attribute_id: int
    data_index: int = 0
    # v2+ 可能有的额外字段
    access_selector: Optional[int] = None
    access_params: Optional[Any] = None
    # 原始 structure 中的元素个数（用于版本判断）
    raw_element_count: int = 0


@dataclass
class PushSetupVersionInfo:
    """Push Setup 版本信息"""
    version: int
    version_name: str
    description: str
    push_object_list_structure: List[str]  # structure 中各字段名称
    attributes: List[str]  # 所有属性列表


# 各版本定义
PUSH_SETUP_VERSIONS: Dict[int, PushSetupVersionInfo] = {
    0: PushSetupVersionInfo(
        version=0,
        version_name="v0",
        description="基础版本",
        push_object_list_structure=[
            "class_id",       # long-unsigned
            "instance_id",    # octet-string(6)
            "attribute_id",   # integer8
        ],
        attributes=[
            "1: Logical name",
            "2: Push object list",
        ],
    ),
    1: PushSetupVersionInfo(
        version=1,
        version_name="v1",
        description="增加推送目标和方法",
        push_object_list_structure=[
            "class_id",       # long-unsigned
            "instance_id",    # octet-string(6)
            "attribute_id",   # integer8
            "data_index",     # long-unsigned (可选)
        ],
        attributes=[
            "1: Logical name",
            "2: Push object list",
            "3: Send destination and method",
        ],
    ),
    2: PushSetupVersionInfo(
        version=2,
        version_name="v2",
        description="增加通信窗口和重试延迟",
        push_object_list_structure=[
            "class_id",         # long-unsigned
            "instance_id",      # octet-string(6)
            "attribute_id",     # integer8
            "data_index",       # long-unsigned
            "access_selector",  # enum (可选)
            "access_params",    # structure (可选)
        ],
        attributes=[
            "1: Logical name",
            "2: Push object list",
            "3: Send destination and method",
            "4: Communication window",
            "5: Repetition delay",
            "6: Number of retries",
        ],
    ),
    3: PushSetupVersionInfo(
        version=3,
        version_name="v3",
        description="最新版本，增强功能",
        push_object_list_structure=[
            "class_id",         # long-unsigned
            "instance_id",      # octet-string(6)
            "attribute_id",     # integer8
            "data_index",       # long-unsigned
            "access_selector",  # enum (可选)
            "access_params",    # structure / array (可选)
        ],
        attributes=[
            "1: Logical name",
            "2: Push object list",
            "3: Send destination and method",
            "4: Communication window",
            "5: Repetition delay",
            "6: Number of retries",
            "7: Push client setup reference",
        ],
    ),
}


def detect_push_setup_version(descriptor_elements: List[Any]) -> int:
    """
    根据 Push object list 中单个描述符的 structure 元素个数，自动识别版本

    版本识别规则（基于描述符 structure 的元素个数）：
    - 3 个元素: v0 (class_id, obis, attribute_id)
    - 4 个元素: v1 (增加 data_index)
    - 5-6 个元素: v2/v3 (增加 access_selector, access_params)

    Args:
        descriptor_elements: 单个描述符的元素列表（从 structure 解析出来的）

    Returns:
        推测的版本号 (0, 1, 2, 3)
    """
    n = len(descriptor_elements)

    if n <= 3:
        return 0
    elif n == 4:
        return 1
    elif n == 5:
        return 2
    elif n >= 6:
        return 3
    else:
        return 0  # 默认 v0


def parse_push_object_descriptor(
    struct_elements: List[Any],
    version: Optional[int] = None
) -> Tuple[PushObjectDefinition, int]:
    """
    解析 Push object list 中的单个描述符 structure

    Args:
        struct_elements: structure 的元素列表
        version: 指定版本，如果为 None 则自动检测

    Returns:
        (PushObjectDefinition, detected_version)
    """
    from app.utils.obis_utils import obis_bytes_to_str

    # 自动检测版本
    if version is None:
        version = detect_push_setup_version(struct_elements)

    n = len(struct_elements)
    obj = PushObjectDefinition(
        class_id=0,
        obis="",
        obis_bytes=b"",
        attribute_id=0,
        raw_element_count=n,
    )

    # 前 3 个元素是固定的：class_id, obis, attribute_id
    if n >= 1 and isinstance(struct_elements[0], int):
        obj.class_id = struct_elements[0]

    if n >= 2 and isinstance(struct_elements[1], (bytes, bytearray)):
        obj.obis_bytes = bytes(struct_elements[1])
        if len(obj.obis_bytes) == 6:
            obj.obis = obis_bytes_to_str(obj.obis_bytes)

    if n >= 3 and isinstance(struct_elements[2], int):
        # attribute_id 可能是 integer (有符号)
        # 在紧凑编码中 0x0F 是 integer (int8)
        obj.attribute_id = struct_elements[2]

    # 第 4 个元素：data_index (v1+)
    if n >= 4 and isinstance(struct_elements[3], int):
        obj.data_index = struct_elements[3]

    # 第 5 个元素：access_selector (v2+)
    if n >= 5:
        if isinstance(struct_elements[4], int):
            obj.access_selector = struct_elements[4]
        elif isinstance(struct_elements[4], list) and len(struct_elements[4]) >= 1:
            # 可能是 enum 形式: [enum_value, ...]
            if isinstance(struct_elements[4][0], int):
                obj.access_selector = struct_elements[4][0]

    # 第 6 个元素：access_params (v2+)
    if n >= 6:
        obj.access_params = struct_elements[5]

    return obj, version


def parse_push_object_list(
    array_elements: List[Any],
    version: Optional[int] = None
) -> Tuple[List[PushObjectDefinition], int]:
    """
    解析整个 Push object list array

    Args:
        array_elements: array 的元素列表（每个是一个 structure）
        version: 指定版本，如果为 None 则自动检测

    Returns:
        (object_list, detected_version)
    """
    if not array_elements:
        return [], version or 0

    # 用第一个描述符来检测版本
    first_struct = array_elements[0]
    if isinstance(first_struct, list):
        detected_version = detect_push_setup_version(first_struct)
    else:
        detected_version = version or 0

    if version is None:
        version = detected_version

    objects = []
    for elem in array_elements:
        if isinstance(elem, list):
            obj, _ = parse_push_object_descriptor(elem, version)
            objects.append(obj)

    return objects, version


def get_version_info(version: int) -> PushSetupVersionInfo:
    """获取指定版本的信息"""
    return PUSH_SETUP_VERSIONS.get(version, PUSH_SETUP_VERSIONS[0])


def get_all_versions() -> List[PushSetupVersionInfo]:
    """获取所有版本列表"""
    return list(PUSH_SETUP_VERSIONS.values())


def auto_detect_version_from_notification_body(
    descriptor_array: List[Any],
    value_count: int
) -> int:
    """
    从 DataNotification body 中自动检测 Class 40 版本

    检测逻辑：
    1. 检查描述符 structure 的元素个数
    2. 结合值的数量辅助判断

    Args:
        descriptor_array: 描述符 array（每个元素是一个 structure）
        value_count: 值的数量

    Returns:
        检测到的版本号
    """
    if not descriptor_array or not isinstance(descriptor_array, list):
        return 0

    first_desc = descriptor_array[0]
    if not isinstance(first_desc, list):
        return 0

    return detect_push_setup_version(first_desc)
