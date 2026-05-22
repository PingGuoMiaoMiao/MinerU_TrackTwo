# Data Agent 技术报告

## 1. 方案概述

本项目实现一个面向复杂文档与网页解析的 Data Agent。系统将任务拆解为“输入解析、目标规划、结构化抽取、质量校验、日志归档”五个阶段，通过统一 API 接收评测请求，并输出可验证的结构化结果和全链路日志。系统已同时接入 MinerU SaaS 端和 MinerU 开源本地工具链，满足比赛对 MinerU 工具链使用的要求。

## 2. 系统架构

- API 层：FastAPI 提供任务创建、状态查询、日志查询接口。
- Agent 层：根据任务目标生成执行计划，调度解析工具和 LLM 抽取器。
- 工具层：解析 PDF、Word、PPT、HTML、TXT 与网页 URL。
- MinerU 层：支持 MinerU SaaS 精准解析、Agent 轻量解析，以及 MinerU 开源本地 CLI 解析，输出 Markdown 作为统一中间表示。
- 存储层：本地 JSON/JSONL 保存任务状态、工具调用和事件日志。
- LLM 适配层：支持 OpenAI-compatible Chat Completions API，可替换为参赛团队自有模型服务。

## 3. 任务执行机制

1. 接收 `goal` 和一个输入源。
2. 创建任务记录并写入 `data/tasks/{task_id}.json`。
3. 规划器根据目标和输入源生成 3-6 个步骤。
4. 解析工具优先调用 MinerU 提取 Markdown、表格和版面文本；SaaS 外部服务不可用时可降级轻量解析，也可切换 `MINERU_MODE=local` 使用开源 MinerU 本地 CLI。
5. LLM 抽取器按统一 schema 输出摘要、实体、表格、质量评分和证据。
6. 校验器检查 schema、原文可用性和文本长度。
7. 最终结果与日志持久化，供评测系统拉取。

## 4. MinerU 工具链接入

系统支持三种 MinerU 解析后端：

- `mineru_precise`：调用 `https://mineru.net/api/v4` 精准解析 API，支持文件上传、任务轮询、结果 zip 下载，并读取 `full.md`。
- `mineru_agent`：精准接口不可用或未配置 token 时，降级调用免登录 Agent 轻量解析 API。
- `mineru_local`：通过 Python 3.12 独立环境中的 `.mineru-py312\Scripts\mineru.exe` 调用 MinerU 开源本地 CLI，输出 Markdown、content list、middle/model JSON 等本地结果。

默认推荐使用 `MINERU_MODE=precise`，用于线上评测和演示；如需展示开源工具链，将 `.env` 切换为 `MINERU_MODE=local`。

## 5. 难点场景设计

系统重点覆盖以下数据处理痛点：

- 财务报告中的关键指标抽取与证据追踪。
- 跨格式文档统一结构化。
- 网页正文清洗与元数据抽取。
- 多步骤执行日志保留，便于复现和审计。
- LLM 不可用时降级为规则化摘要，保证系统稳定返回。

## 6. 典型任务示例

### 示例 1：财报关键指标抽取

输入：`samples/sample_report.txt`

目标：抽取营业收入、净利润、研发费用、现金流等指标，并标注证据。

预期输出：`entities` 中包含指标名称、数值、单位、同比变化；`evidence` 中包含原文片段。

### 示例 2：网页正文结构化

输入：新闻或公告网页 URL。

目标：提取标题、发布时间、主体摘要、关键实体。

### 示例 3：PPT 内容解析

输入：产品介绍 PPTX。

目标：按页提取主题、关键观点和数据表述。

### 示例 4：Word 合同解析

输入：DOCX 合同。

目标：抽取合同主体、金额、期限、违约条款。

### 示例 5：PDF 报告解析

输入：PDF 研究报告。

目标：抽取章节摘要、表格指标和风险提示。

## 7. 测试结果

项目已完成以下验证：

- 5 个本地样例文件：TXT、HTML、DOCX、PPTX、PDF 全部 `succeeded`。
- 4 个公开网络 PDF：arXiv 论文、NASA 报告、NASA 技术论文、132 页 DigitalOcean 年报全部 `succeeded`，解析器均为 `mineru_precise`。
- MinerU 开源本地 CLI：使用 Python 3.12 环境解析 `web_pdfs/arxiv_sklearn_1201_0490.pdf` 成功，生成 Markdown、content list、middle/model JSON 等结果。

详细记录见 `docs/TEST_REPORT.md`、`web_pdfs/web_pdf_test_results.json` 和 `test_files_en/test_results.json`。

## 8. 稳定性说明

- 上传大小通过 `MAX_UPLOAD_MB` 限制。
- 任务记录与事件日志分离，便于异常恢复。
- LLM 调用失败时返回 fallback 结果并记录错误。
- 所有接口返回 Pydantic schema，保证结构一致。
- MinerU SaaS 精准接口异常时可自动降级轻量接口；必要时可切换开源本地 CLI。

## 9. 后续可增强方向

- 增加 OCR 工具处理拍照件、扫描件和低质量文档。
- 增加任务队列，如 Redis Queue、Celery 或 Dramatiq。
- 增加评测集和自动化指标，包括字段准确率、证据召回率和延迟统计。
