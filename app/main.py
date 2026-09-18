import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.recommender import Recommendation, recommend_breed, shutdown_recommender

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await shutdown_recommender()


app = FastAPI(title="Dog Breed Picker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/recommend", response_model=Recommendation)
async def recommend(
    image: UploadFile = File(...),
    message: str | None = Form(default=None),
) -> Recommendation:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded image must be 5 MB or smaller.")
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image cannot be empty.")

    try:
        return await recommend_breed(image_bytes, image.content_type, message)
    except Exception:
        logger.exception("Breed recommendation failed")
        raise HTTPException(
            status_code=502,
            detail="The breed recommender is unavailable right now. Please try again.",
        ) from None
