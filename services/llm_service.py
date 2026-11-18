"""LLM integration service for 6-second video script generation.

Uses LangChain OpenAI (ChatOpenAI) with configuration from .env
to generate structured video prompts depicting dynamic target object changes.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image

from config import (
    REC8K_IMAGES_DIR,
    VIDEO_DURATION_SECONDS,
    config,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert video director and AI video prompt engineer specializing in reference expression counting and object dynamics for image-to-video diffusion models.

Your task is to compose a single, fluid, continuous paragraph (3-5 sentences) describing a complete 6-second video transformation based on the provided reference image and target description.

CRITICAL REQUIREMENTS:
- Output MUST be a SINGLE, continuous paragraph of natural narrative prose.
- Do NOT use markdown headings, bullet points, numbered lists, timestamps (like "0-2s:"), or section labels.
- Chronologically weave the 6-second transformation into the single paragraph:
  1. The opening frames anchor directly to the reference image as the starting frame with subtle camera motion.
  2. Between seconds 2 and 4, describe exactly how {disappear_cnt} target object(s) smoothly disappear or leave the scene, and how {appear_cnt} new target object(s) enter or appear.
  3. In the final seconds (4-6s), describe how the scene naturally stabilizes into the clear, final visible state.
- Write authoritatively and vividly. Output ONLY the paragraph, nothing else."""


@dataclass(frozen=True)
class ScriptInput:
    """Encapsulates input parameters for script creation (adheres to F1)."""

    image_path: str
    description: str
    disappear_cnt: int
    appear_cnt: int


def _encode_image_to_base64(image_path: Path, max_dimension: int = 1024) -> Optional[str]:
    """
    Encode and optimize an image to a base64 string.

    Resizes images exceeding max_dimension to keep API payloads compact and fast
    while preserving high visual fidelity for vision LLMs.
    """
    if not image_path.exists():
        return None
    try:
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            if max(im.width, im.height) > max_dimension:
                im.thumbnail((max_dimension, max_dimension))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as err:
        logger.warning("Could not base64 encode %s: %s", image_path, err)
        return None


def _resolve_image_path(image_input: str) -> Path:
    """Resolve an image filename or path to an absolute path."""
    path = Path(image_input)
    if path.is_absolute() and path.exists():
        return path
    candidate_in_images = REC8K_IMAGES_DIR / path.name
    if candidate_in_images.exists():
        return candidate_in_images
    return path


def _generate_fallback_script(
    image_name: str,
    description: str,
    disappear_cnt: int,
    appear_cnt: int,
) -> str:
    """Generate a clean single-paragraph script when LLM endpoint is unreachable."""
    disappear_phrase = (
        f"{disappear_cnt} target {description} smoothly move out of the frame"
        if disappear_cnt > 0
        else "no target objects leave the scene"
    )
    appear_phrase = (
        f"{appear_cnt} new {description} enter the frame"
        if appear_cnt > 0
        else "no new target objects enter"
    )

    return (
        f"Using the referenced image \"{image_name}\" as the starting frame, the first 2 seconds feature "
        f"a slow cinematic camera glide that establishes the environment while keeping all initial instances "
        f"of {description} in clear view. Between 2 and 4 seconds, {disappear_phrase} while {appear_phrase}, "
        f"maintaining realistic motion blur and consistent lighting. In the final 2 seconds, from 4 to 6 seconds, "
        f"the camera motion gently settles, providing a stable, crystal-clear view of the final composition."
    )


class LLMService:
    """Handles communications with self-hosted LLM via LangChain."""

    def __init__(self) -> None:
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize LangChain ChatOpenAI with environment settings."""
        try:
            from langchain_openai import ChatOpenAI

            self._client = ChatOpenAI(
                base_url=config.llm_base_url,
                api_key=config.llm_api_key,
                model_name=config.llm_model_name,
                temperature=0.7,
                max_tokens=1024,
                timeout=30,
                max_retries=1,
            )
            logger.info(
                "Initialized ChatOpenAI with base_url=%s, model=%s",
                config.llm_base_url,
                config.llm_model_name,
            )
        except Exception as err:
            logger.error("Failed to initialize ChatOpenAI: %s", err)
            self._client = None

    def generate_script(self, request: ScriptInput) -> str:
        """Generate a 6-second video script for a target object transformation."""
        resolved_img_path = _resolve_image_path(request.image_path)
        img_name = resolved_img_path.name
        b64_image = _encode_image_to_base64(resolved_img_path)

        user_content = f"""Reference Image: {img_name}
Target Description: "{request.description}"
Duration: {VIDEO_DURATION_SECONDS} seconds
Target Object Dynamics:
- Target objects to disappear/exit: {request.disappear_cnt}
- Target objects to appear/enter: {request.appear_cnt}

Please write the 6-second video script following the required format."""

        if self._client is not None:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                sys_msg = SystemMessage(
                    content=SYSTEM_PROMPT.format(
                        disappear_cnt=request.disappear_cnt,
                        appear_cnt=request.appear_cnt,
                    )
                )

                # Attempt multimodal vision input first if image file is encoded
                if b64_image:
                    try:
                        multimodal_content = [
                            {"type": "text", "text": user_content},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}"
                                },
                            },
                        ]
                        messages = [sys_msg, HumanMessage(content=multimodal_content)]
                        response = self._client.invoke(messages)
                        if response and response.content:
                            return str(response.content)
                    except Exception as vision_err:
                        logger.info(
                            "Vision input not supported or failed (%s); trying text prompt.",
                            vision_err,
                        )

                # Text-only message invocation
                messages = [sys_msg, HumanMessage(content=user_content)]
                response = self._client.invoke(messages)
                if response and response.content:
                    return str(response.content)
            except Exception as err:
                logger.warning(
                    "LLM invocation failed (%s). Falling back to structured generator.",
                    err,
                )

        return _generate_fallback_script(
            img_name,
            request.description,
            request.disappear_cnt,
            request.appear_cnt,
        )


_llm_service = LLMService()


def create_script(
    image: str,
    description: str,
    disappear_cnt: int,
    appear_cnt: int,
) -> str:
    """
    Generate a 6-second video script for a given image and object expression.

    Args:
        image: Path or filename of the reference image.
        description: Description of the target object(s) to count.
        disappear_cnt: Number of target objects that should disappear.
        appear_cnt: Number of new target objects that should appear.

    Returns:
        Structured script detailing the 6-second video timeline and prompt.
    """
    request = ScriptInput(
        image_path=image,
        description=description,
        disappear_cnt=max(0, disappear_cnt),
        appear_cnt=max(0, appear_cnt),
    )
    return _llm_service.generate_script(request)
