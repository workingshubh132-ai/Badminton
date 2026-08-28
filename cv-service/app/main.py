from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import ENGINE_VERSION, INTERNAL_TOKEN, SERVICE_NAME
from app.detection import PersonDetector
from app.pipeline import run_analysis
from app.schemas import AnalysisResult, AnalyzeRequest

logger = logging.getLogger("cv_service")
# Deliberately never logs frame pixel data or full file paths' contents —
# see docs/CV_ARCHITECTURE.md "Observability". Paths and ids are fine; bytes
# are not.
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading person-detection model...")
    app.state.detector = PersonDetector()
    logger.info("Model loaded.")
    yield
    app.state.detector.close()


app = FastAPI(title=SERVICE_NAME, version=ENGINE_VERSION, lifespan=lifespan)


def _check_internal_token(x_internal_token: str | None) -> None:
    # Defense-in-depth only — this service is never meant to be
    # internet-facing. See docs/CV_ARCHITECTURE.md "Security".
    if INTERNAL_TOKEN and x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing internal token.")


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": ENGINE_VERSION,
        "model_loaded": request.app.state.detector is not None,
    }


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(
    body: AnalyzeRequest,
    request: Request,
    x_internal_token: str | None = Header(default=None),
) -> AnalysisResult | JSONResponse:
    _check_internal_token(x_internal_token)

    video_path = Path(body.video_path)
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail=f"video_path does not exist: {body.video_path}")

    try:
        return run_analysis(
            video_path=video_path,
            detector=request.app.state.detector,
            sampling_fps=body.sampling_fps,
            max_sampled_frames=body.max_sampled_frames,
        )
    except Exception:
        # A genuine service-level failure (crash partway through), distinct
        # from an honest "completed but low-quality/no-detections" result —
        # see docs/CV_ARCHITECTURE.md "Failure handling". The caller (the
        # Next.js CVAnalysisEngine implementation) maps a 500 here to its
        # own status: "failed", never to a fabricated result.
        logger.exception("Analysis failed for video_id=%s", body.video_id)
        raise HTTPException(status_code=500, detail="Analysis failed due to an internal error.")
