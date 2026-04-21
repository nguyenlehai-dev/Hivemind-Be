from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionState:
    session_id: str
    email: str
    status: str = "connected"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssetState:
    asset_id: str
    name: str
    preview_url: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GenerationState:
    job_id: str
    status: str
    model_id: str
    prompt: str
    result_urls: list[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None


sessions: dict[str, SessionState] = {}
assets: dict[str, AssetState] = {}
generations: dict[str, GenerationState] = {}
