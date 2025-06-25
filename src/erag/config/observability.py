from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_OTEL_", extra="ignore"
    )

    endpoint: str = "http://localhost:4317"
    enabled: bool = True

    trace_sample_ratio: float = 1.0
