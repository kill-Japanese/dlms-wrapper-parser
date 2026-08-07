"""
Pull操作路由 - 管理预设Pull操作和执行GetRequest
"""
import uuid
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.services.apdu_parser import build_apdu, parse_apdu
from app.services.wrapper import build_wpd
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes
from app.utils.obis_utils import obis_str_to_bytes


router = APIRouter(prefix="/api/pull", tags=["Pull"])


# ---------- 数据模型 ----------

class PullOperationItem(BaseModel):
    """Pull操作项"""
    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码 (A-B:C.D.E.F格式)")
    attribute_id: int = Field(default=2, description="属性ID")
    name: str = Field(default="", description="名称")


class PullPreset(BaseModel):
    """Pull预设"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="预设ID")
    name: str = Field(description="预设名称")
    description: str = Field(default="", description="描述")
    system_title: Optional[str] = Field(default=None, description="目标设备System Title (8字节十六进制)")
    device_name: Optional[str] = Field(default=None, description="目标设备名称")
    key_type: Optional[str] = Field(default="GUEK", description="密钥类型: GUEK/GUBK")
    operations: List[PullOperationItem] = Field(default_factory=list, description="操作列表")


class PullPresetUpdate(BaseModel):
    """Pull预设更新"""
    name: Optional[str] = Field(default=None, description="预设名称")
    description: Optional[str] = Field(default=None, description="描述")
    system_title: Optional[str] = Field(default=None, description="目标设备System Title")
    device_name: Optional[str] = Field(default=None, description="目标设备名称")
    key_type: Optional[str] = Field(default=None, description="密钥类型: GUEK/GUBK")
    operations: Optional[List[PullOperationItem]] = Field(default=None, description="操作列表")


class BuildGetRequestRequest(BaseModel):
    """构建单个GetRequest请求"""
    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码")
    attribute_id: int = Field(default=2, description="属性ID")
    invoke_id: int = Field(default=1, description="调用ID")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class ExecutePresetRequest(BaseModel):
    """执行预设Pull操作请求"""
    preset_id: str = Field(description="预设ID")
    use_with_list: bool = Field(default=True, description="是否使用WithList模式")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")
    system_title: Optional[str] = Field(default=None, description="覆盖预设的System Title")


class ExecuteOperationsRequest(BaseModel):
    """直接执行操作列表请求"""
    operations: List[PullOperationItem] = Field(description="操作列表")
    use_with_list: bool = Field(default=True, description="是否使用WithList模式")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


# ---------- 内存存储 ----------

_presets: dict[str, PullPreset] = {}


def _init_default_presets():
    """初始化默认预设"""
    if not _presets:
        default_preset = PullPreset(
            id="default-electricity",
            name="电表基础数据",
            description="读取电表的基础电能数据",
            system_title=None,
            device_name=None,
            key_type="GUEK",
            operations=[
                PullOperationItem(
                    class_id=3,
                    obis="1.0.1.8.0.255",
                    attribute_id=2,
                    name="有功总电能（正向）"
                ),
                PullOperationItem(
                    class_id=3,
                    obis="1.0.2.8.0.255",
                    attribute_id=2,
                    name="有功总电能（反向）"
                ),
                PullOperationItem(
                    class_id=1,
                    obis="1.0.32.7.0.255",
                    attribute_id=2,
                    name="电压"
                ),
                PullOperationItem(
                    class_id=1,
                    obis="1.0.31.7.0.255",
                    attribute_id=2,
                    name="电流"
                ),
            ]
        )
        _presets[default_preset.id] = default_preset


_init_default_presets()


# ---------- 路由 ----------

@router.get("/presets", summary="获取预设Pull操作列表")
async def get_presets():
    """
    获取所有预设Pull操作列表
    """
    try:
        preset_list = [preset.model_dump() for preset in _presets.values()]
        return {
            "success": True,
            "presets": preset_list,
            "total": len(preset_list),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预设列表失败: {e}")


@router.get("/presets/{preset_id}", summary="获取单个预设详情")
async def get_preset(preset_id: str):
    """
    获取单个预设的详细信息
    """
    try:
        preset = _presets.get(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail=f"预设 {preset_id} 不存在")
        return {
            "success": True,
            "preset": preset.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预设详情失败: {e}")


@router.put("/presets", summary="保存预设Pull操作列表")
async def save_presets(
    presets: List[PullPreset] = Body(..., description="预设列表"),
):
    """
    批量保存预设Pull操作列表（全量替换）
    """
    try:
        global _presets
        _presets = {p.id: p for p in presets}
        return {
            "success": True,
            "message": "预设列表已保存",
            "total": len(_presets),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存预设列表失败: {e}")


@router.post("/presets", summary="创建新预设")
async def create_preset(preset: PullPreset):
    """
    创建一个新的Pull预设
    """
    try:
        # 如果没有提供ID，自动生成
        if not preset.id or preset.id in _presets:
            preset.id = str(uuid.uuid4())
        _presets[preset.id] = preset
        return {
            "success": True,
            "preset": preset.model_dump(),
            "message": "预设已创建",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建预设失败: {e}")


@router.put("/presets/{preset_id}", summary="更新预设")
async def update_preset(
    preset_id: str,
    update: PullPresetUpdate,
):
    """
    更新指定预设的信息
    """
    try:
        preset = _presets.get(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail=f"预设 {preset_id} 不存在")

        update_data = update.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(preset, key, value)

        return {
            "success": True,
            "preset": preset.model_dump(),
            "message": "预设已更新",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新预设失败: {e}")


@router.delete("/presets/{preset_id}", summary="删除预设")
async def delete_preset(preset_id: str):
    """
    删除指定的Pull预设
    """
    try:
        if preset_id not in _presets:
            raise HTTPException(status_code=404, detail=f"预设 {preset_id} 不存在")
        del _presets[preset_id]
        return {
            "success": True,
            "message": "预设已删除",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除预设失败: {e}")


@router.post("/build-request", summary="构建单个GetRequest帧")
async def build_get_request(request: BuildGetRequestRequest):
    """
    构建单个GetRequest APDU帧（Normal模式）

    返回构造的十六进制帧数据
    """
    try:
        # 构建APDU
        apdu_data = build_apdu("get-request", {
            "get_type": 1,  # normal
            "invoke_id": request.invoke_id,
            "class_id": request.class_id,
            "obis": request.obis,
            "attribute_id": request.attribute_id,
        })

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        # 可选封装Wrapper
        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建GetRequest失败: {e}")


@router.post("/execute", summary="执行预设Pull操作")
async def execute_preset(request: ExecutePresetRequest):
    """
    执行预设Pull操作，构造GetRequest帧

    - use_with_list=True: 使用GetRequest WithList模式，一次请求多个对象
    - use_with_list=False: 为每个对象单独构造GetRequest Normal帧
    """
    try:
        preset = _presets.get(request.preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail=f"预设 {request.preset_id} 不存在")

        operations = [op.model_dump() for op in preset.operations]

        # 确定使用的 system_title: 请求参数优先，其次使用预设配置
        system_title = request.system_title or preset.system_title

        result = await _execute_operations_internal(
            operations=operations,
            use_with_list=request.use_with_list,
            with_wrapper=request.with_wrapper,
            src_wport=request.src_wport,
            dst_wport=request.dst_wport,
            preset_name=preset.name,
            preset_id=preset.id,
        )

        # 在结果中附加设备信息
        result["system_title"] = system_title
        result["device_name"] = preset.device_name
        result["key_type"] = preset.key_type

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行预设失败: {e}")


@router.post("/execute-operations", summary="执行操作列表")
async def execute_operations(request: ExecuteOperationsRequest):
    """
    直接执行一组操作（不通过预设）

    用于临时测试或从其他页面快速执行
    """
    try:
        operations = [op.model_dump() for op in request.operations]
        return await _execute_operations_internal(
            operations=operations,
            use_with_list=request.use_with_list,
            with_wrapper=request.with_wrapper,
            src_wport=request.src_wport,
            dst_wport=request.dst_wport,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行操作失败: {e}")


async def _execute_operations_internal(
    operations: list,
    use_with_list: bool,
    with_wrapper: bool,
    src_wport: int,
    dst_wport: int,
    preset_name: Optional[str] = None,
    preset_id: Optional[str] = None,
) -> dict:
    """
    内部方法：执行操作列表，构造帧数据

    Args:
        operations: 操作列表
        use_with_list: 是否使用WithList模式
        with_wrapper: 是否封装Wrapper帧
        src_wport: 源WPort
        dst_wport: 目的WPort
        preset_name: 预设名称（可选）
        preset_id: 预设ID（可选）

    Returns:
        dict: 执行结果
    """
    if not operations:
        raise HTTPException(status_code=400, detail="操作列表不能为空")

    frames = []

    if use_with_list:
        # WithList模式：一个请求包含多个对象
        apdu_data = build_apdu("get-request", {
            "get_type": 3,  # with-list
            "invoke_id": 1,
            "attribute_list": operations,
        })

        frame_info = {
            "type": "with_list",
            "invoke_id": 1,
            "operation_count": len(operations),
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=src_wport, dst_wport=dst_wport)
            frame_info["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            frame_info["wrapper_length"] = len(wrapper_frame)

        frames.append(frame_info)
    else:
        # Normal模式：每个对象一个请求
        for i, op in enumerate(operations):
            apdu_data = build_apdu("get-request", {
                "get_type": 1,  # normal
                "invoke_id": i + 1,
                "class_id": op["class_id"],
                "obis": op["obis"],
                "attribute_id": op["attribute_id"],
            })

            frame_info = {
                "type": "normal",
                "invoke_id": i + 1,
                "class_id": op["class_id"],
                "obis": op["obis"],
                "attribute_id": op["attribute_id"],
                "name": op.get("name", ""),
                "apdu_hex": bytes_to_hex(apdu_data),
                "apdu_length": len(apdu_data),
            }

            if with_wrapper:
                wrapper_frame = build_wpd(apdu_data, src_wport=src_wport, dst_wport=dst_wport)
                frame_info["wrapper_hex"] = bytes_to_hex(wrapper_frame)
                frame_info["wrapper_length"] = len(wrapper_frame)

            frames.append(frame_info)

    result = {
        "success": True,
        "use_with_list": use_with_list,
        "operation_count": len(operations),
        "frame_count": len(frames),
        "frames": frames,
    }

    if preset_name:
        result["preset_name"] = preset_name
    if preset_id:
        result["preset_id"] = preset_id

    return result


# ---------- Pull 模式扩展端点 ----------

class BuildSetRequestRequest(BaseModel):
    """构建SetRequest请求"""
    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码")
    attribute_id: int = Field(default=2, description="属性ID")
    value: Any = Field(default=None, description="设置值")
    data_type: Optional[str] = Field(default=None, description="值数据类型")
    invoke_id: int = Field(default=1, description="调用ID")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class BuildActionRequestRequest(BaseModel):
    """构建ActionRequest请求"""
    class_id: int = Field(description="类ID")
    obis: str = Field(description="OBIS码")
    method_id: int = Field(default=1, description="方法ID")
    value: Optional[Any] = Field(default=None, description="方法参数")
    data_type: Optional[str] = Field(default=None, description="参数数据类型")
    invoke_id: int = Field(default=1, description="调用ID")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class ParseApduRequest(BaseModel):
    """解析APDU请求"""
    hex_data: str = Field(description="APDU十六进制数据")
    with_wrapper: bool = Field(default=False, description="是否包含Wrapper帧")


class BuildSetResponseRequest(BaseModel):
    """构建SetResponse请求"""
    set_type: int = Field(default=1, description="Set响应类型 (1=normal)")
    invoke_id: int = Field(default=1, description="调用ID")
    result_code: int = Field(default=0, description="结果码 (0=成功, 其他=错误码)")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class BuildActionResponseRequest(BaseModel):
    """构建ActionResponse请求"""
    action_type: int = Field(default=1, description="Action响应类型 (1=normal)")
    invoke_id: int = Field(default=1, description="调用ID")
    result_code: int = Field(default=0, description="结果码 (0=成功, 其他=错误码)")
    value: Optional[Any] = Field(default=None, description="返回数据")
    data_type: Optional[str] = Field(default=None, description="返回数据类型")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class BuildGetResponseRequest(BaseModel):
    """构建GetResponse请求"""
    get_type: int = Field(default=1, description="Get响应类型 (1=normal, 2=next, 3=with-list)")
    invoke_id: int = Field(default=1, description="调用ID")
    result_code: int = Field(default=0, description="结果码 (0=data, 1=datablock, 其他=error)")
    value: Optional[Any] = Field(default=None, description="返回值 (result_code=0时)")
    data_type: Optional[str] = Field(default=None, description="数据类型")
    last_block: bool = Field(default=False, description="是否为最后一块 (result_code=1时)")
    block_number: int = Field(default=0, description="块号 (result_code=1时)")
    raw_data: Optional[str] = Field(default=None, description="块数据十六进制 (result_code=1时)")
    results: Optional[List[dict]] = Field(default=None, description="结果列表 (get_type=3时)")
    with_wrapper: bool = Field(default=True, description="是否封装Wrapper帧")
    src_wport: int = Field(default=1, description="源WPort")
    dst_wport: int = Field(default=16, description="目的WPort")


class ExtractCaptureObjectsRequest(BaseModel):
    """从GetResponse提取capture_objects请求"""
    hex_data: str = Field(description="GetResponse的APDU十六进制数据")


@router.post("/build-set-request", summary="构建SetRequest帧")
async def build_set_request_endpoint(request: BuildSetRequestRequest):
    """
    构建SetRequest APDU帧（Normal模式）
    """
    try:
        apdu_data = build_apdu("set-request", {
            "set_type": 1,
            "invoke_id": request.invoke_id,
            "class_id": request.class_id,
            "obis": request.obis,
            "attribute_id": request.attribute_id,
            "value": request.value,
            "data_type": request.data_type,
        })

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建SetRequest失败: {e}")


@router.post("/build-action-request", summary="构建ActionRequest帧")
async def build_action_request_endpoint(request: BuildActionRequestRequest):
    """
    构建ActionRequest APDU帧（Normal模式）
    """
    try:
        apdu_data = build_apdu("action-request", {
            "action_type": 1,
            "invoke_id": request.invoke_id,
            "class_id": request.class_id,
            "obis": request.obis,
            "method_id": request.method_id,
            "value": request.value,
            "data_type": request.data_type,
        })

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建ActionRequest失败: {e}")


@router.post("/build-get-response", summary="构建GetResponse帧")
async def build_get_response_endpoint(request: BuildGetResponseRequest):
    """
    构建GetResponse APDU帧（支持Normal/Next/WithList模式）
    """
    try:
        params = {
            "get_type": request.get_type,
            "invoke_id": request.invoke_id,
            "result_code": request.result_code,
        }

        if request.get_type == 1 and request.result_code == 0:
            params["value"] = request.value
            params["data_type"] = request.data_type
        elif request.get_type in (1, 2) and request.result_code == 1:
            params["last_block"] = request.last_block
            params["block_number"] = request.block_number
            if request.raw_data:
                params["raw_data"] = hex_to_bytes(request.raw_data)
        elif request.get_type == 3:
            params["results"] = request.results or []

        apdu_data = build_apdu("get-response", params)

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建GetResponse失败: {e}")


@router.post("/build-set-response", summary="构建SetResponse帧")
async def build_set_response_endpoint(request: BuildSetResponseRequest):
    """
    构建SetResponse APDU帧
    """
    try:
        apdu_data = build_apdu("set-response", {
            "set_type": request.set_type,
            "invoke_id": request.invoke_id,
            "result_code": request.result_code,
        })

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建SetResponse失败: {e}")


@router.post("/build-action-response", summary="构建ActionResponse帧")
async def build_action_response_endpoint(request: BuildActionResponseRequest):
    """
    构建ActionResponse APDU帧
    """
    try:
        apdu_data = build_apdu("action-response", {
            "action_type": request.action_type,
            "invoke_id": request.invoke_id,
            "result_code": request.result_code,
            "value": request.value,
            "data_type": request.data_type,
        })

        result = {
            "success": True,
            "apdu_hex": bytes_to_hex(apdu_data),
            "apdu_length": len(apdu_data),
        }

        if request.with_wrapper:
            wrapper_frame = build_wpd(apdu_data, src_wport=request.src_wport, dst_wport=request.dst_wport)
            result["wrapper_hex"] = bytes_to_hex(wrapper_frame)
            result["wrapper_length"] = len(wrapper_frame)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建ActionResponse失败: {e}")


@router.post("/parse-apdu", summary="解析APDU（Pull模式）")
async def parse_apdu_endpoint(request: ParseApduRequest):
    """
    解析APDU数据（Pull模式专用，支持Get/Set/Action的所有请求和响应）

    对GetRequest/SetRequest/ActionRequest等携带COSEM描述符的APDU，
    自动关联数据模型，返回匹配的数模对象信息。
    对GetResponse/SetResponse/ActionResponse等不携带描述符的APDU，
    通过扫描原始数据中的OBIS模式进行数模匹配。
    """
    try:
        hex_str = request.hex_data.replace(" ", "").replace("\n", "")
        apdu_bytes = hex_to_bytes(hex_str)

        # 如果包含Wrapper帧，先解封装
        if request.with_wrapper:
            from app.services.wrapper import parse_wpd
            from app.utils.hex_utils import hex_to_bytes as _h2b
            wrapper_frame = parse_wpd(apdu_bytes)
            if wrapper_frame and wrapper_frame.payload_hex:
                apdu_bytes = _h2b(wrapper_frame.payload_hex)

        apdu = parse_apdu(apdu_bytes)
        apdu_dict = apdu.model_dump() if hasattr(apdu, "model_dump") else apdu.dict()

        # 关联数据模型
        matched_objects = []
        from app.services.datamodel import data_model_manager
        if data_model_manager.is_loaded:
            type_name = apdu.type_name
            descriptors_to_match = []

            if type_name == "GetRequest":
                if getattr(apdu, 'get_type', 0) == 1 and apdu.class_id is not None and apdu.obis:
                    descriptors_to_match.append((apdu.class_id, apdu.obis, apdu.attribute_id or 2))
                elif getattr(apdu, 'get_type', 0) == 3 and hasattr(apdu, 'attribute_list'):
                    for desc in apdu.attribute_list:
                        descriptors_to_match.append((desc.class_id, desc.obis, desc.attribute_id))
            elif type_name == "SetRequest":
                if getattr(apdu, 'set_type', 0) == 1 and apdu.class_id is not None and apdu.obis:
                    descriptors_to_match.append((apdu.class_id, apdu.obis, apdu.attribute_id or 2))
            elif type_name == "ActionRequest":
                if getattr(apdu, 'action_type', 0) == 1 and apdu.class_id is not None and apdu.obis:
                    descriptors_to_match.append((apdu.class_id, apdu.obis, getattr(apdu, 'method_id', 1)))
            elif type_name == "EventNotification":
                if apdu.class_id is not None and apdu.obis:
                    descriptors_to_match.append((apdu.class_id, apdu.obis, apdu.attribute_id or 2))

            def _do_match_with_fallback(class_id, obis_str, attr_id):
                """执行精确匹配+类级回退匹配，返回(matched_dict, is_fallback)"""
                try:
                    if isinstance(obis_str, str):
                        if "-" in obis_str or ":" in obis_str:
                            obis_bytes = obis_str_to_bytes(obis_str)
                        else:
                            obis_bytes = hex_to_bytes(obis_str)
                    elif isinstance(obis_str, (bytes, bytearray)):
                        obis_bytes = bytes(obis_str)
                    else:
                        return None, False

                    # 1. 精确匹配
                    matched = data_model_manager.match_obis(class_id, obis_bytes, attr_id)
                    if matched:
                        return matched.model_dump(), False

                    # 2. 类级回退匹配
                    if hasattr(data_model_manager, 'match_by_class'):
                        fallback = data_model_manager.match_by_class(class_id, attr_id)
                        if fallback:
                            fb_dict = fallback.model_dump()
                            fb_dict["is_fallback"] = True
                            fb_dict["original_obis"] = obis_str if isinstance(obis_str, str) else bytes_to_hex(obis_bytes)
                            return fb_dict, True
                except Exception:
                    pass
                return None, False

            # 主描述符匹配（精确+类级回退）
            for class_id, obis_str, attr_id in descriptors_to_match:
                matched_dict, is_fallback = _do_match_with_fallback(class_id, obis_str, attr_id)
                if matched_dict:
                    matched_objects.append(matched_dict)
                    if "matched_name" not in apdu_dict:
                        apdu_dict["matched_name"] = matched_dict.get("name", "")

            # SetRequest的value中提取capture_objects逐项匹配
            # capture_objects格式: array of structure {class_id, obis, attribute_id, data_index}
            if type_name == "SetRequest" and hasattr(apdu, 'value') and isinstance(apdu.value, list):
                from app.utils.obis_utils import obis_bytes_to_str as _obis_to_str
                for item in apdu.value:
                    if isinstance(item, (list, tuple)) and len(item) >= 3:
                        co_class_id = item[0] if isinstance(item[0], int) else None
                        co_obis_raw = item[1]
                        co_attr_id = item[2] if isinstance(item[2], int) else 2

                        if co_class_id is None:
                            continue

                        # 将OBIS转为可匹配的格式
                        if isinstance(co_obis_raw, str):
                            co_obis_str = co_obis_raw
                        elif isinstance(co_obis_raw, (bytes, bytearray)):
                            co_obis_str = _obis_to_str(bytes(co_obis_raw))
                        else:
                            continue

                        matched_dict, is_fallback = _do_match_with_fallback(co_class_id, co_obis_str, co_attr_id)
                        if matched_dict:
                            # 去重检查
                            existing = {(o.get('class_id'), o.get('obis'), o.get('attribute_id'))
                                       for o in matched_objects}
                            key = (matched_dict.get('class_id'), matched_dict.get('obis'),
                                   matched_dict.get('attribute_id'))
                            if key not in existing:
                                matched_dict["source"] = "capture_object"
                                matched_objects.append(matched_dict)

            # 对所有APDU类型，扫描原始数据中的OBIS模式进行补充数模匹配
            # 这对于SetRequest（value中包含capture_objects等嵌套描述符）
            # 和GetResponse/SetResponse/ActionResponse等不直接携带描述符的类型尤为重要
            _scan_raw_for_obis(apdu_bytes, matched_objects, data_model_manager)

        return {
            "success": True,
            "apdu": apdu_dict,
            "matched_objects": matched_objects,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析APDU失败: {e}")


@router.get("/access-selectors", summary="获取可用的access-selector列表")
async def get_access_selectors():
    """
    返回DLMS标准中常用对象的access-selector配置。
    access-selector用于Get/Set请求的选择性访问（如Profile Generic的按范围读取）。
    """
    access_selectors = [
        {
            "class_id": 7,
            "class_name": "Profile Generic",
            "attribute_id": 2,
            "selector_id": 1,
            "name": "by_entry",
            "description": "按条目范围读取 (from_entry, to_entry)",
            "params": [
                {"name": "from_entry", "type": "uint32", "description": "起始条目号 (从1开始)"},
                {"name": "to_entry", "type": "uint32", "description": "结束条目号 (0=到最后)"},
            ],
        },
        {
            "class_id": 7,
            "class_name": "Profile Generic",
            "attribute_id": 2,
            "selector_id": 2,
            "name": "by_time",
            "description": "按时间范围读取 (from_time, to_time)",
            "params": [
                {"name": "from_time", "type": "date-time", "description": "起始时间"},
                {"name": "to_time", "type": "date-time", "description": "结束时间"},
            ],
        },
        {
            "class_id": 7,
            "class_name": "Profile Generic",
            "attribute_id": 2,
            "selector_id": 3,
            "name": "by_column",
            "description": "按列选择读取 (entry + selected_values)",
            "params": [
                {"name": "entry", "type": "uint32", "description": "条目号"},
                {"name": "selected_values", "type": "array", "description": "选择的列描述符列表"},
            ],
        },
    ]

    return {
        "success": True,
        "access_selectors": access_selectors,
        "total": len(access_selectors),
    }


@router.post("/extract-capture-objects", summary="从GetResponse中提取capture_objects")
async def extract_capture_objects_endpoint(request: ExtractCaptureObjectsRequest):
    """
    从GetResponse APDU中提取Profile Generic的capture_objects配置。

    当用户通过Pull操作读取Class 7 (Profile Generic) 的属性3 (capture_objects)时，
    解析返回的GetResponse数据，提取capture_objects列表并缓存到ProfileCaptureStore。
    """
    try:
        from app.services.profile_capture_store import ProfileCaptureStore

        hex_str = request.hex_data.replace(" ", "").replace("\n", "")
        apdu_bytes = hex_to_bytes(hex_str)

        apdu = parse_apdu(apdu_bytes)

        # 只处理GetResponse
        if apdu.type_name != "GetResponse":
            raise HTTPException(
                status_code=400,
                detail=f"期望GetResponse，实际为: {apdu.type_name}"
            )

        # 获取GetResponse中的值
        value = getattr(apdu, "value", None)

        # capture_objects 是一个array of structure
        # 每个 structure: {class_id, obis, attribute_id, data_index}
        capture_objects = []
        profile_obis = None

        if isinstance(value, list):
            for item in value:
                if isinstance(item, list) and len(item) >= 4:
                    co = {
                        "class_id": item[0] if isinstance(item[0], int) else 0,
                        "instance_id": _obis_bytes_to_str(item[1]) if isinstance(item[1], (bytes, bytearray)) else str(item[1]),
                        "attribute_id": item[2] if isinstance(item[2], int) else 0,
                        "data_index": item[3] if isinstance(item[3], int) else 0,
                    }
                    capture_objects.append(co)

        # 缓存到ProfileCaptureStore（如果提供了profile_obis）
        if capture_objects and profile_obis:
            store = ProfileCaptureStore()
            store.save_config(
                profile_obis=profile_obis,
                capture_objects=capture_objects,
                source="pull",
            )

        return {
            "success": True,
            "capture_objects": capture_objects,
            "count": len(capture_objects),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取capture_objects失败: {e}")


def _obis_bytes_to_str(obis_bytes: bytes) -> str:
    """将OBIS字节转换为A-B:C.D.E.F格式字符串"""
    if len(obis_bytes) != 6:
        return obis_bytes.hex()
    a, b = obis_bytes[0], obis_bytes[1]
    c, d = obis_bytes[2], obis_bytes[3]
    e, f = obis_bytes[4], obis_bytes[5]
    return f"{a}-{b}:{c}.{d}.{e}.{f}"


def _scan_raw_for_obis(raw_bytes: bytes, matched_objects: list, data_model_mgr):
    """
    扫描原始APDU字节流中的COSEM属性描述符模式，进行数据模型匹配。

    当APDU类型为GetResponse/SetResponse/ActionResponse等不直接携带描述符的类型时，
    通过模式匹配从原始数据中提取 class_id + OBIS + attribute_id 组合。

    扫描模式:
    - push_object_list / capture_objects 结构:
      02 04 12 00 XX 09 06 YY YY YY YY YY YY 0f ZZ
      (structure(4) { long-unsigned(class_id), octet-string(6)(OBIS), integer(attr_id), ... })
    - 独立的 octet-string(6) 模式: 09 06 XX XX XX XX XX XX
    """
    if not raw_bytes or len(raw_bytes) < 10:
        return

    matched_set = set()  # 用于去重: (class_id, obis_hex, attr_id)
    existing_keys = set()
    # 同时记录已匹配的 (class_id, attr_id) 对，用于类级回退去重
    existing_class_attr = set()
    for obj in matched_objects:
        key = (obj.get('class_id'), obj.get('obis', ''), obj.get('attribute_id', 0))
        existing_keys.add(key)
        existing_class_attr.add((obj.get('class_id'), obj.get('attribute_id', 0)))

    def _try_match_with_fallback(cid, obis_b, aid):
        """精确匹配+类级回退匹配"""
        try:
            matched = data_model_mgr.match_obis(cid, obis_b, aid)
            if matched:
                return matched.model_dump(), False
            if hasattr(data_model_mgr, 'match_by_class'):
                # 如果已有同class_id+attr_id的匹配，跳过回退（避免重复）
                if (cid, aid) in existing_class_attr:
                    return None, False
                fallback = data_model_mgr.match_by_class(cid, aid)
                if fallback:
                    fb_dict = fallback.model_dump()
                    fb_dict["is_fallback"] = True
                    fb_dict["original_obis"] = _obis_bytes_to_str(obis_b)
                    existing_class_attr.add((cid, aid))
                    return fb_dict, True
        except Exception:
            pass
        return None, False

    # 模式1: structure(4) + long-unsigned + octet-string(6) = push_object_list / capture_objects 条目
    i = 0
    while i < len(raw_bytes) - 14:
        if (raw_bytes[i] == 0x02 and raw_bytes[i+1] == 0x04 and
            raw_bytes[i+2] == 0x12 and raw_bytes[i+3] == 0x00 and
            raw_bytes[i+5] == 0x09 and raw_bytes[i+6] == 0x06):

            class_id = raw_bytes[i+4]
            obis_bytes = raw_bytes[i+7:i+13]

            attr_id = 2
            if i + 13 < len(raw_bytes) and raw_bytes[i+13] == 0x0f:
                attr_id = raw_bytes[i+14]

            obis_hex = obis_bytes.hex()
            key = (class_id, obis_hex, attr_id)
            if key in matched_set or key in existing_keys:
                i += 1
                continue
            matched_set.add(key)

            matched_dict, is_fallback = _try_match_with_fallback(class_id, obis_bytes, attr_id)
            if matched_dict and matched_dict not in matched_objects:
                matched_objects.append(matched_dict)
        i += 1

    # 模式2: 独立的 octet-string(6) 模式
    i = 0
    while i < len(raw_bytes) - 8:
        if raw_bytes[i] == 0x09 and raw_bytes[i+1] == 0x06:
            obis_bytes = raw_bytes[i+2:i+8]
            if obis_bytes == b'\x00\x00\x00\x00\x00\x00':
                i += 1
                continue

            # 尝试从前面的 long-unsigned (12 00 XX) 获取 class_id
            class_id = None
            if i >= 3 and raw_bytes[i-3] == 0x12 and raw_bytes[i-2] == 0x00:
                class_id = raw_bytes[i-1]

            class_ids_to_try = [class_id] if class_id else [1, 3, 4, 7, 8, 40]
            class_ids_to_try = [c for c in class_ids_to_try if c is not None]

            attr_id = 2
            if i + 8 < len(raw_bytes) and raw_bytes[i+8] == 0x0f:
                attr_id = raw_bytes[i+9]

            obis_hex = obis_bytes.hex()
            for cid in class_ids_to_try:
                key = (cid, obis_hex, attr_id)
                if key in matched_set or key in existing_keys:
                    continue
                matched_set.add(key)

                matched_dict, is_fallback = _try_match_with_fallback(cid, obis_bytes, attr_id)
                if matched_dict:
                    if matched_dict not in matched_objects:
                        matched_objects.append(matched_dict)
                    break
        i += 1


# ---------- APDU 打包（压缩+加密+封装） ----------

class PackageApduRequest(BaseModel):
    """打包APDU请求 - 将原始APDU通过V.44压缩+general-glo-ciphering加密（可选Wrapper封装）"""
    apdu_hex: str = Field(description="原始APDU十六进制数据")
    compress: bool = Field(default=True, description="是否V.44压缩（SC置位bit7）")
    encrypt: bool = Field(default=True, description="是否AES-GCM加密（SC置位bit5）")
    system_title: str = Field(description="系统标题（8字节十六进制）")
    guek: Optional[str] = Field(default=None, description="GUEK密钥（十六进制）")
    gubk: Optional[str] = Field(default=None, description="GUBK密钥（十六进制）")
    ak: Optional[str] = Field(default=None, description="认证密钥（十六进制）")
    invocation_counter: int = Field(default=1, description="调用计数器")
    key_id: int = Field(default=0, description="密钥标识 (0=unicast/GUEK, 1=broadcast/GUBK)")
    with_wrapper: bool = Field(default=False, description="是否封装Wrapper帧（默认False，仅APDU->V.44->general-glo-ciphering）")
    src_wport: int = Field(default=1, description="源WPort（仅with_wrapper=true时使用）")
    dst_wport: int = Field(default=16, description="目的WPort（仅with_wrapper=true时使用）")


@router.post("/package-apdu", summary="打包APDU（V.44压缩+加密，可选Wrapper封装）")
async def package_apdu_endpoint(request: PackageApduRequest):
    """
    将原始APDU数据打包为DLMS帧。

    打包流程（APDU->V.44->general-glo-ciphering->Wrapper）:
    1. 原始APDU数据
    2. V.44压缩（如果compress=true）→ SC置位bit7
    3. AES-GCM加密（如果encrypt=true）→ SC置位bit5
    4. General-Glo-Ciphering封装（SC字节同时置位压缩+加密标志）
    5. Wrapper帧封装（WPD头：version + src_wport + dst_wport + length + payload）

    当compress=true且encrypt=true时:
    - SC字节 = 0xB1 (bit7=压缩, bit5=加密, bit4=认证, bit0=Suite1)
    - 加密的内容是V.44压缩后的数据
    """
    try:
        from app.services.dlms_stack import build_frame

        hex_str = request.apdu_hex.replace(" ", "").replace("\n", "")

        result = build_frame(
            apdu_type="",
            params={},
            src_wport=request.src_wport,
            dst_wport=request.dst_wport,
            encrypt=request.encrypt,
            compress=request.compress,
            guek=request.guek,
            gubk=request.gubk,
            ak=request.ak,
            system_title=request.system_title,
            invocation_counter=request.invocation_counter,
            key_id=request.key_id,
            raw_apdu_hex=hex_str,
            with_wrapper=request.with_wrapper,
        )

        if result.get("success"):
            # 附加详细信息
            result["apdu_hex"] = hex_str
            result["apdu_length"] = len(hex_str) // 2
            result["compress"] = request.compress
            result["encrypt"] = request.encrypt
            result["with_wrapper"] = request.with_wrapper
            sc_desc = []
            if request.compress:
                sc_desc.append("bit7=压缩(V.44)")
            if request.encrypt:
                sc_desc.append("bit5=加密(AES-GCM)")
            sc_desc.append("bit0=Suite1")
            result["sc_flags"] = ", ".join(sc_desc)

            # 当启用 Wrapper 时，附加 Wrapper 元数据
            if request.with_wrapper:
                result["wrapper_src_wport"] = request.src_wport
                result["wrapper_dst_wport"] = request.dst_wport

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包APDU失败: {e}")
