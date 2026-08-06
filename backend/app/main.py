"""
DLMS Wrapper Parser - FastAPI 主入口
"""
import os
import asyncio
import uuid
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect

from app.config import settings
from app.routers import parse, datamodel, stream, auto, pull, standards, profile_capture, nb_device
from app.services.tcp_server import tcp_server
from app.services.auto_handler import auto_handler
from app.services.log_manager import log_manager


# WebSocket 连接管理器
class WebSocketManager:
    """WebSocket连接管理器，用于广播解析结果"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """连接WebSocket，返回连接ID"""
        await websocket.accept()
        conn_id = str(uuid.uuid4())
        self.active_connections[conn_id] = websocket
        return conn_id

    def disconnect(self, conn_id: str):
        """断开WebSocket连接"""
        if conn_id in self.active_connections:
            del self.active_connections[conn_id]

    async def broadcast(self, message: dict):
        """向所有连接的客户端广播消息"""
        disconnected = []
        for conn_id, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(conn_id)
        for conn_id in disconnected:
            self.disconnect(conn_id)


ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动时初始化TCP服务器（可选）"""
    # 启动时：初始化WebSocket和自动处理模块
    tcp_server.set_ws_manager(ws_manager)
    auto_handler.set_tcp_server(tcp_server)

    # 如果设置了 TCP_AUTOSTART=true，则自动启动 TCP 服务器
    # 用于 Docker/VPS 部署场景，NB 设备通过公网 TCP 接入
    autostart = os.getenv("TCP_AUTOSTART", "false").lower() in ("true", "1", "yes")
    if autostart:
        try:
            result = await tcp_server.start()
            if result.get("success"):
                print(f"[TCP] 服务器已自动启动: {result.get('host')}:{result.get('port')} ({result.get('protocol', 'tcp').upper()})")
            else:
                print(f"[TCP] 自动启动失败: {result.get('message')}")
        except Exception as e:
            print(f"[TCP] 自动启动异常: {e}")

    yield
    # 关闭时：停止TCP服务器
    if tcp_server.running:
        await tcp_server.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="DLMS/COSEM协议帧解析与组帧工具后端服务",
    lifespan=lifespan,
)

# CORS中间件配置 - 允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cors_to_errors(request: Request, call_next):
    """中间件：确保所有响应（包括错误响应）都有CORS头"""
    try:
        response = await call_next(request)
    except Exception as exc:
        # 捕获所有未处理的异常，返回带CORS头的500响应
        origin = request.headers.get("origin")
        error_detail = str(exc)
        # 只在DEBUG模式下返回完整错误信息
        if settings.LOG_LEVEL != "DEBUG":
            error_detail = "Internal Server Error"

        response = JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": error_detail,
            },
        )
        # 添加CORS头
        if origin:
            if "*" in settings.CORS_ORIGINS or origin in settings.CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    return response


# 注册路由
app.include_router(parse.router)
app.include_router(datamodel.router)
app.include_router(stream.router)
app.include_router(auto.router)
app.include_router(pull.router)
app.include_router(standards.router)
app.include_router(profile_capture.router)
app.include_router(nb_device.router)


@app.get("/health", summary="健康检查")
@app.get("/api/health", summary="健康检查（API前缀）")
async def health_check():
    """健康检查接口（同时支持 /health 和 /api/health 路径）"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tcp_server_running": tcp_server.running,
        "tcp_clients": len(tcp_server.clients),
    }


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket流式推送端点 - 推送TCP服务器收到的帧解析结果"""
    conn_id = await ws_manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（可用于心跳或订阅控制）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
    except Exception as e:
        log_manager.add_log("ws", "error", "websocket", f"WebSocket错误: {e}")
        ws_manager.disconnect(conn_id)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器 - 确保响应有CORS头"""
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail} if isinstance(exc.detail, (str, int, float)) else exc.detail,
    )
    # 添加CORS头
    if origin:
        if "*" in settings.CORS_ORIGINS or origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器 - 捕获所有未处理异常，返回带CORS头的500响应"""
    # 打印错误日志便于调试
    print(f"[ERROR] Unhandled exception: {exc}")
    print(traceback.format_exc())

    origin = request.headers.get("origin")
    error_msg = str(exc) if settings.LOG_LEVEL == "DEBUG" else "Internal Server Error"

    response = JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": error_msg,
        },
    )
    # 添加CORS头
    if origin:
        if "*" in settings.CORS_ORIGINS or origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# ============================================================
# 前端静态文件服务 (Docker 部署时由同一服务提供前后端)
# ============================================================
# 当 backend/app/static 目录存在时（Docker 构建时将前端 dist 复制到此），
# 后端会同时提供 API 服务和前端静态文件，实现单端口访问。
_frontend_dir = Path(__file__).parent / "static"
if _frontend_dir.exists() and (_frontend_dir / "index.html").exists():
    # 挂载 Vite 构建的 assets 目录（js/css/图片等带 hash 的资源）
    _assets_dir = _frontend_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

    # SPA 回退：所有未匹配 API 路由的 GET 请求返回对应静态文件或 index.html
    # 注意：此路由注册在所有 API 路由之后，不影响 /api/*、/health、/docs、/ws 等
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # 防止路径穿越攻击
        resolved = (_frontend_dir / full_path).resolve()
        try:
            resolved.relative_to(_frontend_dir.resolve())
        except ValueError:
            return FileResponse(str(_frontend_dir / "index.html"))

        if full_path and resolved.is_file():
            return FileResponse(str(resolved))
        # SPA 路由回退：返回 index.html 让前端路由处理
        return FileResponse(str(_frontend_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
