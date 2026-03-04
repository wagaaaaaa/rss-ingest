# RSS 采集系统

## 项目简介

本地 RSS 订阅源采集与处理系统，支持多并发采集、内容分析和特色文章标记。

## 技术栈

- Python 3.x
- 虚拟环境: `venv/`
- AI 模型: Gemini API（用于内容分析）

## 环境配置

1. 复制环境变量模板：
   ```bash
   cp rss-ingest-local.env.example rss-ingest-local.env
   ```

2. 配置必要的环境变量：
   - `GEMINI_API_KEY`: Gemini API 密钥
   - 其他配置项参见 `config.py`

## 常用命令

```bash
# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行主程序
python rss_ingest.py

# 运行测试
pytest tests/

# 测试 Gemini API 连接
python test_gemini_3_pro_ping.py
```

## 核心功能

- RSS 订阅源采集
- 多线程并发处理
- 内容去重与分析
- 特色文章自动标记
- 支持自定义采集规则

## 配置说明

主要配置文件：
- `config.py`: 系统配置参数
- `rss-ingest-local.env`: 环境变量（敏感信息）

## Multi-Agent Workflow (Claude Code + Codex + Gemini)

### Core Rule
Claude Code is the only "commander". Codex and Gemini are executors. No one changes scope or interface contracts without Claude's instruction.

### Role Split

#### Claude Code (Commander)
- Convert requirements into clear tasks and acceptance criteria
- Define/freeze backend–frontend interface contract (API/schema/fields)
- Split work into Backend (Codex) and Frontend (Gemini)
- Review outputs from Codex/Gemini and decide revisions/merge order

#### Codex (Backend / Logic Executor)
- Implement backend logic strictly following Claude's task + contract
- Focus: APIs, business logic, data layer, tests, scripts
- Output: commit/diff + test command + test result
- Do NOT touch frontend code or change contract fields

#### Gemini (Frontend / UI Executor)
- Implement frontend strictly following Claude's task + contract
- Focus: UI components, interaction flow, state management, error display
- Output: commit/diff + manual smoke test steps
- Do NOT touch backend code or change contract fields

### Change Control
- Any contract change must be decided by Claude Code first.
- If blockers appear: report to Claude with the minimal evidence (error logs, failing tests, screenshots), wait for updated instruction.
