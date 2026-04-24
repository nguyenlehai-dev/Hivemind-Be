from datetime import datetime, timezone

from app.modules.runway.mock_image import build_mock_result_image
from app.modules.runway.orm import GenerationRow


def advance_mock(job: GenerationRow) -> None:
    """Progress a mock job through queued → running → completed by time."""
    now = datetime.now(timezone.utc)
    created = job.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = (now - created).total_seconds()
    if elapsed >= 3 and job.status != "completed":
        job.status = "completed"
        job.result_urls = [build_mock_result_image(job.prompt, job.model_id)]
    elif elapsed >= 1 and job.status == "queued":
        job.status = "running"
