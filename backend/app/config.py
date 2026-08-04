"""
应用配置管理模块
使用环境变量进行配置，支持 .env 文件
"""
import os
from typing import Optional


class Settings:
    """应用配置类"""

    # 服务配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # TCP服务器配置
    TCP_PORT: int = int(os.getenv("TCP_PORT", "4059"))
    TCP_HOST: str = os.getenv("TCP_HOST", "0.0.0.0")
    TCP_BUFFER_SIZE: int = int(os.getenv("TCP_BUFFER_SIZE", "4096"))

    # 应用名称
    APP_NAME: str = os.getenv("APP_NAME", "DLMS Wrapper Parser")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

    # CORS配置
    CORS_ORIGINS: list = ["*"]

    # 上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")

    # 默认加密密钥（示例，生产环境应从安全配置读取）
    DEFAULT_ENCRYPTION_KEY: Optional[str] = os.getenv("DEFAULT_ENCRYPTION_KEY")

    def __init__(self):
        # 确保必要的目录存在
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)


# 全局配置实例
settings = Settings()
