"""
LLM Guardrails Studio
---------------------
FastAPI backend for Gemini with input and output guardrails.

Project structure:
    guardrails/
        input_guardrails.py
        output_guardrails.py

    services/
        gemini_service.py
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from guardrails.input_guardrails import check_input
from guardrails.output_guardrails import check_output
from services.gemini_service import generate_response


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("llm-guardrails")


# ============================================================
# Application Configuration
# ============================================================

APP_NAME = "LLM Guardrails Studio"
APP_VERSION = "1.0.0"
AUTHOR = "Ajim Mujawar"


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description=(
        "A Gemini-powered FastAPI application with "
        "input and output guardrails."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Static Files and Templates
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# Request Model
# ============================================================

class PromptRequest(BaseModel):
    """
    Request body received from the frontend.
    """

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User prompt to process.",
    )


# ============================================================
# Helper Functions
# ============================================================

def create_stage(
    name: str,
    status: str,
    message: str,
    category: str | None = None,
    duration_ms: float | None = None,
) -> dict[str, Any]:
    """
    Create a standard pipeline stage response.
    """

    return {
        "name": name,
        "status": status,
        "message": message,
        "category": category,
        "duration_ms": duration_ms,
    }


def get_category(result: dict[str, Any]) -> str:
    """
    Safely get category from guardrail result.
    """

    return str(
        result.get("category") or "SAFE"
    )


def create_error_response(
    *,
    request_id: str,
    stage: str,
    category: str,
    message: str,
    stages: list[dict[str, Any]],
    started_at: float,
    metrics: dict[str, float],
) -> dict[str, Any]:
    """
    Create a consistent error response.
    """

    total_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    metrics["total_ms"] = total_ms

    return {
        "status": "error",
        "stage": stage,
        "request_id": request_id,
        "category": category,
        "message": message,
        "response": None,
        "stages": stages,
        "metrics": metrics,
    }


# ============================================================
# Home Page
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Render the main Guardrails Studio UI.
    """

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "author": AUTHOR,
        },
    )


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
async def health():
    """
    Check whether the API is running.
    """

    return {
        "status": "healthy",
        "application": APP_NAME,
        "version": APP_VERSION,
        "components": {
            "fastapi": "online",
            "input_guardrail": "online",
            "gemini": "configured",
            "output_guardrail": "online",
        },
    }


# ============================================================
# API Information
# ============================================================

@app.get("/api/info")
async def api_info():
    """
    Return information about the application pipeline.
    """

    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "author": AUTHOR,
        "pipeline": [
            "User Prompt",
            "Input Guardrail",
            "Gemini LLM",
            "Output Guardrail",
            "Safe Response",
        ],
    }


# ============================================================
# Generate Response
# ============================================================

@app.post("/generate")
async def generate(request: PromptRequest):
    """
    Main LLM processing pipeline.

    Flow:

        User Prompt
             ↓
        Input Guardrail
             ↓
           Gemini
             ↓
        Output Guardrail
             ↓
        Final Response
    """

    request_id = str(uuid.uuid4())
    started_at = time.perf_counter()

    stages: list[dict[str, Any]] = []

    user_input = request.prompt.strip()

    logger.info(
        "Request received | request_id=%s",
        request_id,
    )

    # ========================================================
    # Stage 1: Input Guardrail
    # ========================================================

    stage_started = time.perf_counter()

    try:
        input_result = check_input(user_input)

    except Exception:
        logger.exception(
            "Input guardrail failed | request_id=%s",
            request_id,
        )

        duration_ms = round(
            (time.perf_counter() - stage_started) * 1000,
            2,
        )

        stages.append(
            create_stage(
                name="Input Guardrail",
                status="error",
                message="Input safety check failed.",
                category="GUARDRAIL_ERROR",
                duration_ms=duration_ms,
            )
        )

        return create_error_response(
            request_id=request_id,
            stage="input_guardrail",
            category="GUARDRAIL_ERROR",
            message="Unable to complete the input safety check.",
            stages=stages,
            started_at=started_at,
            metrics={
                "input_guardrail_ms": duration_ms,
            },
        )

    input_ms = round(
        (time.perf_counter() - stage_started) * 1000,
        2,
    )

    input_allowed = bool(
        input_result.get("allowed")
    )

    input_category = get_category(input_result)

    stages.append(
        create_stage(
            name="Input Guardrail",
            status="passed" if input_allowed else "blocked",
            message=str(
                input_result.get(
                    "message",
                    "Input checked.",
                )
            ),
            category=input_category,
            duration_ms=input_ms,
        )
    )

    # --------------------------------------------------------
    # Block unsafe input
    # --------------------------------------------------------

    if not input_allowed:

        total_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        logger.warning(
            "Input blocked | request_id=%s | category=%s",
            request_id,
            input_category,
        )

        return {
            "status": "blocked",
            "stage": "input_guardrail",
            "request_id": request_id,
            "category": input_category,
            "message": input_result.get(
                "message",
                "Input blocked by guardrails.",
            ),
            "response": None,
            "stages": stages,
            "metrics": {
                "total_ms": total_ms,
                "input_guardrail_ms": input_ms,
            },
        }

    # ========================================================
    # Stage 2: Gemini
    # ========================================================

    stage_started = time.perf_counter()

    try:
        model_response = generate_response(
            user_input
        )

    except Exception:
        logger.exception(
            "Gemini request failed | request_id=%s",
            request_id,
        )

        llm_ms = round(
            (time.perf_counter() - stage_started) * 1000,
            2,
        )

        stages.append(
            create_stage(
                name="Gemini LLM",
                status="error",
                message="Gemini could not generate a response.",
                category="MODEL_ERROR",
                duration_ms=llm_ms,
            )
        )

        return create_error_response(
            request_id=request_id,
            stage="llm",
            category="MODEL_ERROR",
            message=(
                "The Gemini request failed. "
                "Please check the Gemini service configuration."
            ),
            stages=stages,
            started_at=started_at,
            metrics={
                "input_guardrail_ms": input_ms,
                "llm_ms": llm_ms,
            },
        )

    llm_ms = round(
        (time.perf_counter() - stage_started) * 1000,
        2,
    )

    stages.append(
        create_stage(
            name="Gemini LLM",
            status="passed",
            message="Model response generated.",
            category="GENERATED",
            duration_ms=llm_ms,
        )
    )

    # ========================================================
    # Stage 3: Output Guardrail
    # ========================================================

    stage_started = time.perf_counter()

    try:
        output_result = check_output(
            model_response
        )

    except Exception:
        logger.exception(
            "Output guardrail failed | request_id=%s",
            request_id,
        )

        output_ms = round(
            (time.perf_counter() - stage_started) * 1000,
            2,
        )

        stages.append(
            create_stage(
                name="Output Guardrail",
                status="error",
                message="Output safety check failed.",
                category="GUARDRAIL_ERROR",
                duration_ms=output_ms,
            )
        )

        return create_error_response(
            request_id=request_id,
            stage="output_guardrail",
            category="GUARDRAIL_ERROR",
            message=(
                "Unable to complete the output safety check."
            ),
            stages=stages,
            started_at=started_at,
            metrics={
                "input_guardrail_ms": input_ms,
                "llm_ms": llm_ms,
                "output_guardrail_ms": output_ms,
            },
        )

    output_ms = round(
        (time.perf_counter() - stage_started) * 1000,
        2,
    )

    output_allowed = bool(
        output_result.get("allowed")
    )

    output_category = get_category(
        output_result
    )

    stages.append(
        create_stage(
            name="Output Guardrail",
            status="passed" if output_allowed else "blocked",
            message=str(
                output_result.get(
                    "message",
                    "Output checked.",
                )
            ),
            category=output_category,
            duration_ms=output_ms,
        )
    )

    # --------------------------------------------------------
    # Block unsafe output
    # --------------------------------------------------------

    if not output_allowed:

        total_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        logger.warning(
            "Output blocked | request_id=%s | category=%s",
            request_id,
            output_category,
        )

        return {
            "status": "blocked",
            "stage": "output_guardrail",
            "request_id": request_id,
            "category": output_category,
            "message": output_result.get(
                "message",
                "Output blocked by guardrails.",
            ),
            "response": None,
            "stages": stages,
            "metrics": {
                "total_ms": total_ms,
                "input_guardrail_ms": input_ms,
                "llm_ms": llm_ms,
                "output_guardrail_ms": output_ms,
            },
        }

    # ========================================================
    # Stage 4: Successful Response
    # ========================================================

    total_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    logger.info(
        "Request completed | request_id=%s | total_ms=%s",
        request_id,
        total_ms,
    )

    return {
        "status": "success",
        "stage": "completed",
        "request_id": request_id,
        "category": "SAFE",
        "message": (
            "Response passed input and output "
            "guardrails successfully."
        ),
        "response": model_response,
        "stages": stages,
        "metrics": {
            "total_ms": total_ms,
            "input_guardrail_ms": input_ms,
            "llm_ms": llm_ms,
            "output_guardrail_ms": output_ms,
        },
    }