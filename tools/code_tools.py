"""代码执行工具"""
import asyncio
import tempfile
from pathlib import Path

from .base import Tool, ToolResult


class CodeRunTool(Tool):
    """执行代码"""

    name = "code_run"
    description = "执行 Python 或 Bash 代码，并返回执行结果"
    required_params = ["code"]
    parameters = {
        "code": {
            "type": "string",
            "description": "要执行的代码",
        },
        "language": {
            "type": "string",
            "description": "代码语言: 'python' 或 'bash'（默认 python）",
            "enum": ["python", "bash"],
        },
        "timeout": {
            "type": "integer",
            "description": "超时时间（秒，默认30秒）",
        },
    }

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> ToolResult:
        try:
            if language == "python":
                return await self._run_python(code, timeout)
            elif language == "bash":
                return await self._run_bash(code, timeout)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"不支持的语言: {language}",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"执行失败: {str(e)}",
            )

    async def _run_python(self, code: str, timeout: int) -> ToolResult:
        """执行 Python 代码"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # 执行代码
            proc = await asyncio.create_subprocess_exec(
                "python", temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"执行超时（超过 {timeout} 秒）",
                )

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                return ToolResult(
                    success=True,
                    output=output or "（代码执行成功，无输出）",
                )
            else:
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"退出码 {proc.returncode}: {error}",
                )

        finally:
            # 清理临时文件
            try:
                Path(temp_file).unlink()
            except:
                pass

    async def _run_bash(self, code: str, timeout: int) -> ToolResult:
        """执行 Bash 命令"""
        # 安全检查：阻止危险命令
        if self._is_dangerous_command(code):
            return ToolResult(
                success=False,
                output="",
                error="该命令已被安全策略阻止",
            )

        proc = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(
                success=False,
                output="",
                error=f"执行超时（超过 {timeout} 秒）",
            )

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return ToolResult(
                success=True,
                output=output or "（命令执行成功，无输出）",
            )
        else:
            return ToolResult(
                success=False,
                output=output,
                error=f"退出码 {proc.returncode}: {error}",
            )

    def _is_dangerous_command(self, code: str) -> bool:
        """检查是否是危险命令"""
        dangerous = [
            "rm -rf /",
            "> /dev/sda",
            "dd if=",
            "mkfs.",
            ":(){ :|:& };:",  # fork bomb
            "curl",
            "wget",
        ]
        code_lower = code.lower()
        for cmd in dangerous:
            if cmd in code_lower:
                return True
        return False
