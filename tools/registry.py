"""工具注册表"""
from typing import Dict, List, Optional, Type, Any

from .base import Tool


class ToolRegistry:
    """工具注册表 - 管理所有可用工具"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool_class: Type[Tool]) -> "ToolRegistry":
        """注册工具类"""
        tool = tool_class()
        self._tools[tool.name] = tool
        return self

    def register_instance(self, tool: Tool) -> "ToolRegistry":
        """注册工具实例"""
        self._tools[tool.name] = tool
        return self

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 schema"""
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> str:
        """执行工具并返回格式化结果"""
        tool = self.get(name)
        if not tool:
            return f"[错误] 工具 '{name}' 不存在"

        result = await tool.execute(**kwargs)
        if result.success:
            return result.output
        else:
            return f"[错误] {result.error or '执行失败'}"
