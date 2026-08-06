"""
DLMS 单位编码标准定义（完整枚举 0-255）

基于 DLMS 蓝皮书 Ed.17 Part 2 Table 5 "Enumerated values for physical units"
"""

from typing import Dict, Optional


class UnitInfo:
    """单位信息"""

    def __init__(self, code: int, name: str, symbol: str, quantity: str = "",
                 si_definition: str = "", category: str = "", deprecated: bool = False):
        self.code = code
        self.name = name           # 单位名称（英文）
        self.symbol = symbol       # 符号
        self.quantity = quantity   # 量（物理量）
        self.si_definition = si_definition  # SI 定义说明
        self.category = category   # 分类：SI / 非SI / 保留 / 其他
        self.deprecated = deprecated  # 是否已废弃

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "si_definition": self.si_definition,
            "category": self.category,
            "deprecated": self.deprecated,
        }


# 完整的 0-255 单位编码表
# 来源: DLMS Blue Book Ed.17 Part 2, Table 5
DLMS_UNIT_CODES: Dict[int, UnitInfo] = {}


def _add(code: int, name: str, symbol: str, quantity: str = "",
         si_definition: str = "", category: str = "SI", deprecated: bool = False):
    """添加一个单位定义"""
    DLMS_UNIT_CODES[code] = UnitInfo(
        code=code,
        name=name,
        symbol=symbol,
        quantity=quantity,
        si_definition=si_definition,
        category=category,
        deprecated=deprecated,
    )


# === 0: 未使用 ===
_add(0, "unused", "", "", "", "reserved")

# === 1-72: SI 单位 ===
_add(1, "year", "a", "时间", "", "SI")
_add(2, "month", "mo", "时间", "", "SI")
_add(3, "week", "wk", "时间", "", "SI")
_add(4, "day", "d", "时间", "", "SI")
_add(5, "hour", "h", "时间", "", "SI")
_add(6, "minute", "min", "时间", "", "SI")
_add(7, "second", "s", "时间(t)", "", "SI")
_add(8, "degree", "°", "相位角", "", "SI")
_add(9, "degree-Celsius", "°C", "温度(ΔT)", "", "SI")
_add(10, "currency", "", "货币", "", "SI")
_add(11, "metre", "m", "长度(l)", "", "SI")
_add(12, "metre per second", "m/s", "速度(v)", "", "SI")
_add(13, "cubic metre", "m³", "体积(V)", "", "SI")
_add(14, "cubic metre corrected", "m³", "修正体积", "", "SI")
_add(15, "cubic metre per hour", "m³/h", "体积流量", "", "SI")
_add(16, "cubic metre per hour corrected", "m³/h", "修正体积流量", "", "SI", deprecated=True)
_add(17, "cubic metre per day", "m³/d", "体积流量", "", "SI")
_add(18, "cubic metre per day corrected", "m³/d", "修正体积流量", "", "SI", deprecated=True)
_add(19, "litre", "l", "体积", "", "SI")
_add(20, "kilogram", "kg", "质量(m)", "", "SI")
_add(21, "newton", "N", "力(F)", "", "SI")
_add(22, "newton meter", "Nm", "能量", "= J", "SI")
_add(23, "pascal", "Pa", "压力(p)", "", "SI")
_add(24, "bar", "bar", "压力(p)", "", "SI")
_add(25, "joule", "J", "能量", "", "SI")
_add(26, "joule per hour", "J/h", "热功率", "", "SI")
_add(27, "watt", "W", "有功功率(P)", "", "SI")
_add(28, "volt-ampere", "VA", "视在功率(S)", "", "SI")
_add(29, "var", "var", "无功功率(Q)", "含畸变功率", "SI")
_add(30, "watt-hour", "Wh", "有功电能", "", "SI")
_add(31, "volt-ampere-hour", "VAh", "视在电能", "", "SI")
_add(32, "var-hour", "varh", "无功电能", "含畸变电能", "SI")
_add(33, "ampere", "A", "电流(I)", "", "SI")
_add(34, "coulomb", "C", "电荷(Q)", "", "SI")
_add(35, "volt", "V", "电压(U)", "", "SI")
_add(36, "volt per metre", "V/m", "电场强度(E)", "", "SI")
_add(37, "farad", "F", "电容(C)", "", "SI")
_add(38, "ohm", "Ω", "电阻(R)", "", "SI")
_add(39, "ohm-metre", "Ω·m", "电阻率(ρ)", "", "SI")
_add(40, "weber", "Wb", "磁通量(Φ)", "", "SI")
_add(41, "tesla", "T", "磁通密度(B)", "", "SI")
_add(42, "ampere per metre", "A/m", "磁场强度(H)", "", "SI")
_add(43, "henry", "H", "电感(L)", "", "SI")
_add(44, "hertz", "Hz", "频率(f, ω)", "", "SI")
_add(45, "active energy meter constant", "1/Wh", "有功电表常数", "", "SI")
_add(46, "reactive energy meter constant", "1/varh", "无功电表常数", "", "SI")
_add(47, "apparent energy meter constant", "1/VAh", "视在电表常数", "", "SI")
_add(48, "volt-squared hour", "V²h", "电压平方时", "", "SI")
_add(49, "ampere-squared hour", "A²h", "电流平方时", "", "SI")
_add(50, "kilogram per second", "kg/s", "质量流量", "", "SI")
_add(51, "siemens", "S", "电导", "", "SI")
_add(52, "kelvin", "K", "温度(T)", "", "SI")
_add(53, "volt-squared hour meter constant", "1/V²h", "电压平方电表常数", "", "SI")
_add(54, "ampere-squared hour meter constant", "1/A²h", "电流平方电表常数", "", "SI")
_add(55, "volume meter constant", "1/m³", "体积电表常数", "", "SI")
_add(56, "percentage", "%", "百分比", "", "SI")
_add(57, "ampere-hour", "Ah", "安时", "", "SI")

# 58-59 保留
for i in range(58, 60):
    _add(i, "reserved", "", "", "", "reserved")

_add(60, "energy per volume", "Wh/m³", "体积能量密度", "", "SI")
_add(61, "calorific value", "J/m³", "热值/沃泊指数", "wobbe", "SI")
_add(62, "mole percent", "Mol %", "摩尔分数", "", "SI")
_add(63, "mass density", "g/m³", "质量密度", "", "SI")
_add(64, "pascal second", "Pa·s", "动力粘度", "", "SI")
_add(65, "specific energy", "J/kg", "比能量", "", "SI")
_add(66, "gram per square centimetre", "g/cm²", "压力", "", "SI")
_add(67, "atmosphere", "atm", "压力", "大气压", "SI")

# 68-69 保留
for i in range(68, 70):
    _add(i, "reserved", "", "", "", "reserved")

_add(70, "dB milliwatt", "dBm", "信号强度", "", "SI")
_add(71, "dB microvolt", "dBµV", "信号强度", "", "SI")
_add(72, "logarithmic ratio", "dB", "对数单位", "", "SI")

# 73-127 保留
for i in range(73, 128):
    _add(i, "reserved", "", "", "", "reserved")

# === 128-174: 非SI单位 ===
_add(128, "inch", "in", "长度(l)", "", "non-SI")
_add(129, "foot", "ft", "长度(l)", "", "non-SI")
_add(130, "pound", "lb", "质量(m)", "", "non-SI")
_add(131, "degree Fahrenheit", "°F", "温度", "", "non-SI")
_add(132, "degree Rankine", "°R", "温度", "", "non-SI")
_add(133, "square inch", "sq. in", "面积", "", "non-SI")
_add(134, "square foot", "sq ft", "面积", "", "non-SI")
_add(135, "acre", "ac", "面积", "", "non-SI")
_add(136, "cubic inch", "cu in", "体积", "", "non-SI")
_add(137, "cubic foot", "cu ft", "体积", "", "non-SI")
_add(138, "acre-foot", "ac ft", "体积", "", "non-SI")
_add(139, "gallon (imperial)", "gal (imp)", "体积", "英制加仑", "non-SI")
_add(140, "gallon (US)", "gal (US)", "体积", "美制加仑", "non-SI")
_add(141, "pound force", "lbf", "力", "", "non-SI")
_add(142, "Pound force per square inch", "psi", "压力(p)", "", "non-SI")
_add(143, "pound per cubic foot", "lb/cu ft", "密度", "", "non-SI")
_add(144, "pound per (foot second)", "lb/(ft·s)", "动力粘度", "", "non-SI")
_add(145, "square foot per second", "sq ft/s", "运动粘度", "", "non-SI")
_add(146, "British thermal unit", "Btu", "能量", "", "non-SI")
_add(147, "Therm (EU)", "thm(EC)", "能量", "", "non-SI")
_add(148, "Therm (US)", "thm(US)", "能量", "", "non-SI")
_add(149, "Btu per pound", "Btu/lb", "质量热值", "", "non-SI")
_add(150, "Btu per cubic foot", "Btu/cu ft", "体积热值", "", "non-SI")
_add(151, "cubic feet", "cu ft", "体积", "", "non-SI")
_add(152, "foot per second", "ft/s", "速度(v)", "", "non-SI")
_add(153, "cubic foot per second", "cu ft/s", "体积流量", "", "non-SI")
_add(154, "cubic foot per minute", "cu ft/min", "体积流量", "", "non-SI")
_add(155, "cubic foot per hour", "cu ft/h", "体积流量", "", "non-SI")
_add(156, "cubic foot per day", "cu ft/d", "体积流量", "", "non-SI")
_add(157, "acre foot per second", "ac ft/s", "体积流量", "", "non-SI")
_add(158, "acre foot per minute", "ac ft/min", "体积流量", "", "non-SI")
_add(159, "acre foot per hour", "ac ft/h", "体积流量", "", "non-SI")
_add(160, "acre foot per day", "ac ft/d", "体积流量", "", "non-SI")
_add(161, "imperial gallon", "gal (imp)", "体积", "", "non-SI")
_add(162, "imperial gallon per second", "gal(imp)/s", "体积流量", "", "non-SI")
_add(163, "imperial gallon per minute", "gal(imp)/min", "体积流量", "", "non-SI")
_add(164, "imperial gallon per hour", "gal(imp)/h", "体积流量", "", "non-SI")
_add(165, "imperial gallon per day", "gal(imp)/d", "体积流量", "", "non-SI")
_add(166, "US gallon", "gal (US)", "体积", "", "non-SI")
_add(167, "US gallon per second", "gal(US)/s", "体积流量", "", "non-SI")
_add(168, "US gallon per minute", "gal(US)/min", "体积流量", "", "non-SI")
_add(169, "US gallon per hour", "gal(US)/h", "体积流量", "", "non-SI")
_add(170, "US gallon per day", "gal(US)/d", "体积流量", "", "non-SI")
_add(171, "Btu per second", "Btu/s", "能流/热/功率", "", "non-SI")
_add(172, "Btu per minute", "Btu/min", "能流/热/功率", "", "non-SI")
_add(173, "Btu per hour", "Btu/h", "能流/热/功率", "", "non-SI")
_add(174, "Btu per day", "Btu/d", "能流/热/功率", "", "non-SI")

# 175-252 保留
for i in range(175, 253):
    _add(i, "reserved", "", "", "", "reserved")

# === 253-255: 特殊值 ===
_add(253, "extended table of units", "", "扩展单位表", "", "other")
_add(254, "other unit", "other", "其他单位", "", "other")
_add(255, "no unit (count)", "count", "无单位/计数", "unitless", "other")


def get_unit_info(code: int) -> Optional[UnitInfo]:
    """获取单位信息"""
    return DLMS_UNIT_CODES.get(code)


def get_unit_name(code: int) -> str:
    """获取单位名称"""
    info = DLMS_UNIT_CODES.get(code)
    return info.name if info else f"unknown({code})"


def get_unit_symbol(code: int) -> str:
    """获取单位符号"""
    info = DLMS_UNIT_CODES.get(code)
    return info.symbol if info else ""


def get_all_units() -> Dict[int, UnitInfo]:
    """获取所有单位"""
    return DLMS_UNIT_CODES


def get_units_by_category(category: str) -> Dict[int, UnitInfo]:
    """按分类获取单位"""
    return {
        code: info for code, info in DLMS_UNIT_CODES.items()
        if info.category == category
    }


def parse_scaler_unit(scaler_unit_bytes: bytes) -> dict:
    """
    解析 scaler_unit 结构（2 字节 octet_string）
    
    DLMS 中 scaler_unit 的编码：
    - 第 1 字节（高 8 位）：scaler（8 位有符号整数，10 的指数）
    - 第 2 字节（低 8 位）：unit（8 位无符号整数，单位编码）
    
    Args:
        scaler_unit_bytes: 2 字节的 octet_string 数据
    
    Returns:
        {
            "scaler": int,          # 量纲指数（如 -3 表示 ×10^-3）
            "scaler_value": float,  # 缩放倍率（如 0.001）
            "unit_code": int,       # 单位编码
            "unit_name": str,       # 单位名称
            "unit_symbol": str,     # 单位符号
            "unit_category": str,   # 单位分类
        }
    """
    if len(scaler_unit_bytes) < 2:
        raise ValueError(f"scaler_unit 需要至少 2 字节，实际 {len(scaler_unit_bytes)} 字节")

    # scaler: 8位有符号整数
    scaler_raw = scaler_unit_bytes[0]
    if scaler_raw >= 128:  # 负数（补码）
        scaler = scaler_raw - 256
    else:
        scaler = scaler_raw

    # unit: 8位无符号整数
    unit_code = scaler_unit_bytes[1]
    unit_info = get_unit_info(unit_code)

    return {
        "scaler": scaler,
        "scaler_value": 10 ** scaler,
        "unit_code": unit_code,
        "unit_name": unit_info.name if unit_info else f"unknown({unit_code})",
        "unit_symbol": unit_info.symbol if unit_info else "",
        "unit_category": unit_info.category if unit_info else "unknown",
    }


def build_scaler_unit(scaler: int, unit_code: int) -> bytes:
    """
    构建 scaler_unit 结构（2 字节 octet_string）
    
    Args:
        scaler: 量纲指数（-128 ~ 127）
        unit_code: 单位编码（0 ~ 255）
    
    Returns:
        2 字节的 octet_string 数据
    """
    # scaler: 8位有符号整数
    if scaler < 0:
        scaler_byte = scaler + 256
    else:
        scaler_byte = scaler
    scaler_byte = scaler_byte & 0xFF

    # unit: 8位无符号整数
    unit_byte = unit_code & 0xFF

    return bytes([scaler_byte, unit_byte])


def format_value_with_scaler_unit(raw_value: float, scaler_unit_bytes: bytes,
                                  auto_prefix: bool = True) -> str:
    """
    使用 scaler_unit 格式化数值
    
    Args:
        raw_value: 原始值
        scaler_unit_bytes: 2 字节 scaler_unit
        auto_prefix: 是否自动换算量纲前缀（k, M, G, m, µ, n 等）
    
    Returns:
        格式化后的字符串，如 "12.345 kW"
    """
    info = parse_scaler_unit(scaler_unit_bytes)
    scaled_value = raw_value * info["scaler_value"]
    unit_symbol = info["unit_symbol"]

    if not auto_prefix or not unit_symbol:
        return f"{scaled_value} {unit_symbol}".strip()

    # 自动换算量纲前缀
    abs_value = abs(scaled_value)
    prefix = ""
    if abs_value >= 1e9:
        scaled_value /= 1e9
        prefix = "G"
    elif abs_value >= 1e6:
        scaled_value /= 1e6
        prefix = "M"
    elif abs_value >= 1e3:
        scaled_value /= 1e3
        prefix = "k"
    elif abs_value < 1e-6:
        scaled_value *= 1e9
        prefix = "n"
    elif abs_value < 1e-3:
        scaled_value *= 1e6
        prefix = "µ"
    elif abs_value < 1:
        scaled_value *= 1e3
        prefix = "m"

    # 保留合适的小数位
    if abs(scaled_value) >= 100:
        formatted = f"{scaled_value:.1f}"
    elif abs(scaled_value) >= 10:
        formatted = f"{scaled_value:.2f}"
    else:
        formatted = f"{scaled_value:.3f}"

    # 去掉末尾多余的0
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    return f"{formatted} {prefix}{unit_symbol}".strip()
