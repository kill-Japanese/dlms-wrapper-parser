"""
DLMS Wrapper Parser - FastAPI 主入口
"""
import asyncio
import uuid
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect

from app.config import settings
from app.routers import parse, datamodel, stream, auto, pull, standards, profile_capture
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
    # 启动时：可选启动TCP服务器
    tcp_server.set_ws_manager(ws_manager)
    auto_handler.set_tcp_server(tcp_server)
    # 默认不自动启动TCP服务器，由API控制
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
