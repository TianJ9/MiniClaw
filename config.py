"""配置管理"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """LLM 配置"""
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_history: int = 20  # 保留的对话轮数

    @classmethod
    def from_env(cls) -> "Config":
        """从 .env 文件和环境变量加载配置"""
        # 加载 .env 文件（如果存在）
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # 也尝试从当前工作目录加载
            load_dotenv()

        return cls(
            api_base=os.getenv("LLM_API_BASE", "https://api.openai.com/v1"),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )
