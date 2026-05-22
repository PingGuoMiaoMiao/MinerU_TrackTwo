# API 接口说明

## `GET /health`

健康检查。

响应：

```json
{"status":"ok","app":"Data Agent for Complex Document Processing"}
```

## `POST /v1/tasks`

创建数据处理任务。使用 `multipart/form-data`。

参数：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `goal` | string | 是 | 任务目标，例如“抽取财报关键指标并标注证据” |
| `file` | file | 三选一 | PDF、DOCX、PPTX、HTML、TXT 等文件 |
| `url` | string | 三选一 | 待解析网页 URL |
| `text` | string | 三选一 | 直接提交文本 |

解析策略：

- `MINERU_MODE=precise`：PDF、DOC/DOCX、PPT/PPTX、XLS/XLSX、图片等优先调用 MinerU SaaS 精准解析 API；精准接口异常时自动降级到 Agent 轻量接口。
- `MINERU_MODE=local`：文件解析调用 MinerU 开源本地 CLI，读取本地输出 Markdown。
- TXT/Markdown、HTML 小文件或 MinerU 不支持的网页会使用本地解析器兜底。
- 任务创建接口会立即返回 `task_id`，解析和抽取在后台异步执行；调用方通过查询接口轮询状态。

响应：

```json
{
  "task_id": "abc123",
  "status": "queued",
  "message": "Task accepted."
}
```

## `GET /v1/tasks/{task_id}`

查询任务状态和结果。

核心响应字段：

| 字段 | 说明 |
| --- | --- |
| `status` | `queued`、`running`、`succeeded`、`failed` |
| `plan` | Agent 规划步骤 |
| `tool_calls` | 工具调用记录 |
| `result` | 结构化结果 |
| `error` | 失败原因 |

`result.metadata.parser` 可用于判断实际解析后端，常见值：

| 值 | 说明 |
| --- | --- |
| `mineru_precise` | MinerU SaaS 精准解析 |
| `mineru_agent` | MinerU Agent 轻量解析 |
| `mineru_local` | MinerU 开源本地 CLI |
| `local` / `local_fallback` | 项目内置本地解析或兜底 |

## `GET /v1/tasks/{task_id}/logs`

查询可追溯执行日志，包含排队、规划、工具调用、成功或失败事件。
