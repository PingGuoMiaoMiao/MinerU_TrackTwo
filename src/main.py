import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.agent.executor import data_agent
from src.config import settings
from src.schemas import SourceKind, TaskCreateResponse, TaskRecord, TaskStatus
from src.storage import store

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/v1/tasks", response_model=TaskCreateResponse)
async def create_task(
    goal: str = Form(...),
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    text: str | None = Form(None),
) -> TaskCreateResponse:
    provided = [value is not None for value in (file, url, text)].count(True)
    if provided != 1:
        raise HTTPException(status_code=400, detail="Exactly one of file, url, or text is required.")

    task_id = uuid4().hex
    now = datetime.now(timezone.utc)

    if file is not None:
        content = await file.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB.")
        source_path = store.save_upload(task_id, file.filename or "upload", content)
        source_kind = SourceKind.file
        source_name = file.filename or source_path.name
        source_payload = source_path
    elif url is not None:
        source_kind = SourceKind.url
        source_name = url
        source_payload = url
    else:
        source_kind = SourceKind.text
        source_name = "inline_text"
        source_payload = text or ""

    record = TaskRecord(
        task_id=task_id,
        status=TaskStatus.queued,
        goal=goal,
        source_kind=source_kind,
        source_name=source_name,
        created_at=now,
        updated_at=now,
    )
    store.save(record)
    store.append_event(task_id, {"event": "task_queued", "source_kind": source_kind, "source_name": source_name})
    asyncio.create_task(data_agent.run(record, source_payload))
    return TaskCreateResponse(task_id=task_id, status=TaskStatus.queued, message="Task accepted.")


@app.get("/v1/tasks/{task_id}", response_model=TaskRecord)
def get_task(task_id: str) -> TaskRecord:
    try:
        return store.load(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc


@app.get("/v1/tasks/{task_id}/logs")
def get_task_logs(task_id: str) -> dict:
    try:
        store.load(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc
    return {"task_id": task_id, "events": store.read_events(task_id)}
