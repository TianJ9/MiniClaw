"""简单内存管理 - 对话历史"""
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    """对话记忆管理"""
    max_history: int = 20
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        """添加助手消息"""
        self.messages.append({"role": "assistant", "content": content})
        self._trim_history()

    def _trim_history(self):
        """保持历史记录在限制范围内，保留系统消息和最近对话"""
        if len(self.messages) > self.max_history * 2 + 1:  # user + assistant = 2 messages per turn
            # 保留第一条（可能是系统消息）和最近的 max_history 轮
            first_msg = self.messages[0] if self.messages[0].get("role") == "system" else None
            keep_start = 1 if first_msg else 0
            # 保留最后 max_history 轮
            self.messages = (
                ([first_msg] if first_msg else []) +
                self.messages[keep_start:][-self.max_history * 2:]
            )

    def clear(self):
        """清空对话历史"""
        self.messages = []

    def get_messages(self) -> List[Dict[str, str]]:
        """获取当前对话历史"""
        return self.messages.copy()

    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        # 移除旧的系统提示
        self.messages = [m for m in self.messages if m.get("role") != "system"]
        # 添加到开头
        self.messages.insert(0, {"role": "system", "content": prompt})
