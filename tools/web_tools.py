"""Web 相关工具"""
import asyncio
import json
import platform
import re
import subprocess
import webbrowser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from .base import Tool, ToolResult


class BrowserOpenTool(Tool):
    """打开浏览器访问指定网址"""

    name = "browser_open"
    description = "打开浏览器访问指定网址，支持指定浏览器或默认浏览器"
    required_params = ["url"]
    parameters = {
        "url": {
            "type": "string",
            "description": "要访问的网址 URL（如 https://www.example.com）",
        },
        "browser": {
            "type": "string",
            "description": "浏览器名称: 'chrome'、'safari'、'firefox'、'edge'、'opera'、'brave'、'arc' 等（可选，默认使用系统默认浏览器）",
        },
        "new_tab": {
            "type": "boolean",
            "description": "是否在新标签页打开（默认 True）",
        },
    }

    # macOS 浏览器应用路径
    MACOS_BROWSER_PATHS = {
        "chrome": [
            "/Applications/Google Chrome.app",
            "/Applications/Chrome.app",
            str(Path.home() / "Applications/Google Chrome.app"),
        ],
        "chromium": [
            "/Applications/Chromium.app",
            str(Path.home() / "Applications/Chromium.app"),
        ],
        "safari": ["/Applications/Safari.app"],
        "firefox": [
            "/Applications/Firefox.app",
            str(Path.home() / "Applications/Firefox.app"),
        ],
        "edge": [
            "/Applications/Microsoft Edge.app",
            str(Path.home() / "Applications/Microsoft Edge.app"),
        ],
        "opera": [
            "/Applications/Opera.app",
            str(Path.home() / "Applications/Opera.app"),
        ],
        "brave": [
            "/Applications/Brave Browser.app",
            str(Path.home() / "Applications/Brave Browser.app"),
        ],
        "arc": [
            "/Applications/Arc.app",
            str(Path.home() / "Applications/Arc.app"),
        ],
    }

    # 浏览器名称别名
    BROWSER_ALIASES = {
        "chrome": ["chrome", "google-chrome", "google chrome", "chromium"],
        "safari": ["safari"],
        "firefox": ["firefox", "mozilla", "mozilla firefox"],
        "edge": ["edge", "microsoft edge", "msedge"],
        "opera": ["opera"],
        "brave": ["brave", "brave browser"],
        "arc": ["arc"],
    }

    async def execute(
        self,
        url: str,
        browser: str = None,
        new_tab: bool = True,
    ) -> ToolResult:
        try:
            # 规范化 URL
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # 验证 URL 格式
            parsed = urlparse(url)
            if not parsed.netloc:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"无效的 URL: {url}",
                )

            # 检查是否是危险 URL
            if self._is_dangerous_url(url):
                return ToolResult(
                    success=False,
                    output="",
                    error="该 URL 已被安全策略阻止",
                )

            # 根据平台选择打开方式
            system = platform.system()

            if browser:
                # 规范化浏览器名称
                browser_key = self._normalize_browser_name(browser)

                if system == "Darwin":  # macOS
                    success, error = await self._open_macos_browser(url, browser_key, new_tab)
                elif system == "Windows":
                    success, error = await self._open_windows_browser(url, browser_key, new_tab)
                else:  # Linux
                    success, error = await self._open_linux_browser(url, browser_key, new_tab)

                if not success:
                    return ToolResult(
                        success=False,
                        output="",
                        error=error,
                    )

                return ToolResult(
                    success=True,
                    output=f"✓ 已在 {browser} 中打开: {url}",
                )
            else:
                # 使用默认浏览器
                webbrowser.open(url, new=2 if new_tab else 1)
                return ToolResult(
                    success=True,
                    output=f"✓ 已在默认浏览器中打开: {url}",
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"打开浏览器失败: {str(e)}",
            )

    def _normalize_browser_name(self, browser: str) -> str:
        """将各种浏览器名称归一化为标准键名"""
        browser_lower = browser.lower().strip()
        for key, aliases in self.BROWSER_ALIASES.items():
            if browser_lower == key or browser_lower in aliases:
                return key
        return browser_lower

    async def _open_macos_browser(self, url: str, browser: str, new_tab: bool) -> tuple:
        """在 macOS 上打开指定浏览器"""
        # 查找浏览器应用
        app_paths = self.MACOS_BROWSER_PATHS.get(browser, [f"/Applications/{browser.capitalize()}.app"])

        browser_path = None
        for path in app_paths:
            if Path(path).exists():
                browser_path = path
                break

        if not browser_path:
            available = self._get_available_macos_browsers()
            return False, f"未找到浏览器 '{browser}'。系统可用的浏览器: {', '.join(available) if available else '无'}"

        # 使用 open 命令打开
        try:
            cmd = ["open", "-a", browser_path, url]
            if new_tab:
                # 尝试在新标签页打开（部分浏览器支持）
                pass  # macOS open 命令默认行为

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                return False, f"打开浏览器失败: {error_msg}"

            return True, None

        except asyncio.TimeoutError:
            return False, "打开浏览器超时"
        except Exception as e:
            return False, f"打开浏览器失败: {str(e)}"

    async def _open_windows_browser(self, url: str, browser: str, new_tab: bool) -> tuple:
        """在 Windows 上打开指定浏览器"""
        browser_commands = {
            "chrome": ["chrome"],
            "firefox": ["firefox"],
            "edge": ["msedge"],
            "opera": ["opera"],
            "brave": ["brave"],
        }

        cmd = browser_commands.get(browser, [browser])
        cmd.append(url)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                return False, f"打开浏览器失败: {error_msg}"

            return True, None

        except FileNotFoundError:
            available = self._get_available_browsers()
            return False, f"未找到浏览器 '{browser}'。系统可用的浏览器: {', '.join(available) if available else '无'}"
        except asyncio.TimeoutError:
            return False, "打开浏览器超时"
        except Exception as e:
            return False, f"打开浏览器失败: {str(e)}"

    async def _open_linux_browser(self, url: str, browser: str, new_tab: bool) -> tuple:
        """在 Linux 上打开指定浏览器"""
        browser_commands = {
            "chrome": ["google-chrome", "chrome", "chromium", "chromium-browser"],
            "firefox": ["firefox"],
            "edge": ["microsoft-edge", "msedge"],
            "opera": ["opera"],
            "brave": ["brave-browser", "brave"],
        }

        candidates = browser_commands.get(browser, [browser])

        for cmd_name in candidates:
            try:
                cmd = [cmd_name, url]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

                if proc.returncode == 0:
                    return True, None

            except FileNotFoundError:
                continue
            except asyncio.TimeoutError:
                return False, "打开浏览器超时"
            except Exception:
                continue

        available = self._get_available_browsers()
        return False, f"未找到浏览器 '{browser}'。系统可用的浏览器: {', '.join(available) if available else '无'}"

    def _get_available_macos_browsers(self) -> list:
        """获取 macOS 上可用的浏览器列表"""
        available = []
        for name, paths in self.MACOS_BROWSER_PATHS.items():
            for path in paths:
                if Path(path).exists():
                    available.append(name)
                    break
        return available

    def _get_available_browsers(self) -> list:
        """获取系统上可用的浏览器列表（通用方法）"""
        system = platform.system()

        if system == "Darwin":
            return self._get_available_macos_browsers()

        # Windows/Linux: 检查命令是否存在
        available = []
        for name, cmds in {
            "chrome": ["google-chrome", "chrome", "chromium", "chromium-browser"],
            "firefox": ["firefox"],
            "edge": ["msedge", "microsoft-edge"],
            "safari": ["safari"],
            "opera": ["opera"],
            "brave": ["brave", "brave-browser"],
        }.items():
            for cmd in cmds:
                try:
                    result = subprocess.run(
                        ["which" if system != "Windows" else "where", cmd],
                        capture_output=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        available.append(name)
                        break
                except Exception:
                    continue

        return available

    def _is_dangerous_url(self, url: str) -> bool:
        """检查是否是危险 URL"""
        dangerous_schemes = [
            "file://",
            "ftp://",
            "javascript:",
            "data:",
            "vbscript:",
        ]
        url_lower = url.lower()
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return True

        # 阻止访问本地地址
        blocked_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
        ]
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in blocked_hosts:
            return True

        return False


class WebScanTool(Tool):
    """扫描/抓取网页内容"""

    name = "web_scan"
    description = "抓取网页内容，获取页面标题、正文、链接等信息。切换页面后一般应先调用查看。"
    required_params = ["url"]
    parameters = {
        "url": {
            "type": "string",
            "description": "要扫描的网页 URL（如 https://www.example.com）",
        },
        "mode": {
            "type": "string",
            "description": "扫描模式: 'text' 提取正文, 'html' 获取原始HTML, 'links' 提取链接（默认 text）",
            "enum": ["text", "html", "links"],
        },
        "max_length": {
            "type": "integer",
            "description": "返回内容的最大长度（默认 5000 字符）",
        },
        "timeout": {
            "type": "integer",
            "description": "请求超时时间（秒，默认 15）",
        },
    }

    async def execute(
        self,
        url: str,
        mode: str = "text",
        max_length: int = 5000,
        timeout: int = 15,
    ) -> ToolResult:
        try:
            # 规范化 URL
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # 验证 URL
            parsed = urlparse(url)
            if not parsed.netloc:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"无效的 URL: {url}",
                )

            # 检查危险 URL
            if self._is_dangerous_url(url):
                return ToolResult(
                    success=False,
                    output="",
                    error="该 URL 已被安全策略阻止",
                )

            # 发送 HTTP 请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html = response.text

            # 根据模式处理内容
            if mode == "html":
                result = html[:max_length]
                if len(html) > max_length:
                    result += f"\n\n... (内容已截断，共 {len(html)} 字符)"

            elif mode == "links":
                links = self._extract_links(html, url)
                result = f"页面链接（共 {len(links)} 个）：\n"
                result += "\n".join([f"- {text[:50]}: {href}" for text, href in links[:50]])
                if len(links) > 50:
                    result += f"\n... (还有 {len(links) - 50} 个链接)"

            else:  # text 模式
                result = self._extract_text(html, max_length)

            return ToolResult(
                success=True,
                output=f"📄 URL: {url}\n\n{result}",
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output="",
                error=f"请求超时（超过 {timeout} 秒）",
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP 错误: {e.response.status_code} - {e.response.reason_phrase}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"抓取失败: {str(e)}",
            )

    def _extract_text(self, html: str, max_length: int) -> str:
        """从 HTML 中提取纯文本内容"""
        # 提取标题
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "无标题"

        # 提取 meta description
        desc_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if not desc_match:
            desc_match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
                html,
                re.IGNORECASE,
            )
        description = desc_match.group(1).strip() if desc_match else ""

        # 移除 script 和 style 标签
        html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<nav[^>]*>[\s\S]*?</nav>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<footer[^>]*>[\s\S]*?</footer>", "", html, flags=re.IGNORECASE)

        # 提取 body 内容
        body_match = re.search(r"<body[^>]*>([\s\S]*)</body>", html, re.IGNORECASE)
        body = body_match.group(1) if body_match else html

        # 提取主要文本内容（优先尝试 article, main, .content 等区域）
        main_content = self._extract_main_content(body)

        # 转换为纯文本
        text = self._html_to_text(main_content if main_content else body)

        # 清理文本
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # 构建结果
        result = f"标题: {title}\n"
        if description:
            result += f"描述: {description}\n"
        result += f"\n{'=' * 40}\n\n"
        result += text[:max_length]

        if len(text) > max_length:
            result += f"\n\n... (内容已截断，共 {len(text)} 字符)"

        return result

    def _extract_main_content(self, html: str) -> str:
        """尝试提取页面的主要内容区域"""
        # 尝试常见的正文容器
        patterns = [
            r"<article[^>]*>([\s\S]*?)</article>",
            r"<main[^>]*>([\s\S]*?)</main>",
            r'<div[^>]+class=["\'][^"\']*(?:content|article|post|entry)[^"\']*["\'][^>]*>([\s\S]*?)</div>',
            r'<section[^>]+class=["\'][^"\']*(?:content|article|post)[^"\']*["\'][^>]*>([\s\S]*?)</section>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)

        return html

    def _html_to_text(self, html: str) -> str:
        """将 HTML 转换为纯文本"""
        # 替换常见标签为换行
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<p[^>]*>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<div[^>]*>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
        html = re.sub(r"</li>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<h[1-6][^>]*>", "\n## ", html, flags=re.IGNORECASE)
        html = re.sub(r"</h[1-6]>", "\n", html, flags=re.IGNORECASE)

        # 移除所有标签
        html = re.sub(r"<[^>]+>", "", html)

        # 解码 HTML 实体
        import html
        html = html.unescape(html)

        # 清理多余空白
        html = re.sub(r"\n\s*\n", "\n\n", html)
        html = re.sub(r"[ \t]+", " ", html)

        return html.strip()

    def _extract_links(self, html: str, base_url: str) -> list:
        """从 HTML 中提取链接"""
        links = []
        seen = set()

        # 匹配所有 a 标签
        pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>'
        matches = re.findall(pattern, html, re.IGNORECASE)

        for href, text in matches:
            # 跳过锚点和 javascript
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # 转换为绝对 URL
            full_url = urljoin(base_url, href)

            # 去重
            if full_url in seen:
                continue
            seen.add(full_url)

            # 提取链接文本
            link_text = re.sub(r"<[^>]+>", "", text).strip()
            if not link_text:
                link_text = full_url

            links.append((link_text[:100], full_url))

        return links

    def _is_dangerous_url(self, url: str) -> bool:
        """检查是否是危险 URL"""
        dangerous_schemes = [
            "file://",
            "ftp://",
            "javascript:",
            "data:",
            "vbscript:",
        ]
        url_lower = url.lower()
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return True

        # 阻止访问本地地址
        blocked_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
        ]
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in blocked_hosts:
            return True

        return False
