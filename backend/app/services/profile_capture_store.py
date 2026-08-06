"""
Profile Generic capture_objects 手动配置存储

用户可以手动为 Profile Generic 对象注入 capture_objects 配置，
当数模中没有该对象或属性3缺失时使用。
配置持久化保存，下次解析时自动使用。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class CaptureObject:
    """单个 capture object 定义"""

    def __init__(self, class_id: int, instance_id: str, attribute_id: int,
                 data_index: int = 0, remark: str = ""):
        self.class_id = class_id
        self.instance_id = instance_id  # OBIS 格式字符串
        self.attribute_id = attribute_id
        self.data_index = data_index
        self.remark = remark  # 用户备注

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "instance_id": self.instance_id,
            "attribute_id": self.attribute_id,
            "data_index": self.data_index,
            "remark": self.remark,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CaptureObject":
        return cls(
            class_id=data.get("class_id", 0),
            instance_id=data.get("instance_id", ""),
            attribute_id=data.get("attribute_id", 0),
            data_index=data.get("data_index", 0),
            remark=data.get("remark", ""),
        )


class ProfileCaptureConfig:
    """一个 Profile Generic 对象的 capture_objects 配置"""

    def __init__(self, profile_obis: str, profile_name: str = "",
                 capture_objects: List[CaptureObject] = None,
                 source: str = "manual"):
        self.profile_obis = profile_obis
        self.profile_name = profile_name
        self.capture_objects = capture_objects or []
        self.source = source  # manual / data_model / pull / standard
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.used_count = 0

    def to_dict(self) -> dict:
        return {
            "profile_obis": self.profile_obis,
            "profile_name": self.profile_name,
            "capture_objects": [co.to_dict() for co in self.capture_objects],
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "used_count": self.used_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileCaptureConfig":
        config = cls(
            profile_obis=data.get("profile_obis", ""),
            profile_name=data.get("profile_name", ""),
            capture_objects=[
                CaptureObject.from_dict(co)
                for co in data.get("capture_objects", [])
            ],
            source=data.get("source", "manual"),
        )
        config.created_at = data.get("created_at", config.created_at)
        config.updated_at = data.get("updated_at", config.updated_at)
        config.used_count = data.get("used_count", 0)
        return config


class ProfileCaptureStore:
    """
    Profile capture_objects 配置存储管理器
    
    以 Profile OBIS 为 key 存储配置，支持：
    - CRUD 操作
    - 导入导出
    - 持久化存储（JSON 文件）
    """

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

        # 配置缓存: { profile_obis: ProfileCaptureConfig }
        self._configs: Dict[str, ProfileCaptureConfig] = {}

        # 存储文件路径
        self._storage_dir = Path(__file__).parent / "data"
        self._storage_file = self._storage_dir / "profile_capture_configs.json"

        # 确保目录存在
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # 加载已有配置
        self._load_from_file()

    def _load_from_file(self):
        """从文件加载配置"""
        if not self._storage_file.exists():
            return

        try:
            with open(self._storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for obis, config_data in data.items():
                    self._configs[obis] = ProfileCaptureConfig.from_dict(config_data)
        except (json.JSONDecodeError, IOError):
            pass

    def _save_to_file(self):
        """保存配置到文件"""
        try:
            data = {
                obis: config.to_dict()
                for obis, config in self._configs.items()
            }
            with open(self._storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    @staticmethod
    def _normalize_obis_key(obis: str) -> str:
        """将 OBIS 字符串标准化为统一格式 (A-B:C.D.E.F) 用于比较

        处理不同格式:
        - "1-0:1.8.0.255" (标准)
        - "1.0.1.8.0.255" (点分隔)
        - "1-0:1.8.0*255" (星号分隔)
        - "0100010800FF"  (十六进制)
        """
        if not obis:
            return ""
        try:
            from app.utils.obis_utils import normalize_obis
            parts = normalize_obis(obis)
            return f"{parts[0]}-{parts[1]}:{parts[2]}.{parts[3]}.{parts[4]}.{parts[5]}"
        except Exception:
            return obis.strip().lower()

    def get_config(self, profile_obis: str) -> Optional[ProfileCaptureConfig]:
        """
        获取指定 Profile 的 capture_objects 配置
        
        支持模糊匹配：先精确匹配，再尝试标准化后的 OBIS 匹配。
        
        Args:
            profile_obis: Profile Generic 对象的 OBIS
        
        Returns:
            配置对象，不存在返回 None
        """
        # 精确匹配
        config = self._configs.get(profile_obis)
        if not config:
            # 标准化模糊匹配
            norm_key = self._normalize_obis_key(profile_obis)
            for stored_obis, stored_config in self._configs.items():
                if self._normalize_obis_key(stored_obis) == norm_key:
                    config = stored_config
                    break
        if config:
            # 更新使用次数
            config.used_count += 1
            config.updated_at = datetime.now().isoformat()
            self._save_to_file()
        return config

    def get_capture_objects(self, profile_obis: str) -> Optional[List[dict]]:
        """
        获取指定 Profile 的 capture_objects 列表（字典格式）
        
        方便直接用于解析。
        
        Args:
            profile_obis: Profile Generic 对象的 OBIS
        
        Returns:
            capture_objects 字典列表，不存在返回 None
        """
        config = self.get_config(profile_obis)
        if not config:
            return None

        return [co.to_dict() for co in config.capture_objects]

    def save_config(self, profile_obis: str, capture_objects: List[dict],
                    profile_name: str = "", source: str = "manual") -> ProfileCaptureConfig:
        """
        保存/更新 Profile 的 capture_objects 配置
        
        Args:
            profile_obis: Profile Generic 对象的 OBIS
            capture_objects: capture_objects 列表（字典格式）
            profile_name: 用户自定义名称（可选）
            source: 配置来源
        
        Returns:
            保存后的配置对象
        """
        if profile_obis in self._configs:
            config = self._configs[profile_obis]
            config.capture_objects = [
                CaptureObject.from_dict(co) for co in capture_objects
            ]
            if profile_name:
                config.profile_name = profile_name
            config.source = source
            config.updated_at = datetime.now().isoformat()
        else:
            config = ProfileCaptureConfig(
                profile_obis=profile_obis,
                profile_name=profile_name,
                capture_objects=[
                    CaptureObject.from_dict(co) for co in capture_objects
                ],
                source=source,
            )
            self._configs[profile_obis] = config

        self._save_to_file()
        return config

    def delete_config(self, profile_obis: str) -> bool:
        """
        删除指定 Profile 的配置
        
        Returns:
            是否删除成功
        """
        if profile_obis in self._configs:
            del self._configs[profile_obis]
            self._save_to_file()
            return True
        return False

    def list_configs(self) -> List[dict]:
        """
        获取所有配置列表
        
        Returns:
            配置列表（字典格式，不含详细 capture_objects）
        """
        return [
            {
                "profile_obis": config.profile_obis,
                "profile_name": config.profile_name,
                "source": config.source,
                "capture_object_count": len(config.capture_objects),
                "created_at": config.created_at,
                "updated_at": config.updated_at,
                "used_count": config.used_count,
            }
            for config in self._configs.values()
        ]

    def get_config_detail(self, profile_obis: str) -> Optional[dict]:
        """获取配置详情（含完整 capture_objects）"""
        config = self._configs.get(profile_obis)
        return config.to_dict() if config else None

    def import_configs(self, configs_data: dict, overwrite: bool = True) -> int:
        """
        批量导入配置
        
        Args:
            configs_data: { profile_obis: config_dict, ... }
            overwrite: 是否覆盖已有配置
        
        Returns:
            导入的配置数量
        """
        count = 0
        for obis, config_data in configs_data.items():
            if not overwrite and obis in self._configs:
                continue
            self._configs[obis] = ProfileCaptureConfig.from_dict(config_data)
            count += 1

        if count > 0:
            self._save_to_file()
        return count

    def export_configs(self) -> dict:
        """导出所有配置"""
        return {
            obis: config.to_dict()
            for obis, config in self._configs.items()
        }

    def has_config(self, profile_obis: str) -> bool:
        """检查是否有指定 Profile 的配置（支持模糊匹配）"""
        if profile_obis in self._configs:
            return True
        norm_key = self._normalize_obis_key(profile_obis)
        for stored_obis in self._configs:
            if self._normalize_obis_key(stored_obis) == norm_key:
                return True
        return False

    def clear_all(self):
        """清空所有配置（慎用）"""
        self._configs.clear()
        self._save_to_file()


# 全局单例
_profile_capture_store: Optional[ProfileCaptureStore] = None


def get_profile_capture_store() -> ProfileCaptureStore:
    """获取 Profile Capture Store 单例"""
    global _profile_capture_store
    if _profile_capture_store is None:
        _profile_capture_store = ProfileCaptureStore()
    return _profile_capture_store
