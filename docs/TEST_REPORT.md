# 测试报告

## 1. 测试环境

- API 服务：FastAPI，`http://127.0.0.1:8000`
- LLM：DeepSeek，OpenAI-compatible Chat Completions
- MinerU SaaS：精准解析 API，`MINERU_MODE=precise`
- MinerU 开源本地：Python 3.12.13 独立环境 `.mineru-py312`，CLI 为 `.mineru-py312\Scripts\mineru.exe`

## 2. 本地样例文件测试

结果文件：`test_files_en/test_results.json`

| 文件 | 类型 | 状态 | 解析器 |
| --- | --- | --- | --- |
| `finance_report_en.txt` | TXT | `succeeded` | `local` |
| `project_notice_en.html` | HTML | `succeeded` | `local` |
| `contract_summary_en.docx` | DOCX | `succeeded` | `mineru_precise` |
| `growth_review_en.pptx` | PPTX | `succeeded` | `mineru_precise` |
| `mineru_example.pdf` | PDF | `succeeded` | `mineru_precise` |

## 3. 公开网络 PDF 测试

结果文件：`web_pdfs/web_pdf_test_results.json`

| 文件 | 页数 | 状态 | 解析器 | 解析字符数 |
| --- | ---: | --- | --- | ---: |
| `arxiv_sklearn_1201_0490.pdf` | 6 | `succeeded` | `mineru_precise` | 15,351 |
| `nasa_global_air_quality_climate_20140002242.pdf` | 21 | `succeeded` | `mineru_precise` | 138,325 |
| `nasa_microgrids_extraterrestrial_habitats_20250002250.pdf` | 22 | `succeeded` | `mineru_precise` | 130,522 |
| `digitalocean_2023_annual_report.pdf` | 132 | `succeeded` | `mineru_precise` | 510,976 |

## 4. MinerU 开源本地测试

测试命令：

```bash
.mineru-py312\Scripts\mineru.exe -p web_pdfs\arxiv_sklearn_1201_0490.pdf -o local_mineru_output -b pipeline -m txt -l en -f true -t true
```

测试结果：

- 状态：成功
- 输出 Markdown：`local_mineru_output/arxiv_sklearn_1201_0490/txt/arxiv_sklearn_1201_0490.md`
- 输出结构：Markdown、`content_list.json`、`middle.json`、`model.json`、layout/span PDF 等
- 解析字符数：15,348

项目代码也已验证可通过 `MINERU_MODE=local` 调用本地 CLI，并返回 `parser=mineru_local`。

## 5. 结论

项目已验证三条关键链路：

- MinerU SaaS 精准解析 + DeepSeek 结构化抽取
- MinerU 精准失败时的轻量解析降级能力
- MinerU 开源本地 CLI 解析能力

整体满足“使用 MinerU 工具链（含 SaaS 端与开源项目）进行开发”的提交要求。
