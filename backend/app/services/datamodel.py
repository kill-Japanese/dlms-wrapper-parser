"""
数据模型管理 (COSEM Data Model)

从Excel文件加载OBIS对象模型，提供搜索和匹配功能。

支持的Excel格式:
1. 标准格式 (行式):
   - 列名: class_id, obis, name, attribute_id, data_type, description, unit, scaler
   - 或者使用更友好的中文列名: 类ID, OBIS码, 名称, 属性ID, 数据类型, 描述, 单位, 倍率

2. SABESP格式 (对象分组式):
   - Sheet名: "Object model"
   - 每个对象有一个"标题行"（D列/IC列有class_id值），后续行是该对象的属性/方法
   - A列 (#): 属性/方法序号
   - B列 (Object / Attribute Name): 对象/属性名称
   - C列 (Data Type): 数据类型
   - D列 (IC / Class): 接口类ID（仅对象标题行有值）
   - E列 (Ver.): 类版本
   - F列 (OBIS code / Default Value): OBIS码（仅标题行有值）
"""
import os
import re
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

        自动检测Excel格式（标准行式 / SABESP对象分组式）并解析。

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

        # 自动检测格式
        format_type = self._detect_format(wb)

        count = 0
        if format_type == "sabesp":
            count = self._load_sabesp_format(wb)
        else:
            count = self._load_standard_format(wb)

        wb.close()

        if count == 0:
            raise ValueError(
                "未能从Excel文件中解析出任何对象。"
                "请检查文件格式是否正确（支持标准行式和SABESP对象分组式）。"
            )

        self._loaded = True
        self._source_file = file_path

        return {
            "total_objects": count,
            "classes": sorted(self._by_class.keys()),
            "source_file": os.path.basename(file_path),
            "format": format_type,
        }

    def _detect_format(self, wb) -> str:
        """
        自动检测Excel格式

        Args:
            wb: openpyxl Workbook对象

        Returns:
            str: "standard" 或 "sabesp"
        """
        # 检查是否有 "Object model" sheet（SABESP格式特征）
        if "Object model" in wb.sheetnames:
            ws = wb["Object model"]
            # 检查前几行是否符合SABESP格式特征
            for i, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True)):
                # 检查D列(索引3)是否有数字字符串的class_id
                d_val = row[3] if len(row) > 3 else None
                f_val = row[5] if len(row) > 5 else None
                if (d_val and isinstance(d_val, str) and d_val.strip().isdigit()
                        and f_val and isinstance(f_val, str)
                        and re.match(r'^\d+-\d+:', f_val.strip())):
                    return "sabesp"

        # 检查活动sheet的表头是否符合标准格式
        ws = wb.active
        headers = []
        for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
            headers = [str(h).strip().lower() if h else "" for h in row]
            break

        col_map = self._map_columns(headers)
        if "class_id" in col_map and "obis" in col_map:
            return "standard"

        # 默认尝试标准格式
        return "standard"

    def _load_standard_format(self, wb) -> int:
        """
        加载标准行式格式的Excel

        Args:
            wb: openpyxl Workbook对象

        Returns:
            int: 解析出的对象数量
        """
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
                    self._add_object(obj)
                    count += 1
            except Exception:
                # 跳过解析失败的行
                continue

        return count

    def _load_sabesp_format(self, wb) -> int:
        """
        加载SABESP对象分组式格式的Excel

        SABESP格式特点:
        - Sheet名: "Object model"
        - 对象标题行: D列(IC)有数字字符串的class_id，A列为空，F列有OBIS码
        - 属性行: A列有数字序号，B列是属性名，C列是数据类型
        - 方法行: A列有数字序号，B列是方法名，C列可能有返回类型
        - 属性和方法分开编号（都从1开始），方法在属性之后，通过序号重置检测
        - 属性部分和方法部分之间没有空行，直接通过序号从1重新开始来区分

        Args:
            wb: openpyxl Workbook对象

        Returns:
            int: 解析出的对象数量
        """
        ws = wb["Object model"]

        count = 0
        current_object = None  # 当前对象信息
        in_method_section = False  # 是否在方法部分
        last_attr_id = 0  # 上一个属性/方法ID，用于检测方法部分的开始
        attr_count = 0  # 当前对象已解析的属性数量

        for row_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
            try:
                a_val = row[0] if len(row) > 0 else None
                b_val = row[1] if len(row) > 1 else None
                c_val = row[2] if len(row) > 2 else None
                d_val = row[3] if len(row) > 3 else None
                e_val = row[4] if len(row) > 4 else None
                f_val = row[5] if len(row) > 5 else None

                # 检测对象标题行
                is_header = self._is_sabesp_object_header(a_val, d_val, f_val)

                if is_header:
                    # 解析对象标题行
                    class_id = int(str(d_val).strip())
                    obis_str = str(f_val).strip()
                    object_name = str(b_val).strip() if b_val else ""

                    # 验证OBIS格式
                    try:
                        normalize_obis(obis_str)
                    except ValueError:
                        # OBIS格式无效，跳过此对象
                        current_object = None
                        continue

                    current_object = {
                        "class_id": class_id,
                        "obis": obis_str,
                        "name": object_name,
                        "version": str(e_val).strip() if e_val else "",
                    }
                    in_method_section = False
                    last_attr_id = 0
                    attr_count = 0

                    # 对象本身也作为一条记录（attribute_id=0）
                    obj = CosemObject(
                        class_id=class_id,
                        obis=obis_str,
                        name=object_name,
                        data_type="",
                        description=f"Object: {object_name}",
                        attribute_id=0,
                        unit="",
                        scaler=1.0,
                    )
                    self._add_object(obj)
                    count += 1

                elif current_object and a_val is not None:
                    # 属性/方法行
                    attr_id = self._parse_attribute_id(a_val)
                    if attr_id is None:
                        continue

                    attr_name = str(b_val).strip() if b_val else ""
                    data_type = str(c_val).strip() if c_val else ""

                    # 检测是否进入方法部分
                    # 当序号从大于1的值回到1时，说明进入了方法部分
                    # COSEM标准中属性在前，方法在后，各自从1开始编号
                    if not in_method_section and attr_id == 1 and last_attr_id > 1:
                        in_method_section = True

                    if in_method_section:
                        # 方法行 - 使用负的attribute_id来区分（-1, -2, ...）
                        method_id = attr_id
                        obj = CosemObject(
                            class_id=current_object["class_id"],
                            obis=current_object["obis"],
                            name=attr_name,
                            data_type=data_type,
                            description=f"Method of {current_object['name']} (method_id={method_id})",
                            attribute_id=-method_id,
                            unit="",
                            scaler=1.0,
                        )
                    else:
                        # 属性行
                        obj = CosemObject(
                            class_id=current_object["class_id"],
                            obis=current_object["obis"],
                            name=attr_name,
                            data_type=data_type,
                            description=f"Attribute of {current_object['name']}",
                            attribute_id=attr_id,
                            unit="",
                            scaler=1.0,
                        )
                        attr_count += 1

                    last_attr_id = attr_id
                    self._add_object(obj)
                    count += 1

            except Exception:
                # 跳过解析失败的行
                continue

        return count

    @staticmethod
    def _is_sabesp_object_header(a_val, d_val, f_val) -> bool:
        """
        判断一行是否为SABESP格式的对象标题行

        标题行特征:
        - A列为空
        - D列(IC/Class)有数字字符串值（class_id）
        - F列(OBIS code)有OBIS格式的值（A-B:C.D.E.F）

        Args:
            a_val: A列值
            d_val: D列值
            f_val: F列值

        Returns:
            bool: 是否为对象标题行
        """
        # A列为空
        if a_val is not None and str(a_val).strip() != "":
            return False

        # D列有数字字符串值
        if d_val is None:
            return False
        d_str = str(d_val).strip()
        if not d_str.isdigit():
            return False

        # F列有OBIS格式的值
        if f_val is None:
            return False
        f_str = str(f_val).strip()
        if not re.match(r'^\d+-\d+:\d+\.\d+\.\d+\.\d+$', f_str):
            return False

        return True

    @staticmethod
    def _parse_attribute_id(a_val) -> Optional[int]:
        """
        解析A列的属性/方法序号

        支持的格式:
        - 整数: 1, 2, 3 -> attribute_id = 1, 2, 3
        - 浮点数: 1.0, 2.1 -> 整数部分为attribute_id

        Args:
            a_val: A列值

        Returns:
            int 或 None: 解析后的属性ID
        """
        if a_val is None:
            return None

        if isinstance(a_val, int):
            return a_val

        if isinstance(a_val, float):
            return int(a_val)

        if isinstance(a_val, str):
            a_str = a_val.strip()
            if not a_str:
                return None
            # 尝试解析为整数
            try:
                return int(a_str)
            except ValueError:
                pass
            # 尝试解析为浮点数，取整数部分
            try:
                return int(float(a_str))
            except ValueError:
                return None

        return None

    def _add_object(self, obj: CosemObject):
        """
        添加对象到索引

        Args:
            obj: CosemObject对象
        """
        key = (obj.class_id, normalize_obis(obj.obis), obj.attribute_id or 0)
        self._objects[key] = obj
        self._all_objects.append(obj)

        # 按类ID索引
        if obj.class_id not in self._by_class:
            self._by_class[obj.class_id] = []
        self._by_class[obj.class_id].append(obj)

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
