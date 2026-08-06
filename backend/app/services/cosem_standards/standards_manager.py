"""
COSEM 标准库管理器

加载和管理所有 Class 的标准定义，提供统一的查询接口。
单例模式，全局只有一个实例。
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path


class StandardsManager:
    """COSEM 标准库管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Class 定义缓存: { (class_id, version): class_definition_dict }
        self._class_definitions: Dict[tuple, dict] = {}

        # 可用 Class 列表缓存: [ (class_id, version, class_name), ... ]
        self._available_classes: List[tuple] = []

        # Class JSON 文件目录
        self._classes_dir = Path(__file__).parent / "classes"

        # 自动加载所有可用的 Class 定义
        self._scan_available_classes()

    def _scan_available_classes(self):
        """扫描 classes 目录，找出所有可用的 Class 定义文件"""
        if not self._classes_dir.exists():
            return

        for filename in os.listdir(self._classes_dir):
            if not filename.endswith(".json"):
                continue
            if not filename.startswith("class_"):
                continue

            # 解析文件名: class_XXX_vY.json
            try:
                # class_007_v1.json -> (7, 1)
                parts = filename.replace(".json", "").split("_")
                if len(parts) >= 3:
                    class_id = int(parts[1])
                    version = int(parts[2].replace("v", ""))
                    class_name = self._peek_class_name(filename)
                    self._available_classes.append((class_id, version, class_name))
            except (ValueError, IndexError):
                continue

        # 按 class_id, version 排序
        self._available_classes.sort(key=lambda x: (x[0], x[1]))

    def _peek_class_name(self, filename: str) -> str:
        """快速查看 JSON 文件中的 class_name 字段（不完整加载）"""
        try:
            filepath = self._classes_dir / filename
            with open(filepath, "r", encoding="utf-8") as f:
                # 只读取前 500 字符，足够获取 class_name
                content = f.read(500)
                data = json.loads(content + "}" if "}" not in content else content)
                return data.get("class_name", "")
        except Exception:
            return ""

    def load_class_definition(self, class_id: int, version: int = 0) -> Optional[dict]:
        """
        加载指定 Class 版本的定义
        
        Args:
            class_id: Class ID
            version: 版本号
        
        Returns:
            Class 定义字典，加载失败返回 None
        """
        cache_key = (class_id, version)
        if cache_key in self._class_definitions:
            return self._class_definitions[cache_key]

        # 构造文件名
        filename = f"class_{class_id:03d}_v{version}.json"
        filepath = self._classes_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                class_def = json.load(f)
            self._class_definitions[cache_key] = class_def
            return class_def
        except (json.JSONDecodeError, IOError):
            return None

    def get_attribute_definition(self, class_id: int, version: int,
                                 attribute_id: int) -> Optional[dict]:
        """
        获取指定属性的定义
        
        Args:
            class_id: Class ID
            version: 版本号
            attribute_id: 属性 ID
        
        Returns:
            属性定义字典
        """
        class_def = self.load_class_definition(class_id, version)
        if not class_def:
            return None

        attributes = class_def.get("attributes", [])
        for attr in attributes:
            if attr.get("attribute_id") == attribute_id:
                return attr

        return None

    def get_method_definition(self, class_id: int, version: int,
                              method_id: int) -> Optional[dict]:
        """
        获取指定方法的定义
        
        Args:
            class_id: Class ID
            version: 版本号
            method_id: 方法 ID
        
        Returns:
            方法定义字典
        """
        class_def = self.load_class_definition(class_id, version)
        if not class_def:
            return None

        methods = class_def.get("methods", [])
        for m in methods:
            if m.get("method_id") == method_id:
                return m

        return None

    def list_available_classes(self) -> List[dict]:
        """
        列出所有可用的 Class
        
        Returns:
            [ { "class_id": 1, "version": 0, "class_name": "Data" }, ... ]
        """
        return [
            {
                "class_id": cid,
                "version": ver,
                "class_name": name,
            }
            for cid, ver, name in self._available_classes
        ]

    def list_class_versions(self, class_id: int) -> List[int]:
        """
        列出某个 Class 的所有可用版本
        
        Args:
            class_id: Class ID
        
        Returns:
            版本号列表，按升序排列
        """
        versions = [
            ver for cid, ver, _ in self._available_classes
            if cid == class_id
        ]
        versions.sort()
        return versions

    def get_latest_version(self, class_id: int) -> Optional[int]:
        """获取某个 Class 的最新版本号"""
        versions = self.list_class_versions(class_id)
        return versions[-1] if versions else None

    def get_class_name(self, class_id: int, version: int = None) -> str:
        """
        获取 Class 名称
        
        Args:
            class_id: Class ID
            version: 版本号（可选，不指定则用最新版本）
        
        Returns:
            Class 名称
        """
        if version is None:
            version = self.get_latest_version(class_id)
            if version is None:
                return f"Class {class_id}"

        class_def = self.load_class_definition(class_id, version)
        if class_def:
            return class_def.get("class_name", f"Class {class_id}")

        return f"Class {class_id}"

    def get_attribute_name(self, class_id: int, version: int, attribute_id: int) -> str:
        """
        获取属性名称
        
        Args:
            class_id: Class ID
            version: 版本号
            attribute_id: 属性 ID
        
        Returns:
            属性名称
        """
        attr_def = self.get_attribute_definition(class_id, version, attribute_id)
        if attr_def:
            return attr_def.get("name", f"attr_{attribute_id}")
        return f"attribute_{attribute_id}"

    def get_method_name(self, class_id: int, version: int, method_id: int) -> str:
        """
        获取方法名称
        
        Args:
            class_id: Class ID
            version: 版本号
            method_id: 方法 ID
        
        Returns:
            方法名称
        """
        method_def = self.get_method_definition(class_id, version, method_id)
        if method_def:
            return method_def.get("name", f"method_{method_id}")
        return f"method_{method_id}"

    def get_attribute_data_type(self, class_id: int, version: int,
                                attribute_id: int) -> str:
        """获取属性的数据类型"""
        attr_def = self.get_attribute_definition(class_id, version, attribute_id)
        if attr_def:
            return attr_def.get("data_type", "")
        return ""

    def get_element_structure(self, class_id: int, version: int,
                              attribute_id: int) -> Optional[List[dict]]:
        """
        获取复合属性的 element_structure（数组元素结构定义）
        
        适用于 array 类型的属性，如：
        - Profile Generic 的 capture_objects (attr 3)
        - Push Setup 的 push_object_list (attr 2)
        
        Args:
            class_id: Class ID
            version: 版本号
            attribute_id: 属性 ID
        
        Returns:
            element_structure 列表，每个元素是一个字段定义
        """
        attr_def = self.get_attribute_definition(class_id, version, attribute_id)
        if not attr_def:
            return None

        return attr_def.get("element_structure")

    def has_class(self, class_id: int, version: int = None) -> bool:
        """检查是否有指定 Class 的定义"""
        if version is not None:
            return self.load_class_definition(class_id, version) is not None

        return any(cid == class_id for cid, _, _ in self._available_classes)

    def get_all_class_definitions(self) -> Dict[int, Dict[int, dict]]:
        """
        获取所有 Class 的所有版本定义
        
        Returns:
            { class_id: { version: class_def } }
        """
        result: Dict[int, Dict[int, dict]] = {}
        for cid, ver, _ in self._available_classes:
            if cid not in result:
                result[cid] = {}
            class_def = self.load_class_definition(cid, ver)
            if class_def:
                result[cid][ver] = class_def
        return result

    def reload(self):
        """重新加载所有 Class 定义（清空缓存）"""
        self._class_definitions.clear()
        self._available_classes.clear()
        self._scan_available_classes()


# 全局单例实例
_standards_manager: Optional[StandardsManager] = None


def get_standards_manager() -> StandardsManager:
    """获取标准库管理器单例"""
    global _standards_manager
    if _standards_manager is None:
        _standards_manager = StandardsManager()
    return _standards_manager
