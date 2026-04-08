from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import logging
import time

from app.api.routes import router as api_router
from app.config import settings
from app.logging_setup import configure_logging


app = FastAPI(title="Project_R1 Camera Service", version="0.1.0")
app.include_router(api_router)

configure_logging(settings.log_level)
logger = logging.getLogger("camera-service.main")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    req_id = f"{int(time.time() * 1000)}-{id(request)}"
    started = time.perf_counter()
    logger.info("REQ_START id=%s method=%s path=%s", req_id, request.method, request.url.path)
    try:
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("REQ_END id=%s status=%s elapsed_ms=%s", req_id, response.status_code, elapsed_ms)
        return response
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("REQ_FAIL id=%s elapsed_ms=%s", req_id, elapsed_ms)
        raise


@app.on_event("startup")
async def _startup_log() -> None:
    logger.info(
        "Startup env=%s sdk_mode=%s host=%s port=%s",
        settings.app_env,
        settings.sdk_mode,
        settings.app_host,
        settings.app_port,
    )


ui_dir = Path(__file__).resolve().parents[2] / "05_UI" / "web"
if ui_dir.exists():
    # Редирект без завершающего слэша — иначе браузер часто резолвит ./styles.css в /styles.css (404).
    @app.get("/ui", include_in_schema=False)
    async def _ui_redirect_slash() -> RedirectResponse:
        return RedirectResponse(url="/ui/")

    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
