# MiniClaw - 本地化 AI Agent 框架

一个轻量级、本地优先的 AI Agent 框架，支持多轮对话、原生 function calling 和可扩展工具系统。

## 功能特性

- ✅ 多轮对话
- ✅ 支持任意 OpenAI 兼容格式的 API
- ✅ 对话历史管理（自动截断保持上下文）
- ✅ 环境变量 / .env 文件配置
- ✅ **原生 function calling** 工具调用循环
- ✅ **工具调用**：文件读写、代码执行、浏览器、网页抓取
- ✅ 文件工具工作区沙箱（默认限制在当前项目目录）
- ✅ 更友好的 CLI 输出与输入体验（`prompt_toolkit`）

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

### 3. 运行

```bash
python cli.py
```

如果你更新过项目，建议重新安装依赖：

```bash
pip install -r requirements.txt
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
用户：把一行日志追加到 logs/run.txt
```

说明：
- `file_write` 在 `append=true` 时会以追加模式写入，不再覆盖原文件
- `file_read` / `file_write` 默认只允许访问当前工作区内的文件
- 默认禁止直接读写 `.env`

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

## Agent 工作方式

当前版本使用 **原生 function calling**，不再依赖自定义 XML / 正则解析。

当任务需要工具时，模型会直接返回结构化的 `tool_calls`，程序执行工具后再把结果回填给模型，直到模型给出最终自然语言答案。

### 一个典型流程

```
用户：在当前目录创建一个 111.md，内容是代码 print(2+3) 的执行结果

Step 1
     Action  code_run
      Input  {"code": "print(2+3)", "language": "python", "timeout": 30}
Observation  5

Step 2
     Action  file_write
      Input  {"path": "111.md", "content": "5"}
Observation  ✓ 已成功写入文件: /path/to/111.md

Step 3
  Assistant  已创建文件 111.md，并写入内容：5
     Status  任务完成

◆ Final Answer
  已创建文件 111.md，并写入内容：5
```

**工作流程：**
1. **User Message** - 用户用自然语言描述任务
2. **Tool Call** - 模型返回原生 `tool_calls`
3. **Tool Result** - 程序执行工具并回填结果
4. **Final Answer** - 模型在全部动作完成后输出自然语言结果

### 为什么改成原生 function calling

- 不需要让模型手写 `<tool_use>` 之类的自定义格式
- 不需要本地用正则解析模型输出
- 多步任务更稳定，尤其是“先运行代码，再写文件”这种链式任务
- 更接近 OpenAI 兼容 API 的标准使用方式

### 当前上下文管理

- 正式会话历史保存在 `memory.py`
- 工具调用和工具结果通过 `assistant/tool` 消息继续传给模型
- 历史会按 `max_history` 自动截断，避免上下文无限增长

## 当前依赖

```txt
httpx
python-dotenv
prompt_toolkit
```

## 实现方式

持续更新中。

## Roadmap

- [x] 原生 function calling 循环
- [x] 基础工具（文件、代码、浏览器）
- [x] CLI 输入体验优化
- [ ] **Memory设计** - 记忆系统的设计
- [ ] **上下文压缩** - 长对话自动摘要
- [ ] **本地 UI 界面** - Web 可视化交互
- [ ] **技能系统** - 插件化扩展工具
- [ ] **多 Agent 协作** - 分工配合完成任务
