import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.schemas import TaskRecord


class TaskStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.data_dir
        self.tasks_dir = self.root / "tasks"
        self.uploads_dir = self.root / "uploads"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def save(self, record: TaskRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        self.task_path(record.task_id).write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load(self, task_id: str) -> TaskRecord:
        path = self.task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(task_id)
        return TaskRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save_upload(self, task_id: str, filename: str, content: bytes) -> Path:
        suffix = Path(filename).suffix
        safe_name = f"{task_id}{suffix}" if suffix else task_id
        path = self.uploads_dir / safe_name
        path.write_bytes(content)
        return path

    def append_event(self, task_id: str, event: dict[str, Any]) -> None:
        log_path = self.tasks_dir / f"{task_id}.jsonl"
        event = {"time": datetime.now(timezone.utc).isoformat(), **event}
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def read_events(self, task_id: str) -> list[dict[str, Any]]:
        log_path = self.tasks_dir / f"{task_id}.jsonl"
        if not log_path.exists():
            return []
        return [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


store = TaskStore()
