import os
from pathlib import Path


TMP_STORAGE_PATH = Path(__file__).parent / ".tmp_storage"
TMP_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

os.environ["STORAGE_MODE"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = str(TMP_STORAGE_PATH)
os.environ["SDK_MODE"] = "mock"


def pytest_sessionstart(session):  # noqa: ARG001
    for p in TMP_STORAGE_PATH.glob("*"):
        p.unlink()
