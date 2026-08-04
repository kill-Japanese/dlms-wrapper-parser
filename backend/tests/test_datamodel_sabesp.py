"""
SABESP格式数据模型解析测试

测试SABESP格式Excel文件的解析功能，验证:
1. 格式自动检测
2. 对象数量解析
3. 属性和方法的正确区分
4. OBIS匹配功能
"""
import os
import sys
import pytest

# 确保项目根目录在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.datamodel import DataModelManager
from app.utils.obis_utils import obis_str_to_bytes


# 测试文件路径
SABESP_EXCEL_PATH = '/workspace/.uploads/db31a5ba-19d9-4b3b-a197-1de376c26538_a2_SWM_Data_Model_DLMS_SABESP_Compressed_Push_DM1(1).xlsx'


@pytest.fixture
def sabesp_manager():
    """创建加载了SABESP格式Excel的DataModelManager实例"""
    # 重置单例
    DataModelManager._instance = None
    mgr = DataModelManager()

    # 检查测试文件是否存在
    if not os.path.exists(SABESP_EXCEL_PATH):
        pytest.skip(f"SABESP测试文件不存在: {SABESP_EXCEL_PATH}")

    mgr.load_excel(SABESP_EXCEL_PATH)
    return mgr


class TestSabespFormatDetection:
    """SABESP格式检测测试"""

    def test_detect_sabesp_format(self, sabesp_manager):
        """测试自动检测SABESP格式"""
        result = sabesp_manager.load_excel(SABESP_EXCEL_PATH)
        assert result.get("format") == "sabesp", "应检测为SABESP格式"

    def test_sabesp_file_loaded(self, sabesp_manager):
        """测试文件是否成功加载"""
        assert sabesp_manager.is_loaded, "数据模型应已加载"
        assert sabesp_manager.total_objects > 0, "应解析出对象"


class TestSabespObjectCount:
    """SABESP格式对象数量测试"""

    def test_total_objects(self, sabesp_manager):
        """测试总对象数量（包括对象本身、属性、方法）"""
        # SABESP格式有128个对象，每个对象有若干属性和方法
        # 总条目数 = 对象数 + 属性数 + 方法数
        total = sabesp_manager.total_objects
        assert total > 128, "总条目数应大于对象数（每个对象还有属性和方法）"
        assert total > 500, "总条目数应大于500"

    def test_object_headers_count(self, sabesp_manager):
        """测试对象标题行数量（attribute_id=0的对象）"""
        # 每个对象的attribute_id=0条目代表对象本身
        object_count = 0
        for obj in sabesp_manager._all_objects:
            if obj.attribute_id == 0:
                object_count += 1
        # SABESP文件有136个对象
        assert object_count == 136, f"应解析出136个对象，实际{object_count}个"
        assert object_count > 100, "对象数量应大于100"

    def test_classes_count(self, sabesp_manager):
        """测试类ID种类数量"""
        classes = sabesp_manager.get_classes()
        # SABESP文件包含多个不同的COSEM类
        assert len(classes) >= 15, f"类ID种类应不少于15个，实际{len(classes)}个"
        # 常见的类应该存在
        assert 1 in classes, "应包含Data类(class=1)"
        assert 3 in classes, "应包含Register类(class=3)"
        assert 8 in classes, "应包含Clock类(class=8)"
        assert 15 in classes, "应包含Association类(class=15)"


class TestSabespAttributeParsing:
    """SABESP格式属性解析测试"""

    def test_clock_attributes(self, sabesp_manager):
        """测试Clock对象的属性解析"""
        obis = obis_str_to_bytes('0-0:1.0.0.255')

        # 属性1: logical_name
        obj = sabesp_manager.match_obis(8, obis, 1)
        assert obj is not None, "应找到Clock的属性1"
        assert obj.name == "logical_name", f"属性1名称应为logical_name，实际{obj.name}"
        assert "octet_string" in obj.data_type.lower(), f"属性1类型应为octet_string，实际{obj.data_type}"

        # 属性2: time
        obj = sabesp_manager.match_obis(8, obis, 2)
        assert obj is not None, "应找到Clock的属性2"
        assert obj.name == "time", f"属性2名称应为time，实际{obj.name}"

        # 属性3: time_zone
        obj = sabesp_manager.match_obis(8, obis, 3)
        assert obj is not None, "应找到Clock的属性3"
        assert obj.name == "time_zone", f"属性3名称应为time_zone，实际{obj.name}"

    def test_current_association_attributes(self, sabesp_manager):
        """测试Current association对象的属性解析"""
        obis = obis_str_to_bytes('0-0:40.0.0.255')

        # 属性1: logical_name
        obj = sabesp_manager.match_obis(15, obis, 1)
        assert obj is not None, "应找到Current association的属性1"
        assert obj.name == "logical_name"

        # 属性2: object_list
        obj = sabesp_manager.match_obis(15, obis, 2)
        assert obj is not None, "应找到Current association的属性2"
        assert obj.name == "object_list"


class TestSabespMethodParsing:
    """SABESP格式方法解析测试"""

    def test_clock_methods(self, sabesp_manager):
        """测试Clock对象的方法解析（方法用负的attribute_id表示）"""
        obis = obis_str_to_bytes('0-0:1.0.0.255')

        # Clock有6个方法: adjust_to_quarter, adjust_to_measuring_period, etc.
        # 方法用负的attribute_id表示: -1, -2, ...
        obj = sabesp_manager.match_obis(8, obis, -1)
        assert obj is not None, "应找到Clock的方法1"
        assert "adjust_to_quarter" in obj.name, f"方法1应为adjust_to_quarter，实际{obj.name}"
        assert "Method" in obj.description, "方法的description应包含Method"

        obj = sabesp_manager.match_obis(8, obis, -2)
        assert obj is not None, "应找到Clock的方法2"
        assert "adjust_to_measuring_period" in obj.name, f"方法2应为adjust_to_measuring_period，实际{obj.name}"

    def test_current_association_methods(self, sabesp_manager):
        """测试Current association对象的方法解析"""
        obis = obis_str_to_bytes('0-0:40.0.0.255')

        # Current association有多个方法
        obj = sabesp_manager.match_obis(15, obis, -1)
        assert obj is not None, "应找到Current association的方法1"
        assert "reply_to_HLS_authentication" in obj.name or "reply" in obj.name.lower(), \
            f"方法1名称应为reply_to_HLS_authentication，实际{obj.name}"

        obj = sabesp_manager.match_obis(15, obis, -2)
        assert obj is not None, "应找到Current association的方法2"
        assert "change_HLS_secret" in obj.name, f"方法2名称应为change_HLS_secret，实际{obj.name}"


class TestSabespOBISMatching:
    """SABESP格式OBIS匹配测试"""

    def test_match_clock_object(self, sabesp_manager):
        """测试匹配Clock对象"""
        obis = obis_str_to_bytes('0-0:1.0.0.255')
        obj = sabesp_manager.match_obis(8, obis, 0)
        assert obj is not None, "应找到Clock对象"
        assert obj.class_id == 8, "类ID应为8"
        assert obj.name == "Clock", f"名称应为Clock，实际{obj.name}"

    def test_match_register_object(self, sabesp_manager):
        """测试匹配Register对象"""
        # 在SABESP文件中应该有多个Register对象 (class=3)
        objects = sabesp_manager.get_object_list(class_id=3, limit=5)
        assert len(objects) > 0, "应找到Register类对象"

        # 测试匹配第一个Register对象
        first_obj = objects[0]
        obis = obis_str_to_bytes(first_obj.obis)
        matched = sabesp_manager.match_obis(3, obis, 0)
        assert matched is not None, "应能通过OBIS匹配到Register对象"
        assert matched.name == first_obj.name

    def test_match_with_attribute_zero(self, sabesp_manager):
        """测试attribute_id=0时的通配匹配"""
        obis = obis_str_to_bytes('0-0:1.0.0.255')
        # attribute_id=0 应该匹配到对象本身（attribute_id=0的条目）
        obj = sabesp_manager.match_obis(8, obis, 0)
        assert obj is not None
        assert obj.attribute_id == 0


class TestSabespSearch:
    """SABESP格式搜索测试"""

    def test_search_by_name(self, sabesp_manager):
        """测试按名称搜索"""
        results = sabesp_manager.search("Clock", class_id=8, limit=10)
        assert len(results) > 0, "搜索Clock应返回结果"
        # 应包含Clock对象本身
        clock_obj = [r for r in results if r.attribute_id == 0 and r.name == "Clock"]
        assert len(clock_obj) > 0, "应找到Clock对象"

    def test_search_by_obis(self, sabesp_manager):
        """测试按OBIS码搜索"""
        results = sabesp_manager.search("0-0:1.0.0.255", limit=10)
        assert len(results) > 0, "搜索OBIS码应返回结果"

    def test_search_keyword(self, sabesp_manager):
        """测试关键词搜索"""
        results = sabesp_manager.search("voltage", limit=20)
        # 可能有也可能没有电压相关的对象，不做硬性断言
        # 只要不报错就行
        assert isinstance(results, list)


class TestSabespHeaderDetection:
    """SABESP格式标题行检测测试"""

    def test_is_sabesp_object_header(self):
        """测试对象标题行检测函数"""
        from app.services.datamodel import DataModelManager

        # 有效的标题行
        assert DataModelManager._is_sabesp_object_header(
            None, '8', '0-0:1.0.0.255'
        ) == True, "应识别为对象标题行"

        assert DataModelManager._is_sabesp_object_header(
            None, '15', '0-0:40.0.0.255'
        ) == True, "应识别为对象标题行"

        # 无效的 - A列有值
        assert DataModelManager._is_sabesp_object_header(
            1, '8', '0-0:1.0.0.255'
        ) == False, "A列有值不应识别为标题行"

        # 无效的 - D列不是数字
        assert DataModelManager._is_sabesp_object_header(
            None, 'Class', '0-0:1.0.0.255'
        ) == False, "D列不是数字不应识别为标题行"

        # 无效的 - F列不是OBIS格式
        assert DataModelManager._is_sabesp_object_header(
            None, '8', 'not_an_obis'
        ) == False, "F列不是OBIS格式不应识别为标题行"

        # 无效的 - D列为None
        assert DataModelManager._is_sabesp_object_header(
            None, None, '0-0:1.0.0.255'
        ) == False, "D列为None不应识别为标题行"

    def test_parse_attribute_id(self):
        """测试属性ID解析函数"""
        from app.services.datamodel import DataModelManager

        # 整数
        assert DataModelManager._parse_attribute_id(1) == 1
        assert DataModelManager._parse_attribute_id(10) == 10

        # 浮点数（取整数部分）
        assert DataModelManager._parse_attribute_id(1.0) == 1
        assert DataModelManager._parse_attribute_id(2.5) == 2

        # 字符串
        assert DataModelManager._parse_attribute_id("1") == 1
        assert DataModelManager._parse_attribute_id("3.1") == 3
        assert DataModelManager._parse_attribute_id("  5  ") == 5

        # None和空值
        assert DataModelManager._parse_attribute_id(None) is None
        assert DataModelManager._parse_attribute_id("") is None
        assert DataModelManager._parse_attribute_id("abc") is None


class TestSabespSpecificObjects:
    """SABESP格式特定对象验证测试"""

    def test_sap_assignment(self, sabesp_manager):
        """测试SAP assignment对象 (class=17)"""
        obis = obis_str_to_bytes('0-0:41.0.0.255')
        obj = sabesp_manager.match_obis(17, obis, 0)
        assert obj is not None, "应找到SAP assignment对象"
        assert "SAP" in obj.name or "sap" in obj.name.lower()

    def test_security_setup(self, sabesp_manager):
        """测试Security setup对象 (class=64)"""
        obis = obis_str_to_bytes('0-0:43.0.0.255')
        obj = sabesp_manager.match_obis(64, obis, 0)
        assert obj is not None, "应找到Security setup对象"
        assert "Security" in obj.name or "security" in obj.name.lower()

    def test_device_name(self, sabesp_manager):
        """测试COSEM logical device name对象"""
        obis = obis_str_to_bytes('0-0:42.0.0.255')
        obj = sabesp_manager.match_obis(1, obis, 0)
        assert obj is not None, "应找到COSEM logical device name对象"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
