"""
数据模型路由 - 管理COSEM对象模型
"""
import os
import uuid
import tempfile
import urllib.request
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional

from app.models.datamodel import (
    CosemObject,
    DataModelUploadResponse,
    DataModelSearchResponse,
    DataModelObjectListResponse,
    CosemObjectDetail,
)
from app.services.datamodel import data_model_manager
from app.config import settings


router = APIRouter(prefix="/api/datamodel", tags=["DataModel"])


class GithubImportRequest(BaseModel):
    """从 GitHub 导入数据模型的请求"""
    url: str = "https://raw.githubusercontent.com/kill-Japanese/dlms-wrapper-parser/main/sample_data/cosem_data_model.xlsx"


def _load_from_excel_bytes(excel_bytes: bytes, filename: str) -> DataModelUploadResponse:
    """从 Excel 字节数据加载数据模型（通用方法）"""
    # 保存到临时文件
    file_id = str(uuid.uuid4())[:8]
    temp_filename = f"{file_id}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

    with open(file_path, "wb") as f:
        f.write(excel_bytes)

    # 加载数据模型
    result = data_model_manager.load_excel(file_path)

    return DataModelUploadResponse(
        success=True,
        total_objects=result["total_objects"],
        classes=result["classes"],
        message=f"成功加载 {result['total_objects']} 个对象",
    )


@router.post("/upload", response_model=DataModelUploadResponse, summary="上传数据模型Excel")
async def upload_datamodel(file: UploadFile = File(..., description="Excel文件 (.xlsx)")):
    """
    上传COSEM数据模型Excel文件

    Excel应包含以下列（支持中英文列名）:
    - class_id / 类ID
    - obis / OBIS码
    - name / 名称
    - attribute_id / 属性ID
    - data_type / 数据类型
    - description / 描述
    - unit / 单位
    - scaler / 倍率
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的Excel文件")

    try:
        contents = await file.read()
        return _load_from_excel_bytes(contents, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


@router.post("/import-github", response_model=DataModelUploadResponse, summary="从 GitHub 导入数据模型")
async def import_from_github(request: GithubImportRequest):
    """
    从 GitHub Raw URL 导入 COSEM 数据模型 Excel 文件

    - **url**: GitHub Raw 文件 URL（默认使用仓库内置的示例数据模型）
    """
    url = request.url

    # 简单校验 URL
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="无效的 URL 格式")

    # 从 URL 中提取文件名
    filename = url.split("/")[-1].split("?")[0]
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="URL 必须指向 .xlsx 或 .xls 文件")

    try:
        # 下载文件
        req = urllib.request.Request(url, headers={
            "User-Agent": "DLMS-Wrapper-Parser/1.0"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail=f"下载失败: HTTP {response.status}")
            contents = response.read()

        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="下载的文件为空")

        return _load_from_excel_bytes(contents, filename)

    except HTTPException:
        raise
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"无法访问 URL: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")


@router.get("/list", response_model=list[CosemObject], summary="获取对象列表（所有条目）")
async def list_objects(
    class_id: Optional[int] = Query(None, description="按类ID过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取COSEM对象列表（所有条目，包括属性和方法行）

    - **class_id**: 可选，按类ID过滤（如 1=Data, 3=Register, 8=ProfileGeneric等）
    - **limit**: 返回数量限制
    - **offset**: 分页偏移量
    """
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载，请先上传Excel文件")

    try:
        objects = data_model_manager.get_object_list(
            class_id=class_id,
            limit=limit,
            offset=offset,
        )
        return objects
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.get("/objects", response_model=DataModelObjectListResponse, summary="获取对象标题行列表")
async def list_object_headers(
    class_id: Optional[int] = Query(None, description="按类ID过滤"),
    limit: int = Query(200, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取COSEM对象标题行列表（仅对象本身，不含属性和方法行）

    只返回 attribute_id=0 的对象记录，用于前端对象列表展示。

    - **class_id**: 可选，按类ID过滤
    - **limit**: 返回数量限制
    - **offset**: 分页偏移量
    """
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载，请先上传Excel文件")

    try:
        objects, total = data_model_manager.get_object_headers(
            class_id=class_id,
            limit=limit,
            offset=offset,
        )
        return DataModelObjectListResponse(
            objects=objects,
            total=total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.get("/search", response_model=DataModelSearchResponse, summary="搜索OBIS对象")
async def search_objects(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    class_id: Optional[int] = Query(None, description="按类ID过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    """
    搜索COSEM对象

    搜索范围:
    - 对象名称
    - OBIS码
    - 描述信息

    - **keyword**: 搜索关键词
    - **class_id**: 可选，按类ID过滤
    - **limit**: 返回数量限制
    """
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载，请先上传Excel文件")

    try:
        results = data_model_manager.search(
            keyword=keyword,
            class_id=class_id,
            limit=limit,
        )
        return DataModelSearchResponse(
            results=results,
            total=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {e}")


@router.get("/classes", summary="获取所有类ID列表")
async def get_classes():
    """获取数据模型中包含的所有类ID"""
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载")

    return {
        "classes": data_model_manager.get_classes(),
        "total_objects": data_model_manager.total_objects,
    }


@router.get("/status", summary="数据模型加载状态")
async def get_datamodel_status():
    """获取数据模型加载状态"""
    return {
        "loaded": data_model_manager.is_loaded,
        "total_objects": data_model_manager.total_objects,
        "source_file": os.path.basename(data_model_manager.source_file) if data_model_manager.source_file else None,
        "classes": data_model_manager.get_classes() if data_model_manager.is_loaded else [],
    }


@router.get("/match", response_model=Optional[CosemObject], summary="精确匹配OBIS")
async def match_obis(
    class_id: int = Query(..., description="类ID"),
    obis: str = Query(..., description="OBIS码"),
    attribute_id: int = Query(0, description="属性ID (0=任意)"),
):
    """
    根据类ID、OBIS码和属性ID精确匹配对象

    - **class_id**: 类ID
    - **obis**: OBIS码 (如 1-0:1.8.0.255)
    - **attribute_id**: 属性ID
    """
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载")

    from app.utils.obis_utils import obis_str_to_bytes
    try:
        obis_bytes = obis_str_to_bytes(obis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"OBIS码格式错误: {e}")

    result = data_model_manager.match_obis(class_id, obis_bytes, attribute_id)
    if not result:
        raise HTTPException(status_code=404, detail="未找到匹配的对象")
    return result


@router.get("/object/{class_id}/{obis}", response_model=CosemObjectDetail, summary="获取对象完整详情")
async def get_object_detail(
    class_id: int,
    obis: str,
):
    """
    获取单个COSEM对象的完整信息，包含所有属性和方法列表

    - **class_id**: 类ID
    - **obis**: OBIS码 (如 1-0:1.8.0.255)
    """
    if not data_model_manager.is_loaded:
        raise HTTPException(status_code=404, detail="数据模型未加载，请先上传Excel文件")

    result = data_model_manager.get_object_detail(class_id, obis)
    if not result:
        raise HTTPException(status_code=404, detail=f"未找到对象: class_id={class_id}, obis={obis}")
    return result
