# MiniClaw - 本地化 AI Agent 框架

一个轻量级、本地优先的 AI Agent 框架，支持多轮对话、工具调用和可扩展的技能系统。

## 功能特性

- ✅ 多轮对话（流式输出）
- ✅ 支持任意 OpenAI 兼容格式的 API
- ✅ 对话历史管理（自动截断保持上下文）
- ✅ 环境变量 / .env 文件配置
- ✅ **工具调用**：文件读写、代码执行

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
# 复制配置文件模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
```

`.env` 文件示例：

```bash
LLM_API_KEY=sk-your-api-key-here
LLM_API_BASE=https://api.openai.com/v1  # 可选
LLM_MODEL=gpt-4o-mini                   # 可选
LLM_TEMPERATURE=0.7                     # 可选
```

### 浏览器自动化配置（可选）

如需使用 `web_execute_js` 工具控制 Chrome 浏览器：

**1. 启动 Chrome 调试模式**
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# 或新建一个独立的 Chrome 实例
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_dev
```

**2. 启动 Browser Bridge 服务**
```bash
pip install fastapi uvicorn
python browser_bridge.py
```

**3. 在 MiniClaw 中使用**
```
>>> 打开百度并搜索"复旦大学"
```

服务将自动：导航到百度 → 输入关键词 → 点击搜索 → 返回结果

### 3. 运行

```bash
python cli.py
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `/clear` | 清空对话历史 |
| `/history` | 显示对话历史 |
| `/tools` | 显示可用工具 |
| `/system <prompt>` | 修改系统提示词 |
| `exit` / `quit` | 退出程序 |

## 项目结构

```
miniclaw/
├── cli.py           # 命令行交互界面
├── agent.py         # Agent 核心（工具调用循环）
├── config.py        # 配置管理（支持 .env 文件）
├── llm_client.py    # LLM API 客户端
├── memory.py        # 对话记忆管理
├── tools/           # 工具包
│   ├── __init__.py
│   ├── base.py      # 工具基类
│   ├── registry.py  # 工具注册表
│   ├── file_tools.py   # 文件操作工具
│   └── code_tools.py   # 代码执行工具
├── requirements.txt # 依赖
├── .env.example     # 配置模板
└── .gitignore       # Git 忽略文件
```

## 可用工具

Agent 会自动判断何时调用工具，你只需用自然语言描述需求。

### 1. file_read - 读取文件
```
用户：读取 README.md 的前20行
```

### 2. file_write - 写入文件
```
用户：创建一个 hello.py 文件，内容是打印 "Hello World"
```

### 3. code_run - 执行代码
```
用户：运行 Python 代码计算 1+2+3+...+100
```

### 4. browser_open - 打开浏览器
```
用户：打开浏览器访问 https://www.google.com
用户：用 chrome 打开 github.com
用户：在 safari 中打开 apple.com
```

### 5. web_scan - 扫描网页内容
```
用户：抓取 https://example.com 的内容
用户：扫描 github.com，提取所有链接
用户：获取 https://news.ycombinator.com 的文章内容
```

**扫描模式：**
- `text` (默认): 提取页面正文、标题、描述
- `html`: 获取原始 HTML 代码
- `links`: 提取页面中的所有链接

### 6. web_execute_js - 执行 JavaScript
```
用户：在 example.com 执行 JS 获取页面标题
用户：用 web_execute_js 在 https://www.google.com 执行 document.title
用户：执行 JS 代码: document.querySelectorAll('a').length
```

**参数：**
- `code`: 要执行的 JavaScript 代码（必需）
- `url`: 先导航到的网页 URL（可选）
- `wait_for`: 执行前等待的元素选择器（可选）
- `timeout`: 超时时间（默认 30 秒）

## ReAct Agent（思考-行动-观察）

Agent 现在使用 **ReAct 范式**，显式展示思考过程：

```
>>> 读取 README.md 的前5行，告诉我内容是什么

[ReAct] 开始处理: 读取 README.md 的前5行...
==================================================

--- 第 1 轮 ---

🤔 Thought: 用户想要读取 README.md 文件的前5行，我需要使用 file_read 工具

🔧 Action: file_read
📥 Input: {"path": "README.md", "offset": 1, "limit": 5}

👁️  Observation: # MiniClaw - 本地化 AI Agent 框架
一个轻量级、本地优先的 AI Agent 框架...

✅ 任务完成

🤖 最终回答: README.md 的前5行内容是：...
```

**工作流程：**
1. **Thought** - AI 分析当前情况
2. **Action** - 选择并执行工具
3. **Observation** - 观察工具返回结果
4. **重复** - 直到完成任务

## Roadmap

- [✅] ReAct 循环（显式思考-行动-观察）
- [✅] 基础工具（文件、代码、浏览器）
- [ ] **Memory设计** - 记忆系统的设计
- [ ] **上下文压缩** - 长对话自动摘要
- [ ] **本地 UI 界面** - Web 可视化交互
- [ ] **技能系统** - 插件化扩展工具
- [ ] **多 Agent 协作** - 分工配合完成任务