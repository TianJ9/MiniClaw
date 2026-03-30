"""
Agent 核心 - ReAct 范式：思考-行动-观察循环
"""
import json
import re
from typing import Dict, List, Any

from config import Config
from llm_client import LLMClient
from memory import ConversationMemory
from tools import ToolRegistry, FileReadTool, FileWriteTool, CodeRunTool, BrowserOpenTool, WebScanTool


class ReActAgent:
    """
    ReAct Agent - 显式思考-行动-观察循环

    工作流程：
    1. Thought: LLM 分析当前状态，决定下一步
    2. Action: 调用工具（如果有需要）
    3. Observation: 获取工具执行结果
    4. 重复直到得出最终答案
    """

    # 终止动作 - Agent 完成任务
    FINISH_ACTION = "finish"

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
        """设置 ReAct 格式的系统提示词"""
        tools_json = self._get_tools_json()
        prompt = f"""你是一个智能 AI Agent，使用 ReAct（思考-行动-观察）模式解决问题。

你的任务是帮助用户完成各种任务。你可以使用工具来获取信息或执行操作。

## 可用工具（JSON Schema 格式）

{tools_json}

## 输出格式

你必须使用以下格式之一回复：

### 格式 1: 使用工具（需要调用工具时）
```
<thinking>
你的思考过程，分析当前情况，决定需要什么工具
</thinking>

<tool_use>
{{"name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
</tool_use>
```

### 格式 2: 直接回答（不需要工具时）
```
<thinking>
我已经完成了分析/不需要使用工具，可以直接回答
</thinking>

<tool_use>
{{"name": "finish", "arguments": {{"answer": "你的最终答案"}}}}
</tool_use>
```

## 重要规则

1. **每次回复必须包含 `<thinking>` 和 `<tool_use>` 标签**
2. **不要编造工具**，只能使用上面列出的工具
3. **`<tool_use>` 标签内必须是合法的 JSON 格式**
4. **JSON 中使用 `name` 和 `arguments` 字段**，不是 `action` 和 `action_input`
5. **如果需要多步操作**，一步一步来，等待观察结果后再继续

## 示例

用户：读取 README.md 的前10行

<thinking>
用户想要读取文件内容，我需要使用 file_read 工具
</thinking>

<tool_use>
{{"name": "file_read", "arguments": {{"path": "README.md", "limit": 10, "offset": 1}}}}
</tool_use>

[你会收到 Observation，然后继续下一步]
"""
        self.memory.set_system_prompt(prompt)

    def _get_tools_json(self) -> str:
        """生成工具的 JSON Schema 描述"""
        tools = []
        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            schema = tool.get_schema()
            tools.append(schema["function"])
        return json.dumps(tools, ensure_ascii=False, indent=2)

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
        print(f"\n[ReAct] 开始 Agent Loop")
        print("=" * 50)

        for iteration in range(self.max_iterations):
            print(f"\n--- 第 {iteration + 1} 轮 ---")

            # 1. 思考：调用 LLM 获取 Thought + Action
            response = await self._call_llm()

            # 2. 解析响应
            parsed = self._parse_react_response(response)
            thought = parsed.get("thought", "")
            action = parsed.get("action", "")
            action_input = parsed.get("action_input", {})

            # 显示思考过程
            print(f"\n🤔 Thought: {thought}")

            # 3. 检查是否完成任务
            if action == self.FINISH_ACTION or not action:
                print(f"\n✅ 任务完成")
                self.memory.add_assistant_message(
                    f"<thinking>\n{thought}\n</thinking>\n\n<tool_use>\n{json.dumps({'name': 'finish', 'arguments': action_input}, ensure_ascii=False)}\n</tool_use>"
                )
                return action_input.get("answer", thought)

            print(f"\n🔧 Action: {action}")
            print(f"📥 Input: {json.dumps(action_input, ensure_ascii=False)}")

            # 4. 行动：执行工具
            observation = await self._execute_action(action, action_input)

            # 截断过长的观察结果用于显示
            display_obs = observation[:300] + "..." if len(observation) > 300 else observation
            print(f"\n👁️  Observation: {display_obs}")

            # 5. 记忆：将本轮结果添加到对话历史
            self.memory.add_assistant_message(
                f"<thinking>\n{thought}\n</thinking>\n\n<tool_use>\n{json.dumps({'name': action, 'arguments': action_input}, ensure_ascii=False)}\n</tool_use>"
            )
            self.memory.add_user_message(
                f"[Observation - 工具 '{action}' 的返回结果]\n{observation}\n\n"
                "分析：请根据以上结果，判断任务是否全部完成。"
                "如果还需要其他工具，请继续使用 <tool_use> 调用；"
                "只有当所有步骤都完成后，才能调用 finish。"
            )

        # 达到最大迭代次数
        return "[警告] 达到最大迭代次数，任务未完成"

    async def _call_llm(self) -> str:
        """调用 LLM 获取回复"""
        result = await self.llm.chat(
            messages=self.memory.get_messages(),
            stream=False
        )

        if "error" in result:
            return f"<thinking>\n调用失败\n</thinking>\n\n<tool_use>\n{{\"name\": \"finish\", \"arguments\": {{\"answer\": \"[错误] {result['error']}\"}}}}\n</tool_use>"

        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or ""

        return content

    def _parse_react_response(self, text: str) -> Dict[str, Any]:
        """
        解析 ReAct 格式的回复

        提取 <thinking> 和 <tool_use> 标签内容
        """
        result = {
            "thought": "",
            "action": "",
            "action_input": {}
        }

        # 提取 thinking
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
        if thinking_match:
            result["thought"] = thinking_match.group(1).strip()

        # 提取 tool_use JSON
        tool_match = re.search(r'<tool_use>\s*(\{.*?\})\s*</tool_use>', text, re.DOTALL)
        if tool_match:
            try:
                json_str = tool_match.group(1).strip()
                tool_data = json.loads(json_str)
                result["action"] = tool_data.get("name", "").lower()
                result["action_input"] = tool_data.get("arguments", {})
            except json.JSONDecodeError as e:
                print(f"[警告] 解析 tool_use 失败: {e}")
                # 尝试提取原始内容用于调试
                result["action"] = ""
                result["action_input"] = {}

        return result

    async def _execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """执行工具动作"""
        if action == self.FINISH_ACTION:
            return "任务完成"

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
