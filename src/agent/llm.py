import json
from typing import Any

import httpx

from src.config import settings


class LLMClient:
    def __init__(self) -> None:
        self.base_url = settings.effective_llm_base_url.rstrip("/")
        self.api_key = settings.effective_llm_api_key
        self.model = settings.effective_llm_model
        self.timeout = settings.llm_timeout_seconds

    async def chat_json(self, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key or self.api_key == "replace-me":
            return fallback

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as exc:
            fallback["llm_error"] = str(exc)
            return fallback


llm_client = LLMClient()
