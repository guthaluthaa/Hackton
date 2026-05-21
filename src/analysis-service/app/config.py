from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "hackton"
    rabbitmq_password: str = "hackton123"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "hackton"
    minio_secret_key: str = "hackton123"
    minio_bucket: str = "uploads"
    minio_secure: bool = False

    # Provedor LLM: "claude" ou "openai"
    llm_provider: str = "claude"

    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-opus-4-5"

    # OpenAI API
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
