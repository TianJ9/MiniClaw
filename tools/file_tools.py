"""文件操作工具"""
from pathlib import Path

from .base import Tool, ToolResult


class WorkspaceFileTool(Tool):
    """带工作区沙箱的文件工具基类"""

    workspace_root = Path.cwd().resolve()

    def _resolve_workspace_path(self, path: str) -> Path:
        """解析路径，并限制在当前工作区内"""
        raw_path = Path(path).expanduser()
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (self.workspace_root / raw_path).resolve()

        if not self._is_in_workspace(resolved):
            raise PermissionError(
                f"路径超出工作区范围，当前仅允许访问: {self.workspace_root}"
            )

        if self._is_dangerous_path(resolved):
            raise PermissionError("没有权限访问该路径")

        return resolved

    def _is_in_workspace(self, path: Path) -> bool:
        """检查路径是否位于工作区内"""
        try:
            path.relative_to(self.workspace_root)
            return True
        except ValueError:
            return False

    def _is_dangerous_path(self, path: Path) -> bool:
        """检查是否是受保护路径"""
        return path.name == ".env"


class FileReadTool(WorkspaceFileTool):
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
            file_path = self._resolve_workspace_path(path)

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

        except PermissionError as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"读取失败: {str(e)}",
            )


class FileWriteTool(WorkspaceFileTool):
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
            file_path = self._resolve_workspace_path(path)

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            mode = "a" if append else "w"
            with file_path.open(mode, encoding="utf-8") as f:
                f.write(content)

            action = "追加到" if append else "写入"
            return ToolResult(
                success=True,
                output=f"✓ 已成功{action}文件: {file_path}",
            )

        except PermissionError as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"写入失败: {str(e)}",
            )
