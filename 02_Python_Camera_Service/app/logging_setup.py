from __future__ import annotations

import faulthandler
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(log_level: str) -> Path:
    service_root = Path(__file__).resolve().parents[1]
    log_dir = service_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "camera_service.log"
    fault_file = log_dir / "camera_service_fault.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT)
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    # Native crashes (access violation) may bypass Python exceptions.
    fault_fd = os.open(str(fault_file), os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    faulthandler.enable(file=os.fdopen(fault_fd, "a", encoding="utf-8", buffering=1), all_threads=True)

    def _threading_hook(args) -> None:
        logging.getLogger("camera-service.threading").exception(
            "Unhandled thread exception in %s",
            getattr(args.thread, "name", "<unknown>"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    if hasattr(sys, "excepthook"):
        prev_hook = sys.excepthook

        def _excepthook(exc_type, exc_value, exc_tb) -> None:
            logging.getLogger("camera-service").exception(
                "Unhandled exception",
                exc_info=(exc_type, exc_value, exc_tb),
            )
            prev_hook(exc_type, exc_value, exc_tb)

        sys.excepthook = _excepthook

    try:
        import threading

        threading.excepthook = _threading_hook
    except Exception:
        pass

    logging.getLogger("camera-service").info("Logging initialized: %s", log_file)
    return log_file
