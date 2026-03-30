"""LLM 客户端 - 支持 OpenAI 兼容格式的 API"""
import json
from typing import AsyncIterator, Dict, List, Any, Optional
import httpx


class LLMClient:
    """与远程 LLM 交互的客户端"""

    def __init__(self, api_base: str, api_key: str, model: str, temperature: float = 0.7):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        流式对话，逐字返回 AI 的回复

        Args:
            messages: 对话历史，格式 [{"role": "user", "content": "..."}, ...]
            tools: 工具定义列表（可选）

        Yields:
            每个 chunk 的文本内容
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with self.client.stream(
                "POST", url, headers=headers, json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data = line[6:]  # 去掉 "data: " 前缀
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            error_msg = f"API 错误: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('error', {}).get('message', '')}"
            except:
                pass
            yield f"\n[错误] {error_msg}"
        except Exception as e:
            yield f"\n[错误] 请求失败: {str(e)}"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        非流式对话，支持工具调用

        Args:
            messages: 对话历史
            tools: 工具定义列表

        Returns:
            完整的响应对象，包含 tool_calls
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "tools": tools,
            "tool_choice": "auto",
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"API 错误: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('error', {}).get('message', '')}"
            except:
                pass
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> Dict[str, Any]:
        """非流式对话（stream 参数为兼容接口，始终非流式）"""
        """
        非流式对话

        Args:
            messages: 对话历史
            stream: 是否流式（这里始终非流式）

        Returns:
            完整的响应对象
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"API 错误: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('error', {}).get('message', '')}"
            except:
                pass
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
