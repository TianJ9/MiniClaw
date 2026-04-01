"""
Agent 核心 - ReAct 范式：思考-行动-观察循环
"""
import json
import textwrap
from typing import Dict, List, Any

from config import Config
from llm_client import LLMClient
from memory import ConversationMemory
from tools import ToolRegistry, FileReadTool, FileWriteTool, CodeRunTool, BrowserOpenTool, WebScanTool


class ReActAgent:
    """
    Agent - 基于原生 function calling 的工具调用循环

    工作流程：
    1. Assistant: 模型返回自然语言内容和/或 tool_calls
    2. Action: 程序执行工具调用
    3. Tool Result: 将工具结果回填给模型
    4. 重复直到得出最终答案
    """

    LOG_WIDTH = 88

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(
            api_base=config.api_base,
            api_key=config.api_key,
            model=config.model,
            temperature=config.temperature,
        )
        self.memory = ConversationMemory(max_history=config.max_history)
        self.tools = self._init_tools()
        self._setup_system_prompt()
        self.max_iterations = 10  # 最大循环次数，防止无限循环

    def _init_tools(self) -> ToolRegistry:
        """初始化工具注册表"""
        registry = ToolRegistry()
        registry.register(FileReadTool)
        registry.register(FileWriteTool)
        registry.register(CodeRunTool)
        registry.register(BrowserOpenTool)
        registry.register(WebScanTool)
        return registry

    def _setup_system_prompt(self):
        """设置 function calling 模式的系统提示词"""
        prompt = """你是一个智能 AI Agent，使用原生 function calling 模式解决问题。

你的任务是帮助用户完成各种任务。你可以调用工具来获取信息或执行操作。

重要规则：
1. 当任务需要操作文件、代码、网页等能力时，优先调用工具，不要假装已经执行。
2. 多步任务必须逐步完成；只有在所有要求都已经实际完成后，才直接给出最终答复。
3. 当你已经从工具拿到中间结果，但仍需执行下一步动作时，应继续调用工具。
4. 最终答复请直接用自然语言返回，不要输出 XML、标签或伪造的工具格式。
5. 简洁说明你完成了什么，必要时带上关键结果。
"""
        self.memory.set_system_prompt(prompt)

    async def chat(self, user_message: str) -> str:
        """
        处理用户消息，执行 ReAct 循环

        Returns:
            最终答案
        """
        # 添加用户消息
        self.memory.add_user_message(user_message)

        # 执行 Agent Loop
        return await self.agent_loop()

    async def agent_loop(self) -> str:
        """
        ReAct 核心循环：思考-行动-观察

        Returns:
            最终答案
        """
        for iteration in range(self.max_iterations):
            print()
            print(self._step_header(iteration + 1))

            response = await self._call_llm_with_tools()
            if "error" in response:
                self._print_log_block("Status", "调用失败")
                return f"[错误] {response['error']}"

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = (message.get("content") or "").strip()
            tool_calls = message.get("tool_calls") or []

            if content:
                self._print_log_block("Assistant", content)

            if not tool_calls:
                self.memory.add_assistant_message(content)
                self._print_log_block("Status", "任务完成")
                return content or "任务已完成。"

            self.memory.add_assistant_message(content or "", tool_calls=tool_calls)

            for tool_call in tool_calls:
                function_info = tool_call.get("function", {})
                action = function_info.get("name", "")
                raw_arguments = function_info.get("arguments") or "{}"
                action_input = self._safe_load_tool_arguments(raw_arguments)

                self._print_log_block("Action", action or "（无）")
                self._print_log_block("Input", json.dumps(action_input, ensure_ascii=False))

                observation = await self._execute_action(action, action_input)
                display_obs = observation[:300] + "..." if len(observation) > 300 else observation
                self._print_log_block("Observation", display_obs)

                self.memory.add_tool_message(
                    tool_call_id=tool_call.get("id", ""),
                    name=action,
                    content=observation,
                )

        # 达到最大迭代次数
        return "[警告] 达到最大迭代次数，任务未完成"

    async def _call_llm_with_tools(self) -> Dict[str, Any]:
        """调用 LLM，使用原生 function calling"""
        return await self.llm.chat_with_tools(
            messages=self.memory.get_messages(),
            tools=self.tools.get_all_schemas(),
        )

    def _safe_load_tool_arguments(self, raw_arguments: str) -> Dict[str, Any]:
        """解析模型返回的工具参数 JSON"""
        try:
            parsed = json.loads(raw_arguments)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    def _print_log_block(self, label: str, content: str):
        """统一打印 Agent 运行日志"""
        print(f"{label:>11}  {self._format_log_text(content)}")

    def _format_log_text(self, text: str) -> str:
        """将日志文本压成紧凑且易读的单段样式"""
        normalized = "\n".join(line.rstrip() for line in text.strip().splitlines()) if text else ""
        paragraphs = normalized.splitlines() or [""]
        wrapped_lines: List[str] = []
        for paragraph in paragraphs:
            if not paragraph:
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(
                textwrap.wrap(
                    paragraph,
                    width=self.LOG_WIDTH - 14,
                    replace_whitespace=False,
                    drop_whitespace=True,
                )
            )

        if not wrapped_lines:
            return ""

        first_line = wrapped_lines[0]
        continuation = wrapped_lines[1:]
        if not continuation:
            return first_line

        indent = "\n" + (" " * 13)
        return first_line + indent + indent.join(continuation)

    def _rule(self, title: str) -> str:
        """生成日志分隔线"""
        title_text = f" {title} "
        total_width = self.LOG_WIDTH
        remaining = max(total_width - len(title_text), 0)
        left = remaining // 2
        right = remaining - left
        return f"{'─' * left}{title_text}{'─' * right}"

    def _step_header(self, step: int) -> str:
        """生成更轻量的步骤标题"""
        return f"Step {step}"

    async def _execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """执行工具动作"""
        # 检查工具是否存在
        if action not in self.tools.list_tools():
            return f"[错误] 未知工具: {action}。可用工具: {', '.join(self.tools.list_tools())}"

        try:
            result = await self.tools.execute(action, **action_input)
            return result
        except Exception as e:
            return f"[错误] 工具执行失败: {str(e)}"

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return self.tools.list_tools()

    async def close(self):
        """关闭资源"""
        await self.llm.close()


# 为了向后兼容，保留旧类名
Agent = ReActAgent
