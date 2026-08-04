"""
数据模型管理 (COSEM Data Model)

从Excel文件加载OBIS对象模型，提供搜索和匹配功能。

Excel格式要求:
- 列名: class_id, obis, name, attribute_id, data_type, description, unit, scaler
- 或者使用更友好的中文列名: 类ID, OBIS码, 名称, 属性ID, 数据类型, 描述, 单位, 倍率
"""
import os
from typing import Optional, Dict, Tuple, List

from openpyxl import load_workbook

from app.models.datamodel import CosemObject
from app.utils.obis_utils import normalize_obis, obis_bytes_to_str
from app.utils.hex_utils import hex_to_bytes


class DataModelManager:
    """数据模型管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 内存索引
        # 主索引: (class_id, obis_tuple, attribute_id) -> CosemObject
        self._objects: Dict[Tuple[int, Tuple[int, ...], int], CosemObject] = {}

        # 辅助索引
        self._by_class: Dict[int, List[CosemObject]] = {}
        self._all_objects: List[CosemObject] = []

        # 加载状态
        self._loaded = False
        self._source_file: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def total_objects(self) -> int:
        return len(self._all_objects)

    @property
    def source_file(self) -> Optional[str]:
        return self._source_file

    def load_excel(self, file_path: str) -> dict:
        """
        从Excel文件加载数据模型

        Args:
            file_path: Excel文件路径

        Returns:
            dict: 加载结果信息

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: Excel格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel文件不存在: {file_path}")

        # 清空现有数据
        self._objects.clear()
        self._by_class.clear()
        self._all_objects.clear()

        wb = load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active

        # 读取表头
        headers = []
        for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
            headers = [str(h).strip().lower() if h else "" for h in row]
            break

        # 列映射 - 支持中英文列名
        col_map = self._map_columns(headers)

        if "class_id" not in col_map or "obis" not in col_map:
            raise ValueError(
                "Excel文件缺少必要列（class_id/类ID 和 obis/OBIS码）。"
                f"当前列: {headers}"
            )

        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            try:
                obj = self._parse_row(row, col_map)
                if obj is not None:
                    key = (obj.class_id, normalize_obis(obj.obis), obj.attribute_id or 0)
                    self._objects[key] = obj
                    self._all_objects.append(obj)

                    # 按类ID索引
                    if obj.class_id not in self._by_class:
                        self._by_class[obj.class_id] = []
                    self._by_class[obj.class_id].append(obj)

                    count += 1
            except Exception:
                # 跳过解析失败的行
                continue

        wb.close()

        self._loaded = True
        self._source_file = file_path

        return {
            "total_objects": count,
            "classes": sorted(self._by_class.keys()),
            "source_file": os.path.basename(file_path),
        }

    @staticmethod
    def _map_columns(headers: List[str]) -> Dict[str, int]:
        """
        映射列名到列索引

        支持的列名（不区分大小写）:
        - class_id / 类ID / class id / class
        - obis / OBIS码 / obis code
        - name / 名称 / 描述名
        - attribute_id / 属性ID / attr id
        - data_type / 数据类型 / type
        - description / 描述 / remark / 备注
        - unit / 单位
        - scaler / 倍率 / 系数
        """
        col_map = {}

        for i, h in enumerate(headers):
            h_lower = h.lower().strip()

            if h_lower in ("class_id", "class id", "class", "类id", "类号"):
                col_map["class_id"] = i
            elif h_lower in ("obis", "obis code", "obis码", "obis代码"):
                col_map["obis"] = i
            elif h_lower in ("name", "名称", "对象名", "描述名"):
                col_map["name"] = i
            elif h_lower in ("attribute_id", "attribute id", "attr_id", "attr id", "属性id", "属性号"):
                col_map["attribute_id"] = i
            elif h_lower in ("data_type", "data type", "datatype", "数据类型", "类型"):
                col_map["data_type"] = i
            elif h_lower in ("description", "desc", "描述", "说明", "备注", "remark"):
                col_map["description"] = i
            elif h_lower in ("unit", "单位", "计量单位"):
                col_map["unit"] = i
            elif h_lower in ("scaler", "scaling", "倍率", "系数", "比例"):
                col_map["scaler"] = i

        return col_map

    @staticmethod
    def _parse_row(row: tuple, col_map: Dict[str, int]) -> Optional[CosemObject]:
        """
        解析Excel行数据

        Args:
            row: 行数据元组
            col_map: 列映射

        Returns:
            CosemObject或None（如果行无效）
        """
        def get_val(key, default=None):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return default
            val = row[idx]
            return val if val is not None else default

        # class_id - 必填
        class_id_val = get_val("class_id")
        if class_id_val is None:
            return None
        try:
            class_id = int(class_id_val)
        except (ValueError, TypeError):
            return None

        # obis - 必填
        obis_val = get_val("obis")
        if obis_val is None or str(obis_val).strip() == "":
            return None
        obis_str = str(obis_val).strip()

        # 验证OBIS格式
        try:
            normalize_obis(obis_str)
        except ValueError:
            return None

        # 可选字段
        name = str(get_val("name", "")) if get_val("name") else ""
        data_type = str(get_val("data_type", "")) if get_val("data_type") else ""
        description = str(get_val("description", "")) if get_val("description") else ""
        unit = str(get_val("unit", "")) if get_val("unit") else ""

        attribute_id = None
        attr_val = get_val("attribute_id")
        if attr_val is not None:
            try:
                attribute_id = int(attr_val)
            except (ValueError, TypeError):
                pass

        scaler = 1.0
        scaler_val = get_val("scaler")
        if scaler_val is not None:
            try:
                scaler = float(scaler_val)
            except (ValueError, TypeError):
                pass

        return CosemObject(
            class_id=class_id,
            obis=obis_str,
            name=name,
            data_type=data_type,
            description=description,
            attribute_id=attribute_id,
            unit=unit,
            scaler=scaler,
        )

    def match_obis(self, class_id: int, obis_bytes: bytes, attribute_id: int = 0) -> Optional[CosemObject]:
        """
        匹配OBIS对象

        Args:
            class_id: 类ID
            obis_bytes: OBIS码（6字节）
            attribute_id: 属性ID (0表示匹配任意属性)

        Returns:
            匹配到的CosemObject，未找到返回None
        """
        if not self._loaded:
            return None

        try:
            obis_tuple = tuple(obis_bytes)
        except Exception:
            return None

        # 精确匹配
        key = (class_id, obis_tuple, attribute_id)
        if key in self._objects:
            return self._objects[key]

        # 尝试匹配 attribute_id=0 的情况（通配）
        key = (class_id, obis_tuple, 0)
        if key in self._objects:
            return self._objects[key]

        # 尝试带通配符的OBIS匹配 (255表示通配)
        for (c_id, o_tuple, a_id), obj in self._objects.items():
            if c_id == class_id and (a_id == 0 or a_id == attribute_id):
                # 检查OBIS通配匹配
                match = True
                for o1, o2 in zip(obis_tuple, o_tuple):
                    if o1 != 255 and o2 != 255 and o1 != o2:
                        match = False
                        break
                if match:
                    return obj

        return None

    def get_object_list(self, class_id: Optional[int] = None,
                        limit: int = 100, offset: int = 0) -> List[CosemObject]:
        """
        获取对象列表

        Args:
            class_id: 按类ID过滤（None表示不过滤）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            对象列表
        """
        if not self._loaded:
            return []

        if class_id is not None:
            objects = self._by_class.get(class_id, [])
        else:
            objects = self._all_objects

        return objects[offset:offset + limit]

    def search(self, keyword: str, class_id: Optional[int] = None,
               limit: int = 100) -> List[CosemObject]:
        """
        搜索OBIS对象

        Args:
            keyword: 搜索关键词（匹配名称、描述、OBIS码）
            class_id: 按类ID过滤（可选）
            limit: 返回数量限制

        Returns:
            匹配的对象列表
        """
        if not self._loaded or not keyword:
            return []

        keyword_lower = keyword.lower()
        results = []

        source = self._by_class.get(class_id, []) if class_id is not None else self._all_objects

        for obj in source:
            if (keyword_lower in obj.name.lower() or
                keyword_lower in obj.obis.lower() or
                keyword_lower in obj.description.lower()):
                results.append(obj)
                if len(results) >= limit:
                    break

        return results

    def get_classes(self) -> List[int]:
        """获取所有类ID列表"""
        return sorted(self._by_class.keys())


# 全局单例实例
data_model_manager = DataModelManager()


# 便捷函数
def load_excel(file_path: str) -> dict:
    """从Excel加载数据模型"""
    return data_model_manager.load_excel(file_path)


def match_obis(class_id: int, obis_bytes: bytes, attribute_id: int = 0) -> Optional[CosemObject]:
    """匹配OBIS对象"""
    return data_model_manager.match_obis(class_id, obis_bytes, attribute_id)
