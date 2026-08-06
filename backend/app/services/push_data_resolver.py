"""
Push 数据深度解析器

结合 Push Setup (Class 40) 的 push_object_list 和数据模型/标准库/手动配置，
深度解析 DataNotification 中的推送数据。

特别支持 Profile Generic (Class 7) buffer 的逐元素解析，
需要使用 capture_objects 定义来解释 buffer 中每个元素的含义。

capture_objects 获取优先级：
1. 用户手动注入（ProfileCaptureStore）← 最高优先级
2. 数据模型（datamodel）
3. 标准库（cosem_standards）← 仅结构框架
"""

from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class PushDataResolver:
    """
    Push 数据深度解析器
    
    提供静态方法，对 DataNotification 的数据项进行深度解析和增强。
    """

    @staticmethod
    def resolve_notification_items(notification_items: List[dict],
                                    push_object_list: List[dict] = None,
                                    data_model=None,
                                    standards_manager=None,
                                    profile_capture_store=None) -> dict:
        """
        深度解析 DataNotification 的所有推送项
        
        Args:
            notification_items: APDU 解析出的 notification-body 数据项列表
            push_object_list: Push Setup 的 push_object_list 定义（可选）
            data_model: 数据模型管理器（可选，用于获取对象详情）
            standards_manager: 标准库管理器（可选，用于获取 Class 定义）
            profile_capture_store: Profile capture_objects 手动配置存储（可选）
        
        Returns:
            {
                "push_object_list": [...],        # 推送对象定义列表
                "resolved_items": [...],          # 解析后的项（每个项含详细信息）
                "warnings": [...]                 # 警告信息
            }
        """
        warnings = []
        resolved_items = []

        # 如果没有 push_object_list，直接返回原始数据加警告
        if not push_object_list:
            warnings.append("No push_object_list provided, showing raw values only")
            for i, item in enumerate(notification_items):
                resolved_items.append({
                    "index": i,
                    "type": "unknown",
                    "raw_value": item.get("value") if isinstance(item, dict) else item,
                    "raw_type": item.get("type", "") if isinstance(item, dict) else "",
                    "warning": "No push object definition available",
                })
            return {
                "push_object_list": [],
                "resolved_items": resolved_items,
                "warnings": warnings,
            }

        # 逐项解析
        for i, item in enumerate(notification_items):
            resolved_item = PushDataResolver._resolve_single_item(
                item, i, push_object_list, data_model,
                standards_manager, profile_capture_store, warnings
            )
            resolved_items.append(resolved_item)

        return {
            "push_object_list": push_object_list,
            "resolved_items": resolved_items,
            "warnings": warnings,
        }

    @staticmethod
    def _resolve_single_item(item: dict, index: int,
                             push_object_list: List[dict],
                             data_model, standards_manager,
                             profile_capture_store, warnings: List[str]) -> dict:
        """解析单个推送项"""
        # 获取原始值
        raw_value = item.get("value") if isinstance(item, dict) else item
        raw_type = item.get("type", "") if isinstance(item, dict) else ""

        result = {
            "index": index,
            "raw_value": raw_value,
            "raw_type": raw_type,
        }

        # 获取对应的 push object 定义
        if index >= len(push_object_list):
            result["push_object"] = None
            result["type"] = "unknown"
            result["warning"] = f"No push object definition for item {index}"
            warnings.append(f"Item {index}: no push object definition")
            return result

        push_obj = push_object_list[index]

        # 标准化 push_obj 格式
        class_id = push_obj.get("class_id", push_obj.get("classId", 0))
        instance_id = push_obj.get("instance_id", push_obj.get("obis", ""))
        attribute_id = push_obj.get("attribute_id", push_obj.get("attrId", 0))
        data_index = push_obj.get("data_index", push_obj.get("dataIndex", 0))

        # 获取 Class 名称和属性名称
        class_name = PushDataResolver._get_class_name(class_id, standards_manager)
        attribute_name = PushDataResolver._get_attribute_name(
            class_id, attribute_id, standards_manager
        )

        result["push_object"] = {
            "class_id": class_id,
            "class_name": class_name,
            "obis": instance_id,
            "attribute_id": attribute_id,
            "attribute_name": attribute_name,
            "data_index": data_index,
        }

        # 根据不同类型进行深度解析
        if class_id == 7 and attribute_id == 2:
            # Profile Generic buffer - 深度解析
            result["type"] = "profile_buffer"
            result["profile_buffer"] = PushDataResolver._resolve_profile_buffer(
                raw_value, class_id, instance_id, attribute_id, data_index,
                data_model, standards_manager, profile_capture_store, warnings
            )
        else:
            # 普通对象 - 增强显示信息
            result["type"] = "normal_object"
            result["enhanced"] = PushDataResolver._enhance_normal_object(
                raw_value, class_id, instance_id, attribute_id,
                data_model, standards_manager, warnings
            )

        return result

    @staticmethod
    def _resolve_profile_buffer(buffer_value, class_id: int, obis: str,
                                attribute_id: int, data_index: int,
                                data_model, standards_manager,
                                profile_capture_store, warnings: List[str]) -> dict:
        """
        解析 Profile Generic buffer

        buffer 格式: array of structure (每个 structure 是一条记录)
        每个 structure 的元素对应 capture_objects 中的一个对象。

        返回结构:
        {
            "profile_obis": ...,
            "capture_objects_source": ...,
            "capture_objects": [...],
            "entries": [
                {
                    "entry_index": 0,
                    "fields": [
                        { "field_index": 0, "capture_object": {...}, "formatted_value": ... },
                        ...
                    ],
                    "field_count": N
                },
                ...
            ],
            "entry_count": N,
            # 兼容旧前端的平铺 fields (取第一条记录)
            "fields": [...],
            "field_count": N,
        }
        """
        result = {
            "profile_obis": obis,
            "capture_objects_source": "unknown",
            "capture_objects": [],
            "entries": [],
            "entry_count": 0,
            # 兼容旧前端
            "fields": [],
            "field_count": 0,
        }

        # 获取 capture_objects 定义（按优先级）
        capture_result = PushDataResolver._get_capture_objects(
            obis, data_model, standards_manager, profile_capture_store
        )
        result["capture_objects_source"] = capture_result["source"]
        result["capture_objects"] = capture_result["objects"]

        if capture_result["source"] == "unknown":
            result["warning"] = (
                "Cannot resolve capture_objects. "
                "You can manually configure it or select a profile OBIS."
            )
            warnings.append(f"Profile {obis}: capture_objects unknown")
            result["raw_structure"] = buffer_value
            return result

        cap_objs = capture_result["objects"]

        # 规范化 buffer_value 为 entries 列表
        # buffer_value 可能是:
        #   1. [[elem1, elem2, ...], [elem1, elem2, ...]]  → array of entries
        #   2. [elem1, elem2, ...]                         → single entry (structure)
        #   3. 非 list                                      → single value
        if isinstance(buffer_value, list) and len(buffer_value) > 0:
            first = buffer_value[0]
            if isinstance(first, list):
                # array of entries
                entries_raw = buffer_value
            else:
                # single entry (structure)
                entries_raw = [buffer_value]
        else:
            entries_raw = [[buffer_value]] if buffer_value is not None else []

        all_entries = []

        for entry_idx, entry_elements in enumerate(entries_raw):
            # 每个 entry 是一个 structure，其元素对应 capture_objects
            elements = entry_elements if isinstance(entry_elements, list) else [entry_elements]

            fields = []
            for j, field_value in enumerate(elements):
                field = {
                    "field_index": j,
                    "raw_value": field_value,
                }

                if j < len(cap_objs):
                    cap_obj = cap_objs[j]
                    cap_class_id = cap_obj.get("class_id", 0)
                    cap_obis = cap_obj.get("instance_id", cap_obj.get("obis", ""))
                    cap_attr_id = cap_obj.get("attribute_id", 0)

                    field["capture_object"] = {
                        "class_id": cap_class_id,
                        "class_name": PushDataResolver._get_class_name(
                            cap_class_id, standards_manager
                        ),
                        "obis": cap_obis,
                        "obis_name": PushDataResolver._get_obis_name(
                            cap_class_id, cap_obis, data_model
                        ),
                        "attribute_id": cap_attr_id,
                        "attribute_name": PushDataResolver._get_attribute_name(
                            cap_class_id, cap_attr_id, standards_manager
                        ),
                        "data_index": cap_obj.get("data_index", 0),
                        "remark": cap_obj.get("remark", ""),
                    }

                    # 格式化值
                    field["formatted_value"] = PushDataResolver._format_capture_value(
                        field_value, cap_obj, data_model, standards_manager
                    )
                    field["unit"] = PushDataResolver._get_capture_unit(
                        cap_obj, data_model
                    )
                else:
                    # 超出 capture_objects 范围的字段
                    field["capture_object"] = None
                    field["formatted_value"] = str(field_value)
                    field["unit"] = ""
                    field["warning"] = f"No capture_object for field {j}"

                fields.append(field)

            entry_result = {
                "entry_index": entry_idx,
                "fields": fields,
                "field_count": len(fields),
            }
            all_entries.append(entry_result)

        result["entries"] = all_entries
        result["entry_count"] = len(all_entries)

        # 兼容旧前端: 用第一条记录的 fields 作为顶层 fields
        if all_entries:
            result["fields"] = all_entries[0]["fields"]
            result["field_count"] = all_entries[0]["field_count"]

        return result

    @staticmethod
    def _get_capture_objects(profile_obis: str, data_model,
                             standards_manager, profile_capture_store) -> dict:
        """
        获取 Profile Generic 对象的 capture_objects 定义
        
        优先级：
        1. 用户手动注入（profile_capture_store）← 最高
        2. 数据模型（data_model）
        3. 标准库（standards_manager）← 仅结构框架
        
        Returns:
            {
                "source": "manual" | "data_model" | "standard" | "unknown",
                "objects": [ ... ]
            }
        """
        # 方式1：从手动注入存储获取（最高优先级）
        if profile_capture_store:
            try:
                cap_objs = profile_capture_store.get_capture_objects(profile_obis)
                if cap_objs:
                    return {
                        "source": "manual",
                        "objects": cap_objs,
                    }
            except Exception as e:
                logger.debug(f"Failed to get capture_objects from store: {e}")

        # 方式2：从数据模型获取
        if data_model:
            try:
                cap_objs = PushDataResolver._get_capture_from_datamodel(
                    profile_obis, data_model
                )
                if cap_objs:
                    return {
                        "source": "data_model",
                        "objects": cap_objs,
                    }
            except Exception as e:
                logger.debug(f"Failed to get capture_objects from data_model: {e}")

        # 方式3：从标准库获取结构定义（仅框架，无具体对象）
        if standards_manager:
            try:
                # 获取 Profile Generic v1 的属性3定义
                attr_def = standards_manager.get_attribute_definition(7, 1, 3)
                if attr_def and attr_def.get("element_structure"):
                    # 标准库只知道结构，不知道具体 capture 了哪些对象
                    return {
                        "source": "standard",
                        "objects": [],  # 空列表，因为不知道具体对象
                        "structure_def": attr_def["element_structure"],
                    }
            except Exception as e:
                logger.debug(f"Failed to get capture_objects from standards: {e}")

        return {"source": "unknown", "objects": []}

    @staticmethod
    def _get_capture_from_datamodel(profile_obis: str, data_model) -> List[dict]:
        """从数据模型获取 capture_objects"""
        try:
            # 尝试从数据模型获取 Profile Generic 对象详情
            if hasattr(data_model, 'get_object_detail'):
                obj_detail = data_model.get_object_detail(
                    class_id=7, obis=profile_obis
                )
                if obj_detail:
                    # 尝试获取属性3（capture_objects）
                    attributes = getattr(obj_detail, 'attributes', None) or []
                    for attr in attributes:
                        attr_id = getattr(attr, 'attribute_id', None) or attr.get('attribute_id')
                        if attr_id == 3:
                            # 检查是否有 capture_objects 字段
                            cap_objs = getattr(attr, 'capture_objects', None)
                            if cap_objs and isinstance(cap_objs, list):
                                return [
                                    co if isinstance(co, dict) else {
                                        "class_id": getattr(co, 'class_id', 0),
                                        "instance_id": getattr(co, 'instance_id', ''),
                                        "attribute_id": getattr(co, 'attribute_id', 0),
                                        "data_index": getattr(co, 'data_index', 0),
                                    }
                                    for co in cap_objs
                                ]
                            # 也可能在 value 字段中
                            attr_value = getattr(attr, 'value', None)
                            if attr_value and isinstance(attr_value, list):
                                return attr_value
        except Exception as e:
            logger.debug(f"Error getting capture from datamodel: {e}")

        return []

    @staticmethod
    def _enhance_normal_object(value, class_id: int, obis: str,
                               attribute_id: int, data_model,
                               standards_manager, warnings: List[str]) -> dict:
        """增强普通对象的显示信息"""
        result = {
            "value": value,
            "formatted_value": str(value),
            "unit": "",
            "object_name": "",
        }

        # 尝试获取对象名称
        result["object_name"] = PushDataResolver._get_obis_name(
            class_id, obis, data_model
        )

        # 对于 Register 类型，尝试获取 scaler_unit 进行缩放
        if class_id in (3, 4, 5) and attribute_id == 2:  # value 属性
            scaler_unit_info = PushDataResolver._get_scaler_unit(
                class_id, obis, data_model
            )
            if scaler_unit_info:
                try:
                    from .cosem_standards.unit_codes import format_value_with_scaler_unit
                    if isinstance(value, (int, float)):
                        result["formatted_value"] = format_value_with_scaler_unit(
                            value, scaler_unit_info
                        )
                        result["unit"] = PushDataResolver._get_unit_symbol_from_bytes(
                            scaler_unit_info
                        )
                except Exception:
                    pass

        return result

    @staticmethod
    def _format_capture_value(value, cap_obj: dict, data_model,
                              standards_manager) -> str:
        """格式化 capture object 的值"""
        # 简单实现：转换为字符串
        if value is None:
            return "null"
        if isinstance(value, bytes):
            return value.hex()
        if isinstance(value, dict):
            # date-time 对象有 iso 字段
            if "iso" in value:
                return value["iso"]
            return value.get("value", str(value))
        if isinstance(value, list):
            return f"[structure with {len(value)} elements]"
        return str(value)

    @staticmethod
    def _get_capture_unit(cap_obj: dict, data_model) -> str:
        """获取 capture object 的单位（仅 Register 等类型有效）"""
        class_id = cap_obj.get("class_id", 0)
        if class_id in (3, 4, 5):  # Register 类型有 scaler_unit
            obis = cap_obj.get("instance_id", "")
            scaler_unit = PushDataResolver._get_scaler_unit(class_id, obis, data_model)
            if scaler_unit:
                return PushDataResolver._get_unit_symbol_from_bytes(scaler_unit)
        return ""

    @staticmethod
    def _get_scaler_unit(class_id: int, obis: str, data_model) -> bytes:
        """从数据模型获取对象的 scaler_unit（属性3）"""
        if not data_model:
            return None

        try:
            if hasattr(data_model, 'get_object_detail'):
                obj_detail = data_model.get_object_detail(class_id=class_id, obis=obis)
                if obj_detail:
                    attributes = getattr(obj_detail, 'attributes', None) or []
                    for attr in attributes:
                        attr_id = getattr(attr, 'attribute_id', None) or attr.get('attribute_id')
                        if attr_id == 3:  # scaler_unit
                            attr_value = getattr(attr, 'value', None)
                            if isinstance(attr_value, bytes):
                                return attr_value
                            attr_val = attr.get('value') if isinstance(attr, dict) else None
                            if isinstance(attr_val, bytes):
                                return attr_val
        except Exception:
            pass

        return None

    @staticmethod
    def _get_unit_symbol_from_bytes(scaler_unit_bytes: bytes) -> str:
        """从 scaler_unit 字节中获取单位符号"""
        try:
            from .cosem_standards.unit_codes import parse_scaler_unit
            info = parse_scaler_unit(scaler_unit_bytes)
            return info["unit_symbol"]
        except Exception:
            return ""

    @staticmethod
    def _get_class_name(class_id: int, standards_manager) -> str:
        """获取 Class 名称"""
        if standards_manager:
            try:
                return standards_manager.get_class_name(class_id)
            except Exception:
                pass
        return f"Class {class_id}"

    @staticmethod
    def _get_attribute_name(class_id: int, attribute_id: int,
                            standards_manager) -> str:
        """获取属性名称"""
        if standards_manager:
            try:
                # 尝试获取最新版本的属性名称
                latest_ver = standards_manager.get_latest_version(class_id)
                if latest_ver is not None:
                    return standards_manager.get_attribute_name(
                        class_id, latest_ver, attribute_id
                    )
            except Exception:
                pass
        return f"attribute_{attribute_id}"

    @staticmethod
    def _get_obis_name(class_id: int, obis: str, data_model) -> str:
        """从数据模型获取对象的名称"""
        if not data_model or not obis:
            return ""

        try:
            if hasattr(data_model, 'get_object_detail'):
                obj_detail = data_model.get_object_detail(class_id=class_id, obis=obis)
                if obj_detail:
                    name = getattr(obj_detail, 'name', None) or getattr(obj_detail, 'obis_name', None)
                    if name:
                        return name
        except Exception:
            pass

        return ""

    @staticmethod
    def parse_push_object_list(raw_list: List) -> List[dict]:
        """
        解析原始的 push_object_list 数据
        
        将 APDU 解析出的原始数据转换为标准格式的 push_object_list。
        
        Args:
            raw_list: 原始 push_object_list 数据（array of structure）
        
        Returns:
            标准化的 push_object_list，每项包含 class_id, instance_id, attribute_id, data_index
        """
        result = []
        if not raw_list:
            return result

        for item in raw_list:
            if isinstance(item, list) and len(item) >= 3:
                # structure: [class_id, instance_id, attribute_id, data_index?]
                obj = {
                    "class_id": item[0] if len(item) > 0 else 0,
                    "instance_id": item[1] if len(item) > 1 else "",
                    "attribute_id": item[2] if len(item) > 2 else 0,
                    "data_index": item[3] if len(item) > 3 else 0,
                }
                result.append(obj)
            elif isinstance(item, dict):
                obj = {
                    "class_id": item.get("class_id", item.get("classId", 0)),
                    "instance_id": item.get("instance_id", item.get("obis", "")),
                    "attribute_id": item.get("attribute_id", item.get("attrId", 0)),
                    "data_index": item.get("data_index", item.get("dataIndex", 0)),
                }
                result.append(obj)

        return result
