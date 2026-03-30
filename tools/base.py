"""工具基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str
    error: Optional[str] = None


class Tool(ABC):
    """工具基类"""

    # 工具元数据（子类必须定义）
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    required_params: list = []  # 必需参数名称列表

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具，子类必须实现"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具 schema（用于 LLM function calling）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params,
                },
            },
        }
