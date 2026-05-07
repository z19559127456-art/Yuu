"""
配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

class Config:
    """基础配置"""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # 数据库配置
    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # LLM 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # WebSocket
    WS_HOST = os.getenv("WS_HOST", "localhost")
    WS_PORT = int(os.getenv("WS_PORT", 7890))

    # 安全策略
    SECURITY_POLICY_DIR = Path(os.getenv("SECURITY_POLICY_DIR", BASE_DIR / "security_policies"))
    SECURITY_POLICY_DIR.mkdir(parents=True, exist_ok=True)

    # 向量存储
    CHROMADB_PATH = Path(os.getenv("CHROMADB_PATH", BASE_DIR / "chromadb_store"))
    CHROMADB_PATH.mkdir(parents=True, exist_ok=True)

    # 并发控制
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))

    # 工具超时（秒）
    TOOL_TIMEOUT_DEFAULT = int(os.getenv("TOOL_TIMEOUT_DEFAULT", "60"))

    # 日志
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
