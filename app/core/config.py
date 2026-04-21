from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HIVEMIND_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_env: str = "development"
    runway_mock_mode: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    database_url: str = (
        "postgresql+asyncpg://hivemind:hivemind@localhost:5432/hivemind"
    )
    database_echo: bool = False

    # Playwright login (only used when runway_mock_mode=False).
    # Credentials MUST come from .env — never commit them.
    runway_email: str = ""
    runway_password: str = ""
    runway_login_url: str = "https://app.runwayml.com/login"
    runway_dashboard_url_prefix: str = "https://app.runwayml.com/"
    runway_playwright_headless: bool = True
    runway_playwright_timeout_ms: int = 30_000

    # Runway Developer API (official — https://docs.dev.runwayml.com).
    # When runway_api_key is set, GenerationService submits real tasks for
    # supported modes (currently: image_to_video with reference). Otherwise
    # the service falls back to the SVG mock.
    runway_api_key: str = ""
    runway_api_base_url: str = "https://api.dev.runwayml.com/v1"
    runway_api_version: str = "2024-11-06"
    runway_api_timeout_s: float = 30.0
    runway_default_video_model: str = "gen3a_turbo"
    runway_default_duration_s: int = 5

    # Which backend to use for generation:
    #   "mock"    - always return SVG gradient (default, safe).
    #   "api"     - use Runway Developer API (requires runway_api_key).
    #   "scraper" - drive app.runwayml.com via Playwright using the stored
    #               storage_state from login. FRAGILE + ToS risk.
    runway_backend: str = "mock"

    # For scraper: your Runway team slug (from URL app.runwayml.com/.../teams/<slug>/...).
    runway_team_slug: str = ""
    runway_scraper_timeout_ms: int = 120_000
    runway_scraper_result_wait_ms: int = 180_000


settings = Settings()
