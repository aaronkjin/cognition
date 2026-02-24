from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    SettingsConfigDict,
)


class _CsvListParseMixin:
    """Mixin that parses comma-separated env strings for designated list fields."""

    _CSV_LIST_FIELDS: frozenset[str] = frozenset({"connected_repos"})

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name in self._CSV_LIST_FIELDS and isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()] if value else []
        return super().prepare_field_value(field_name, field, value, value_is_complex)  # type: ignore[misc]


class _CsvAwareEnvSource(_CsvListParseMixin, EnvSettingsSource):
    pass


class _CsvAwareDotEnvSource(_CsvListParseMixin, DotEnvSettingsSource):
    pass


class OrchestratorConfig(BaseSettings):
    devin_api_key: str = ""
    devin_api_base_url: str = "https://api.devin.ai/v1"
    mock_mode: bool = True
    max_parallel_sessions: int = 10
    max_acu_per_session: int = 5
    poll_interval_seconds: int = 20
    session_timeout_minutes: int = 90
    min_success_rate: float = 0.7
    wave_size: int = 10
    slack_webhook_url: str = ""
    state_file_path: str = "./state.json"

    # EXT-1: Live/Hybrid mode
    hybrid_mode: bool = False
    connected_repos: list[str] = Field(default_factory=list)

    # EXT-3: Client resilience
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 30
    max_retries: int = 3
    retry_jitter_max_seconds: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("connected_repos", mode="before")
    @classmethod
    def parse_connected_repos(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [r.strip() for r in v.split(",") if r.strip()]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        return (
            init_settings,
            _CsvAwareEnvSource(settings_cls),
            _CsvAwareDotEnvSource(
                settings_cls,
                env_file=settings_cls.model_config.get("env_file"),
                env_file_encoding=settings_cls.model_config.get("env_file_encoding"),
            ),
            _CsvAwareDotEnvSource(
                settings_cls,
                env_file=".env.local",
                env_file_encoding=settings_cls.model_config.get("env_file_encoding"),
            ),
            file_secret_settings,
        )
