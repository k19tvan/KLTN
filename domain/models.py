"""Domain models for REC-8K Video Generation Tracking System.

Defines core business entities, enums, request/response schemas,
and validation logic according to Clean Code standards.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SampleStatus(str, Enum):
    """Lifecycle status of a sample in the transformation pipeline."""

    PENDING = "pending"
    SCRIPTED = "scripted"
    VIDEO_UPLOADED = "video_uploaded"


class Point(BaseModel):
    """2D coordinate representing an object counting point."""

    x: float = Field(..., description="Horizontal coordinate on the image")
    y: float = Field(..., description="Vertical coordinate on the image")


class ScriptParams(BaseModel):
    """Parameters governing object dynamics in the 6-second video."""

    disappear_cnt: int = Field(
        default=1,
        ge=0,
        description="Number of target objects that exit or disappear",
    )
    appear_cnt: int = Field(
        default=0,
        ge=0,
        description="Number of new target objects that enter or appear",
    )


class Sample(BaseModel):
    """A single REC-8K curated sample undergoing video transformation."""

    id: str = Field(..., description="Unique sample identifier")
    image_filename: str = Field(..., description="Filename of the image in images directory")
    description: str = Field(..., description="Reference expression describing target objects")
    category_type: str = Field(..., description="Category type (e.g., color, action, age)")
    target_class: str = Field(..., description="Semantic class of the target object")
    attribute: str = Field(default="", description="Attribute qualifier (e.g. red, walking)")
    counting_answer: int = Field(..., ge=0, lt=15, description="Ground truth target count (< 15)")
    points: List[List[float]] = Field(..., description="List of [x, y] coordinates for visualization")
    script_params: ScriptParams = Field(default_factory=ScriptParams)
    script: Optional[str] = Field(default=None, description="LLM-generated 6-second video script")
    video_filename: Optional[str] = Field(default=None, description="Filename of uploaded generated video")
    status: SampleStatus = Field(default=SampleStatus.PENDING)
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class ScriptRequest(BaseModel):
    """Request payload to trigger LLM script generation."""

    disappear_cnt: int = Field(default=1, ge=0)
    appear_cnt: int = Field(default=0, ge=0)


class ScriptResponse(BaseModel):
    """Response payload containing generated script and calculated dynamics."""

    sample_id: str
    script: str
    disappear_cnt: int
    appear_cnt: int
    initial_count: int
    projected_final_count: int


class CategorySummary(BaseModel):
    """Aggregated status counts for a category."""

    name: str
    total_samples: int
    scripted_samples: int
    video_uploaded_samples: int


class ProjectStats(BaseModel):
    """System-wide progress metrics."""

    total_samples: int
    total_categories: int
    scripted_count: int
    video_uploaded_count: int
    categories: List[CategorySummary]
