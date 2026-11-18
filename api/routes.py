"""API routes for the REC-8K Video Generation Tracking System.

Provides RESTful endpoints for querying samples, generating scripts,
uploading persistent videos, and tracking project completion.
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from domain.models import (
    CategorySummary,
    ProjectStats,
    Sample,
    SampleStatus,
    ScriptRequest,
    ScriptResponse,
)
from services.dataset_service import dataset_service
from services.llm_service import create_script
from services.video_service import video_service

router = APIRouter(prefix="/api", tags=["tracker"])


class PaginatedSamplesResponse(BaseModel):
    """Response container for paginated samples list."""

    samples: List[Sample]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class UpdateScriptRequest(BaseModel):
    """Payload to manually update script text."""

    script: str
    disappear_cnt: int = 1
    appear_cnt: int = 0


@router.get("/stats", response_model=ProjectStats)
def get_project_stats() -> ProjectStats:
    """Retrieve overall project completion statistics and category breakdowns."""
    return dataset_service.get_project_stats()


@router.get("/categories", response_model=List[CategorySummary])
def get_categories() -> List[CategorySummary]:
    """Retrieve all available category types with progress metrics."""
    return dataset_service.get_project_stats().categories


@router.get("/samples", response_model=PaginatedSamplesResponse)
def get_samples(
    category: Optional[str] = Query(default=None, description="Category filter (or 'all')"),
    status_filter: Optional[SampleStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, description="Search description or class"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedSamplesResponse:
    """Query samples with category, status, and search filters with pagination."""
    filtered = dataset_service.filter_samples(
        category=category,
        status=status_filter,
        search_query=search,
    )
    paginated_items, total = dataset_service.paginate_samples(
        filtered, page=page, page_size=page_size
    )
    total_pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedSamplesResponse(
        samples=paginated_items,
        total_count=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/samples/{sample_id}", response_model=Sample)
def get_sample(sample_id: str) -> Sample:
    """Retrieve a single sample by its unique ID."""
    sample = dataset_service.get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )
    return sample


@router.post("/samples/{sample_id}/script", response_model=ScriptResponse)
def generate_sample_script(sample_id: str, payload: ScriptRequest) -> ScriptResponse:
    """
    Generate a 6-second video script for the sample using the configured LLM.

    Applies the user-specified disappear and appear counts.
    """
    sample = dataset_service.get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )

    # Invoke requested create_script function
    generated_script = create_script(
        image=sample.image_filename,
        description=sample.description,
        disappear_cnt=payload.disappear_cnt,
        appear_cnt=payload.appear_cnt,
    )

    # Persist updated script to storage
    updated_sample = dataset_service.update_script(
        sample_id=sample_id,
        script=generated_script,
        disappear_cnt=payload.disappear_cnt,
        appear_cnt=payload.appear_cnt,
    )

    if not updated_sample:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated script.",
        )

    final_count = max(0, sample.counting_answer - payload.disappear_cnt + payload.appear_cnt)

    return ScriptResponse(
        sample_id=sample_id,
        script=generated_script,
        disappear_cnt=payload.disappear_cnt,
        appear_cnt=payload.appear_cnt,
        initial_count=sample.counting_answer,
        projected_final_count=final_count,
    )


@router.put("/samples/{sample_id}/script", response_model=Sample)
def update_sample_script(sample_id: str, payload: UpdateScriptRequest) -> Sample:
    """Manually update or edit the script text for a sample."""
    sample = dataset_service.update_script(
        sample_id=sample_id,
        script=payload.script,
        disappear_cnt=payload.disappear_cnt,
        appear_cnt=payload.appear_cnt,
    )
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )
    return sample


@router.post("/samples/{sample_id}/video", response_model=Sample)
async def upload_sample_video(
    sample_id: str,
    file: UploadFile = File(...),
) -> Sample:
    """
    Upload and persistently save a video for a sample.

    Ensures the video is saved to storage/videos/ so it survives server reloads.
    """
    sample = dataset_service.get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )

    file_bytes = await file.read()
    updated = video_service.save_uploaded_video(
        sample_id=sample_id,
        original_filename=file.filename or "video.mp4",
        file_bytes=file_bytes,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video file format or write error. Supported: .mp4, .webm, .mov",
        )

    return updated


@router.delete("/samples/{sample_id}/video", response_model=Sample)
def delete_sample_video(sample_id: str) -> Sample:
    """Delete an uploaded video file and revert sample status."""
    updated = video_service.delete_video(sample_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )
    return updated
