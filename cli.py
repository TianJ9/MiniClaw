"""命令行交互界面"""
import asyncio
import shutil
import sys
import textwrap

from agent import Agent
from config import Config
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory


class ChatCLI:
    """交互式命令行聊天界面"""

    PROMPT = "miniclaw> "
    RULE_CHAR = "─"

    def __init__(self, config: Config):
        self.agent = Agent(config)
        self.terminal_width = self._get_terminal_width()
        self.prompt_session = PromptSession(history=InMemoryHistory())

    async def run(self):
        """运行主循环"""
        self._print_banner()

        while True:
            try:
                # 获取用户输入
                user_input = await self._get_input(self._format_prompt())

                # 处理特殊命令
                if not user_input.strip():
                    continue

                if user_input.strip().lower() in ["exit", "quit", "bye"]:
                    self._print_message("Session", "再见，期待我们继续一起打磨 MiniClaw。")
                    break

                if user_input.strip().lower() == "/clear":
                    self.agent.memory.clear()
                    self.agent._setup_system_prompt()
                    self._print_message("Memory", "对话历史已清空，系统提示词已恢复。")
                    continue

                if user_input.strip().lower() == "/history":
                    self._show_history()
                    continue

                if user_input.strip().lower() == "/tools":
                    self._show_tools()
                    continue

                if user_input.strip().lower().startswith("/system "):
                    new_prompt = user_input.strip()[8:]
                    self.agent.memory.set_system_prompt(new_prompt)
                    self._print_message("System", "系统提示词已更新。")
                    continue

                # 调用 Agent 处理（ReAct 循环，内部已打印思考过程）
                response = await self.agent.chat(user_input)
                self._print_section("Final Answer", response, style="answer")

            except KeyboardInterrupt:
                self._print_message("Session", "已中断，随时可以继续。")
                break
            except EOFError:
                self._print_message("Session", "输入结束，已退出。")
                break

        await self.agent.close()

    async def _get_input(self, prompt: str) -> str:
        """获取用户输入（兼容 asyncio）"""
        return await self.prompt_session.prompt_async(prompt)

    def _print_banner(self):
        """打印欢迎信息"""
        lines = [
            "MiniClaw  Local-First AI Agent CLI",
            f"Model: {self.agent.config.model}",
            f"API:   {self.agent.config.api_base}",
            "",
            "Commands:",
            "/clear    Clear conversation history",
            "/history  Show recent conversation messages",
            "/tools    List available tools",
            "/system   Replace the system prompt",
            "exit      Quit the session",
        ]
        self._print_block(lines, accent="╭", footer="╰")

    def _show_history(self):
        """显示对话历史"""
        print()
        print(self._rule("Conversation History"))
        for msg in self.agent.memory.get_messages():
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                self._print_section("System", content, style="muted", max_lines=4)
            elif role == "user":
                self._print_section("User", content, style="plain", max_lines=6)
            elif role == "assistant":
                self._print_section("Assistant", content, style="plain", max_lines=6)
        print(self._rule())
        print()

    def _show_tools(self):
        """显示可用工具"""
        print()
        print(self._rule("Available Tools"))
        for name in self.agent.get_available_tools():
            tool = self.agent.tools.get(name)
            self._print_section(tool.name, tool.description, style="plain")
        print(self._rule())
        print("直接描述需求即可，Agent 会自行选择工具。\n")

    def _print_message(self, title: str, content: str):
        """输出简短消息"""
        self._print_section(title, content, style="muted")

    def _print_section(self, title: str, content: str, style: str = "plain", max_lines: int = None):
        """输出统一风格的内容块"""
        print()
        title_prefix = {
            "plain": "•",
            "muted": "·",
            "answer": "◆",
        }.get(style, "•")
        print(f"{title_prefix} {title}")

        lines = self._wrap_text(content)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                lines[-1] = lines[-1] + " ..."

        for line in lines or [""]:
            print(f"  {line}")

    def _print_block(self, lines: list[str], accent: str = "╭", footer: str = "╰"):
        """输出带边框的块"""
        width = min(max(self.terminal_width, 60), 96)
        inner_width = width - 4
        print()
        print(f"{accent}{self.RULE_CHAR * (width - 2)}╮")
        for raw_line in lines:
            wrapped = self._wrap_text(raw_line, width=inner_width)
            if not wrapped:
                wrapped = [""]
            for line in wrapped:
                print(f"│ {line.ljust(inner_width)} │")
        print(f"{footer}{self.RULE_CHAR * (width - 2)}╯")
        print()

    def _rule(self, title: str = "") -> str:
        """输出分隔线"""
        width = min(max(self.terminal_width, 60), 96)
        if not title:
            return self.RULE_CHAR * width
        prefix = f" {title} "
        remaining = max(width - len(prefix), 0)
        left = remaining // 2
        right = remaining - left
        return f"{self.RULE_CHAR * left}{prefix}{self.RULE_CHAR * right}"

    def _wrap_text(self, text: str, width: int = None) -> list[str]:
        """按终端宽度折行，同时保留空行"""
        wrap_width = width or min(max(self.terminal_width - 2, 40), 92)
        lines = []
        for paragraph in text.splitlines():
            if not paragraph.strip():
                lines.append("")
                continue
            lines.extend(
                textwrap.wrap(
                    paragraph,
                    width=wrap_width,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
            )
        return lines

    def _format_prompt(self) -> str:
        """构造输入提示"""
        return f"\n{self.PROMPT}"

    def _get_terminal_width(self) -> int:
        """获取终端宽度"""
        return shutil.get_terminal_size(fallback=(88, 24)).columns


async def main():
    """入口函数"""
    config = Config.from_env()

    if not config.api_key:
        print("错误: 请设置 LLM_API_KEY 环境变量")
        print("示例:")
        print("  export LLM_API_KEY='your-api-key'")
        print("  或在 .env 文件中配置")
        sys.exit(1)

    cli = ChatCLI(config)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
