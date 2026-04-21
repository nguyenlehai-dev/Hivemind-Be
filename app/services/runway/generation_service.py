from datetime import datetime
from uuid import uuid4
from urllib.parse import quote

from fastapi import HTTPException

from app.schemas.runway import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseData,
    GenerationDetailData,
    GenerationDetailResponse,
)
from app.services.runway.store import GenerationState, generations


def _build_result_image(prompt: str, model_id: str) -> str:
    safe_prompt = prompt[:80] or "Untitled scene"
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='1280' height='720'>
      <defs>
        <linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'>
          <stop offset='0%' stop-color='#102038'/>
          <stop offset='100%' stop-color='#245dff'/>
        </linearGradient>
      </defs>
      <rect width='1280' height='720' fill='url(#bg)'/>
      <circle cx='1040' cy='120' r='180' fill='rgba(255,255,255,0.08)'/>
      <text x='80' y='170' fill='white' font-size='42' font-family='Arial'>Runway Custom Workflow</text>
      <text x='80' y='250' fill='white' font-size='28' font-family='Arial'>{model_id}</text>
      <foreignObject x='80' y='310' width='1020' height='220'>
        <div xmlns='http://www.w3.org/1999/xhtml'
             style='font-size:36px;color:white;font-family:Arial;line-height:1.3;'>
          {safe_prompt}
        </div>
      </foreignObject>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"


class RunwayGenerationService:
    def create(self, payload: GenerateRequest) -> GenerateResponse:
        job_id = f"job_{uuid4().hex[:10]}"
        generations[job_id] = GenerationState(
            job_id=job_id,
            status="queued",
            model_id=payload.model_id,
            prompt=payload.prompt,
            result_urls=[],
        )
        return GenerateResponse(data=GenerateResponseData(job_id=job_id, status="queued"))

    def get(self, job_id: str) -> GenerationDetailResponse:
        job = generations.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        elapsed = (datetime.utcnow() - job.created_at).total_seconds()
        if elapsed >= 3 and job.status != "completed":
            job.status = "completed"
            job.result_urls = [_build_result_image(job.prompt, job.model_id)]
        elif elapsed >= 1 and job.status == "queued":
            job.status = "running"

        return GenerationDetailResponse(
            data=GenerationDetailData(
                id=job.job_id,
                status=job.status,
                model_id=job.model_id,
                prompt=job.prompt,
                result_urls=job.result_urls,
                error=job.error,
            )
        )


generation_service = RunwayGenerationService()
