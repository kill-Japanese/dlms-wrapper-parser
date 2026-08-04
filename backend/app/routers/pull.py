"""
Pull操作路由 - 管理预设Pull操作和执行GetRequest
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.services.apdu_parser import build_apdu
from app.services.wrapper import build_wpd
from app.utils.hex_utils import bytes_to_hex, hex_to_bytes


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
