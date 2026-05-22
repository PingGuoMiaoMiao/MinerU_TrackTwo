import asyncio
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from src.config import settings


SUPPORTED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".jp2",
    ".webp",
    ".gif",
    ".bmp",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".html",
    ".htm",
}


class MinerUError(RuntimeError):
    pass


class MinerUClient:
    def __init__(self) -> None:
        self.base_url = settings.mineru_base_url.rstrip("/")
        self.token = settings.mineru_api_token
        self.model_version = settings.mineru_model_version
        self.timeout = settings.mineru_timeout_seconds
        self.poll_interval = settings.mineru_poll_interval_seconds

    def supports_path(self, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_SUFFIXES

    async def parse_file(self, path: Path, data_id: str | None = None) -> tuple[str, dict[str, Any]]:
        if settings.mineru_mode.lower() == "local":
            return await self.parse_local_file(path)
        if not self.token:
            return await self.parse_agent_file(path)
        try:
            return await self.parse_precise_file(path, data_id=data_id)
        except MinerUError as exc:
            markdown, metadata = await self.parse_agent_file(path)
            metadata["precise_fallback_error"] = str(exc)
            return markdown, metadata

    async def parse_local_file(self, path: Path) -> tuple[str, dict[str, Any]]:
        output_root = settings.mineru_local_output_dir
        output_root.mkdir(parents=True, exist_ok=True)
        command = [
            settings.mineru_local_command,
            "-p",
            str(path),
            "-o",
            str(output_root),
            "-b",
            "pipeline",
            "-m",
            "txt",
            "-l",
            "en",
            "-f",
            "true",
            "-t",
            "true",
        ]
        process = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=self.timeout,
        )
        if process.returncode != 0:
            raise MinerUError(
                f"Local MinerU failed with code {process.returncode}: "
                f"{(process.stderr or process.stdout)[-1000:]}"
            )

        markdown_path = self._find_local_markdown(output_root, path.stem)
        markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
        return markdown, {
            "parser": "mineru_local",
            "filename": path.name,
            "markdown_path": str(markdown_path),
            "bytes": path.stat().st_size,
            "chars": len(markdown),
        }

    async def parse_url(self, url: str, file_name: str | None = None, data_id: str | None = None) -> tuple[str, dict[str, Any]]:
        suffix = Path(file_name or url.split("?")[0]).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise MinerUError(f"MinerU does not support URL suffix: {suffix or 'unknown'}")
        if not self.token:
            return await self.parse_agent_url(url, file_name=file_name)
        try:
            return await self.parse_precise_url(url, data_id=data_id)
        except MinerUError as exc:
            markdown, metadata = await self.parse_agent_url(url, file_name=file_name)
            metadata["precise_fallback_error"] = str(exc)
            return markdown, metadata

    async def parse_precise_url(self, url: str, data_id: str | None = None) -> tuple[str, dict[str, Any]]:
        payload = {
            "url": url,
            "model_version": self._model_for_name(url),
            "enable_table": True,
            "enable_formula": True,
            "is_ocr": False,
        }
        if data_id:
            payload["data_id"] = data_id

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.post(
                f"{self.base_url}/api/v4/extract/task",
                headers=self._auth_headers(),
                json=payload,
            )
            data = self._checked_json(response)
            mineru_task_id = data["data"]["task_id"]

            result = await self._poll_precise_task(client, mineru_task_id)
            markdown = await self._download_full_markdown(client, result["full_zip_url"])

        metadata = {
            "parser": "mineru_precise",
            "mineru_task_id": mineru_task_id,
            "state": "done",
            "source": url,
            "full_zip_url": result["full_zip_url"],
            "chars": len(markdown),
        }
        return markdown, metadata

    async def parse_precise_file(self, path: Path, data_id: str | None = None) -> tuple[str, dict[str, Any]]:
        payload = {
            "files": [{"name": path.name, "data_id": data_id or path.stem}],
            "model_version": self._model_for_name(path.name),
            "enable_table": True,
            "enable_formula": True,
            "is_ocr": False,
        }

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.post(
                f"{self.base_url}/api/v4/file-urls/batch",
                headers=self._auth_headers(),
                json=payload,
            )
            data = self._checked_json(response)
            batch_id = data["data"]["batch_id"]
            upload_url = data["data"]["file_urls"][0]

            put_response = await client.put(upload_url, content=path.read_bytes())
            if put_response.status_code not in (200, 201):
                raise MinerUError(f"MinerU upload failed: HTTP {put_response.status_code}")

            result = await self._poll_precise_batch(client, batch_id, path.name)
            markdown = await self._download_full_markdown(client, result["full_zip_url"])

        metadata = {
            "parser": "mineru_precise",
            "batch_id": batch_id,
            "state": "done",
            "filename": path.name,
            "full_zip_url": result["full_zip_url"],
            "bytes": path.stat().st_size,
            "chars": len(markdown),
        }
        return markdown, metadata

    async def parse_agent_url(self, url: str, file_name: str | None = None) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "url": url,
            "language": "ch",
            "enable_table": True,
            "enable_formula": True,
            "is_ocr": False,
        }
        if file_name:
            payload["file_name"] = file_name

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.post(f"{self.base_url}/api/v1/agent/parse/url", json=payload)
            data = self._checked_json(response)
            mineru_task_id = data["data"]["task_id"]
            result = await self._poll_agent_task(client, mineru_task_id)
            markdown = await self._download_text(client, result["markdown_url"])

        return markdown, {
            "parser": "mineru_agent",
            "mineru_task_id": mineru_task_id,
            "state": "done",
            "source": url,
            "markdown_url": result["markdown_url"],
            "chars": len(markdown),
        }

    async def parse_agent_file(self, path: Path) -> tuple[str, dict[str, Any]]:
        payload = {
            "file_name": path.name,
            "language": "ch",
            "enable_table": True,
            "enable_formula": True,
            "is_ocr": False,
        }

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.post(f"{self.base_url}/api/v1/agent/parse/file", json=payload)
            data = self._checked_json(response)
            mineru_task_id = data["data"]["task_id"]
            upload_url = data["data"]["file_url"]

            put_response = await client.put(upload_url, content=path.read_bytes())
            if put_response.status_code not in (200, 201):
                raise MinerUError(f"MinerU upload failed: HTTP {put_response.status_code}")

            result = await self._poll_agent_task(client, mineru_task_id)
            markdown = await self._download_text(client, result["markdown_url"])

        return markdown, {
            "parser": "mineru_agent",
            "mineru_task_id": mineru_task_id,
            "state": "done",
            "filename": path.name,
            "markdown_url": result["markdown_url"],
            "bytes": path.stat().st_size,
            "chars": len(markdown),
        }

    async def _poll_precise_task(self, client: httpx.AsyncClient, task_id: str) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + self.timeout
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(
                f"{self.base_url}/api/v4/extract/task/{task_id}",
                headers=self._auth_headers(),
            )
            data = self._checked_json(response)["data"]
            if data["state"] == "done":
                return data
            if data["state"] == "failed":
                raise MinerUError(data.get("err_msg") or "MinerU precise parsing failed")
            await asyncio.sleep(self.poll_interval)
        raise MinerUError(f"MinerU precise task timed out: {task_id}")

    async def _poll_precise_batch(self, client: httpx.AsyncClient, batch_id: str, file_name: str) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + self.timeout
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(
                f"{self.base_url}/api/v4/extract-results/batch/{batch_id}",
                headers=self._auth_headers(),
            )
            results = self._checked_json(response)["data"].get("extract_result", [])
            result = next((item for item in results if item.get("file_name") == file_name), results[0] if results else None)
            if result and result["state"] == "done":
                return result
            if result and result["state"] == "failed":
                raise MinerUError(result.get("err_msg") or "MinerU precise batch parsing failed")
            await asyncio.sleep(self.poll_interval)
        raise MinerUError(f"MinerU precise batch timed out: {batch_id}")

    async def _poll_agent_task(self, client: httpx.AsyncClient, task_id: str) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + self.timeout
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(f"{self.base_url}/api/v1/agent/parse/{task_id}")
            data = self._checked_json(response)["data"]
            if data["state"] == "done":
                return data
            if data["state"] == "failed":
                raise MinerUError(data.get("err_msg") or "MinerU agent parsing failed")
            await asyncio.sleep(self.poll_interval)
        raise MinerUError(f"MinerU agent task timed out: {task_id}")

    async def _download_full_markdown(self, client: httpx.AsyncClient, zip_url: str) -> str:
        response = await client.get(zip_url)
        response.raise_for_status()
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            names = archive.namelist()
            full_md = next((name for name in names if name.endswith("full.md")), None)
            if not full_md:
                full_md = next((name for name in names if name.lower().endswith(".md")), None)
            if not full_md:
                raise MinerUError("MinerU zip result does not contain markdown")
            return archive.read(full_md).decode("utf-8", errors="ignore")

    async def _download_text(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    def _checked_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise MinerUError(f"MinerU HTTP {exc.response.status_code}: {body}") from exc
        data = response.json()
        if data.get("code") != 0:
            raise MinerUError(data.get("msg") or f"MinerU API error: {data}")
        return data

    def _model_for_name(self, name: str) -> str:
        suffix = Path(name.split("?")[0]).suffix.lower()
        if suffix in {".html", ".htm"}:
            return "MinerU-HTML"
        return self.model_version

    def _find_local_markdown(self, output_root: Path, stem: str) -> Path:
        candidates = sorted(
            output_root.glob(f"**/{stem}.md"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            candidates = sorted(
                output_root.glob("**/*.md"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        if not candidates:
            raise MinerUError(f"Local MinerU did not produce markdown under {output_root}")
        return candidates[0]


mineru_client = MinerUClient()
