"""文件操作工具"""
from pathlib import Path
from typing import Any, Dict

from .base import Tool, ToolResult


class FileReadTool(Tool):
    """读取文件内容"""

    name = "file_read"
    description = "读取指定文件的内容，支持文本文件"
    required_params = ["path"]
    parameters = {
        "path": {
            "type": "string",
            "description": "文件路径（相对路径或绝对路径）",
        },
        "limit": {
            "type": "integer",
            "description": "读取的最大行数（可选，默认全部）",
        },
        "offset": {
            "type": "integer",
            "description": "起始行号（从1开始，可选）",
        },
    }

    async def execute(
        self,
        path: str,
        limit: int = None,
        offset: int = None,
    ) -> ToolResult:
        try:
            file_path = Path(path).resolve()

            # 安全检查：防止读取敏感路径
            if self._is_dangerous_path(file_path):
                return ToolResult(
                    success=False,
                    output="",
                    error="没有权限读取该路径",
                )

            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"文件不存在: {path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"不是文件: {path}",
                )

            # 读取文件
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")

            # 处理 offset
            if offset and offset > 1:
                lines = lines[offset - 1 :]

            # 处理 limit
            if limit and limit > 0:
                lines = lines[:limit]

            result = "\n".join(lines)

            # 添加行号
            start_line = offset if offset else 1
            numbered = "\n".join(
                f"{i + start_line:4} | {line}"
                for i, line in enumerate(lines)
            )

            return ToolResult(
                success=True,
                output=f"文件: {file_path}\n```\n{numbered}\n```",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"读取失败: {str(e)}",
            )

    def _is_dangerous_path(self, path: Path) -> bool:
        """检查是否是危险路径"""
        # 检查是否在 .env 文件中
        env_path = Path(".env").resolve()
        if path == env_path:
            return True
        return False


class FileWriteTool(Tool):
    """写入文件内容"""

    name = "file_write"
    description = "写入内容到指定文件，可以创建新文件或覆盖已有文件"
    required_params = ["path", "content"]
    parameters = {
        "path": {
            "type": "string",
            "description": "文件路径（相对路径或绝对路径）",
        },
        "content": {
            "type": "string",
            "description": "要写入的文件内容",
        },
        "append": {
            "type": "boolean",
            "description": "是否追加模式（可选，默认覆盖）",
        },
    }

    async def execute(
        self,
        path: str,
        content: str,
        append: bool = False,
    ) -> ToolResult:
        try:
            file_path = Path(path).resolve()

            # 安全检查
            if self._is_dangerous_path(file_path):
                return ToolResult(
                    success=False,
                    output="",
                    error="没有权限写入该路径",
                )

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            mode = "a" if append else "w"
            file_path.write_text(content, encoding="utf-8")

            action = "追加到" if append else "写入"
            return ToolResult(
                success=True,
                output=f"✓ 已成功{action}文件: {file_path}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"写入失败: {str(e)}",
            )

    def _is_dangerous_path(self, path: Path) -> bool:
        """检查是否是危险路径"""
        env_path = Path(".env").resolve()
        if path == env_path:
            return True
        return False
