from datetime import datetime, timezone
from pathlib import Path

from src.agent.llm import llm_client
from src.agent.planner import build_plan
from src.schemas import SourceKind, StructuredResult, TaskRecord, TaskStatus, ToolCall
from src.storage import store
from src.tools.parsers import parse_file_auto, parse_text, parse_url


def preview(text: str, limit: int = 500) -> str:
    text = " ".join(text.split())
    return text[:limit]


class DataAgent:
    async def run(self, record: TaskRecord, source_payload: str | Path) -> TaskRecord:
        record.status = TaskStatus.running
        store.save(record)
        store.append_event(record.task_id, {"event": "task_started", "goal": record.goal})

        try:
            record.plan = await build_plan(record.goal, record.source_name)
            store.append_event(
                record.task_id,
                {"event": "plan_created", "steps": [step.model_dump() for step in record.plan]},
            )
            store.save(record)

            parsed_text, metadata = await self._parse(record, source_payload)
            self._mark_plan_step(record, "parse_source", TaskStatus.succeeded.value, fallback_index=0)
            result = await self._extract(record.goal, parsed_text, metadata)
            self._mark_plan_step(record, "extract_structure", TaskStatus.succeeded.value, fallback_index=1)
            result = self._validate(result, parsed_text)
            self._mark_plan_step(record, "validate_result", TaskStatus.succeeded.value, fallback_index=len(record.plan) - 1)
            self._mark_remaining_steps(record, TaskStatus.succeeded.value)

            record.result = result
            record.status = TaskStatus.succeeded
            store.append_event(
                record.task_id,
                {"event": "task_succeeded", "quality": result.quality},
            )
        except Exception as exc:
            record.status = TaskStatus.failed
            record.error = str(exc)
            store.append_event(record.task_id, {"event": "task_failed", "error": str(exc)})

        store.save(record)
        return record

    async def _parse(self, record: TaskRecord, source_payload: str | Path) -> tuple[str, dict]:
        call = ToolCall(
            name="document_parser",
            input={"source_kind": record.source_kind, "source_name": record.source_name},
            status="started",
            started_at=datetime.now(timezone.utc),
        )
        record.tool_calls.append(call)
        store.save(record)

        try:
            if record.source_kind == SourceKind.file:
                text, metadata = await parse_file_auto(Path(source_payload), data_id=record.task_id)
            elif record.source_kind == SourceKind.url:
                text, metadata = await parse_url(str(source_payload))
            else:
                text, metadata = parse_text(str(source_payload))

            call.status = "succeeded"
            call.output_preview = preview(text)
            call.ended_at = datetime.now(timezone.utc)
            store.append_event(
                record.task_id,
                {
                    "event": "tool_call",
                    "tool": call.name,
                    "status": call.status,
                    "metadata": metadata,
                    "output_preview": call.output_preview,
                },
            )
            store.save(record)
            return text, metadata
        except Exception as exc:
            call.status = "failed"
            call.error = str(exc)
            call.ended_at = datetime.now(timezone.utc)
            store.save(record)
            raise

    async def _extract(self, goal: str, text: str, metadata: dict) -> StructuredResult:
        fallback = {
            "summary": preview(text, 260),
            "metadata": metadata,
            "entities": [],
            "tables": [],
            "quality": {
                "confidence": 0.55,
                "checks": ["fallback_without_llm", "non_empty_text" if text else "empty_text"],
            },
            "evidence": [{"type": "text_preview", "content": preview(text, 220)}] if text else [],
            "raw_text_preview": preview(text, 1000),
        }

        data = await llm_client.chat_json(
            system=(
                "你是严谨的数据结构化抽取器。只输出 JSON，字段必须包含："
                "summary, metadata, entities, tables, quality, evidence, raw_text_preview。"
                "所有结论尽量给出 evidence，禁止编造原文不存在的信息。"
            ),
            user=(
                f"任务目标：{goal}\n"
                f"文档元数据：{metadata}\n"
                f"原文：\n{text[:12000]}"
            ),
            fallback=fallback,
        )
        if isinstance(data.get("metadata"), dict):
            data["metadata"] = {**metadata, **data["metadata"]}
        else:
            data["metadata"] = metadata
        data.setdefault("entities", [])
        data.setdefault("tables", [])
        data.setdefault("quality", {})
        data.setdefault("evidence", [])
        data.setdefault("raw_text_preview", preview(text, 1000))
        data["entities"] = self._normalize_list_of_objects(data["entities"], "value")
        data["tables"] = self._normalize_list_of_objects(data["tables"], "value")
        data["evidence"] = self._normalize_list_of_objects(data["evidence"], "content")
        return StructuredResult(**data)

    def _validate(self, result: StructuredResult, text: str) -> StructuredResult:
        checks = list(result.quality.get("checks", []))
        checks.append("schema_valid")
        checks.append("source_text_available" if text else "source_text_missing")
        result.quality["checks"] = checks
        result.quality.setdefault("confidence", 0.7 if text else 0.2)
        result.quality["text_length"] = len(text)
        return result

    def _mark_plan_step(self, record: TaskRecord, action: str, status: str, fallback_index: int | None = None) -> None:
        for step in record.plan:
            if step.action == action:
                step.status = status
                store.save(record)
                store.append_event(
                    record.task_id,
                    {"event": "plan_step_updated", "step_id": step.id, "action": step.action, "status": status},
                )
                return
        if fallback_index is not None and 0 <= fallback_index < len(record.plan):
            step = record.plan[fallback_index]
            step.status = status
            store.save(record)
            store.append_event(
                record.task_id,
                {"event": "plan_step_updated", "step_id": step.id, "action": step.action, "status": status},
            )

    def _mark_remaining_steps(self, record: TaskRecord, status: str) -> None:
        changed = False
        for step in record.plan:
            if step.status == "pending":
                step.status = status
                changed = True
        if changed:
            store.save(record)
            store.append_event(
                record.task_id,
                {
                    "event": "plan_completed",
                    "steps": [step.model_dump() for step in record.plan],
                },
            )

    def _normalize_list_of_objects(self, value: object, default_key: str) -> list[dict]:
        if not isinstance(value, list):
            return []
        normalized = []
        for item in value:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({default_key: str(item)})
        return normalized


data_agent = DataAgent()
