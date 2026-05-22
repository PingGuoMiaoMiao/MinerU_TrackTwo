from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig")

    app_name: str = "Data Agent for Complex Document Processing"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 60
    deepseek_api_key: str = ""
    mineru_api_token: str = ""
    mineru_base_url: str = "https://mineru.net"
    mineru_mode: str = "precise"
    mineru_model_version: str = "vlm"
    mineru_timeout_seconds: int = 300
    mineru_poll_interval_seconds: float = 3.0
    mineru_local_command: str = r".mineru-py312\Scripts\mineru.exe"
    mineru_local_output_dir: Path = Path("local_mineru_output")

    data_dir: Path = Path("data")
    max_upload_mb: int = 50

    @property
    def effective_llm_base_url(self) -> str:
        if self.llm_api_key:
            return self.llm_base_url
        if self.deepseek_api_key:
            return "https://api.deepseek.com/v1"
        return self.llm_base_url

    @property
    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or self.deepseek_api_key

    @property
    def effective_llm_model(self) -> str:
        if self.llm_api_key:
            return self.llm_model
        if self.deepseek_api_key and self.llm_model == "gpt-4o-mini":
            return "deepseek-chat"
        return self.llm_model


settings = Settings()
