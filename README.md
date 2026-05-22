# Data Agent 复杂文档处理智能体

这是一个面向“智能进化 Agent 能力评测赛道”的可复现 Data Agent 项目骨架。系统提供统一 API，支持上传 PDF、Word、PPT、HTML、TXT 或提交网页 URL，自动完成任务规划、工具调用、结构化抽取、结果校验和可追溯日志输出。

## 核心能力

- 文档/网页输入：支持文件上传与 URL 抓取。
- 自动规划：根据用户目标生成处理计划，拆解为解析、抽取、清洗、校验等步骤。
- 工具执行：集成 MinerU SaaS 精准解析、Agent 轻量解析和 MinerU 开源本地 CLI，内置 TXT/HTML 本地兜底解析。
- 结构化输出：统一返回 `summary`、`metadata`、`entities`、`tables`、`quality`、`evidence`。
- 全链路日志：每个任务保存输入、计划、工具调用、异常恢复与最终结果。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

访问：

- 健康检查：`GET http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`

也可以运行最小烟测，脚本会启动服务、提交一条文本任务、轮询结果并校验 schema：

```bash
python scripts/run_smoke_tests.py
```

当前工作区已经额外安装了 MinerU 开源本地环境：

```bash
.mineru-py312\Scripts\mineru.exe --help
```

本地开源模式需要 Python 3.12；主服务仍可用当前 Python 环境运行。

## 配置 API

在 `.env` 中填写你提供的 OpenAI-compatible API：

```env
LLM_BASE_URL=https://your-api-host/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

当前项目也支持 DeepSeek 快捷配置：

```env
DEEPSEEK_API_KEY=your-deepseek-key
LLM_MODEL=deepseek-chat
```

MinerU 可通过下面变量配置：

```env
MINERU_API_TOKEN=your-mineru-token
MINERU_MODE=precise
MINERU_MODEL_VERSION=vlm
MINERU_TIMEOUT_SECONDS=300
```

系统会优先使用 MinerU 精准解析 API；如果 token 未开通或精准接口失败，会自动降级到免登录的 Agent 轻量解析 API。两种模式都会轮询结果并读取 MinerU 返回的 Markdown，再交给 Agent 做结构化抽取。

项目也支持 MinerU 开源本地模式，需使用 Python 3.12 独立环境安装 `mineru[core]`：

```env
MINERU_MODE=local
MINERU_LOCAL_COMMAND=.mineru-py312\Scripts\mineru.exe
MINERU_LOCAL_OUTPUT_DIR=local_mineru_output
```

当前已使用本地开源 MinerU 在 `web_pdfs/arxiv_sklearn_1201_0490.pdf` 上完成解析测试，输出 Markdown、content list、middle/model JSON 等结果。

推荐提交/演示默认使用：

```env
MINERU_MODE=precise
```

需要展示开源工具链时切换为：

```env
MINERU_MODE=local
```

如果你的 API 不是 OpenAI Chat Completions 格式，需要修改 [src/agent/llm.py](src/agent/llm.py) 中的 `LLMClient.chat_json`。

## 提交任务

### 上传文件

```bash
curl -X POST "http://localhost:8000/v1/tasks" ^
  -F "goal=抽取财报中的关键财务指标，输出结构化 JSON，并标注证据来源" ^
  -F "file=@samples/sample_report.txt"
```

### 提交网页

```bash
curl -X POST "http://localhost:8000/v1/tasks" ^
  -F "goal=解析网页正文，提取标题、关键实体、表格和摘要" ^
  -F "url=https://example.com"
```

### 查看结果

```bash
curl http://localhost:8000/v1/tasks/{task_id}
curl http://localhost:8000/v1/tasks/{task_id}/logs
```

## 提交材料

建议正式提交时包含：

- GitHub 仓库链接：开源 `src/`、`docs/`、`samples/`、`scripts/`、`requirements.txt`、`README.md`。
- 系统部署与运行说明：本 README 与 [docs/API.md](docs/API.md)。
- 技术报告：[docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md)。
- 测试报告与运行记录：[docs/TEST_REPORT.md](docs/TEST_REPORT.md)、`test_files_en/test_results.json`、`web_pdfs/web_pdf_test_results.json`。
- 提交自检清单：[docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md)。
- 演示讲稿/PPT 大纲：[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)。

提交前请确认 `.env`、`data/`、`.mineru-py312/`、`local_mineru_output/` 不进入公开仓库。

## 目录

```text
src/
  agent/          Agent 规划、执行、校验和 LLM 适配
  tools/          文档、网页解析工具
  storage.py      本地任务存储
  main.py         FastAPI 入口
data/             运行时生成任务、上传文件、日志和结果
docs/             技术报告与 API 说明
samples/          示例任务文件
scripts/          烟测与提交验证脚本
```

## 评测接口说明

详细接口见 [docs/API.md](docs/API.md)，技术方案见 [docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md)，测试记录见 [docs/TEST_REPORT.md](docs/TEST_REPORT.md)。
