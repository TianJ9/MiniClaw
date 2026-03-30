"""命令行交互界面"""
import asyncio
import sys

from agent import Agent
from config import Config


class ChatCLI:
    """交互式命令行聊天界面"""

    def __init__(self, config: Config):
        self.agent = Agent(config)

    async def run(self):
        """运行主循环"""
        self._print_banner()

        while True:
            try:
                # 获取用户输入
                user_input = await self._get_input(">>> ")

                # 处理特殊命令
                if not user_input.strip():
                    continue

                if user_input.strip().lower() in ["exit", "quit", "bye"]:
                    print("\n再见！")
                    break

                if user_input.strip().lower() == "/clear":
                    self.agent.memory.clear()
                    self.agent._setup_system_prompt()
                    print("[对话历史已清空]\n")
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
                    print(f"[系统提示词已更新]\n")
                    continue

                # 调用 Agent 处理（ReAct 循环，内部已打印思考过程）
                response = await self.agent.chat(user_input)
                print(f"\n🤖 最终回答: {response}")
                print()

            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except EOFError:
                print("\n\n再见！")
                break

        await self.agent.close()

    async def _get_input(self, prompt: str) -> str:
        """获取用户输入（兼容 asyncio）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    def _print_banner(self):
        """打印欢迎信息"""
        banner = f"""
╔════════════════════════════════════════╗
║      MiniClaw - AI Agent CLI           ║
╠════════════════════════════════════════╣
║  Model: {self.agent.config.model:<28} ║
║  API:   {self.agent.config.api_base[:28]:<28} ║
╠════════════════════════════════════════╣
║  命令:                                 ║
║    /clear    - 清空对话历史            ║
║    /history  - 显示对话历史            ║
║    /tools    - 显示可用工具            ║
║    /system   - 设置系统提示            ║
║    exit/quit - 退出                    ║
╚════════════════════════════════════════╝
"""
        print(banner)

    def _show_history(self):
        """显示对话历史"""
        print("\n--- 对话历史 ---")
        for msg in self.agent.memory.get_messages():
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                print(f"[系统] {content[:100]}...")
            elif role == "user":
                print(f"[用户] {content}")
            elif role == "assistant":
                print(f"[AI] {content[:200]}...")
        print("---------------\n")

    def _show_tools(self):
        """显示可用工具"""
        print("\n--- 可用工具 ---")
        for name in self.agent.get_available_tools():
            tool = self.agent.tools.get(name)
            print(f"\n🔧 {tool.name}")
            print(f"   {tool.description}")
        print("\n使用方式：直接描述需求，AI 会自动选择合适的工具")
        print("----------------\n")


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
