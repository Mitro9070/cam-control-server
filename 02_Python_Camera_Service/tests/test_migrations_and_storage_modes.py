from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.storage import StorageService
import app.storage as storage_module


SERVICE_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    config = Config(str(SERVICE_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(SERVICE_ROOT / "alembic"))
    return config


def test_migrations_upgrade_and_downgrade_sqlite(monkeypatch, tmp_path):
    sqlite_db_path = tmp_path / "migration_test.db"
    sqlite_url = f"sqlite:///{sqlite_db_path.as_posix()}"
    monkeypatch.setenv("ALEMBIC_SQLALCHEMY_URL", sqlite_url)

    config = _alembic_config()
    command.upgrade(config, "head")

    engine = create_engine(sqlite_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "app_settings",
        "event_log",
        "camera_profiles",
        "camera_session",
        "exposure_job",
        "exposure_image_meta",
    }.issubset(tables)

    command.downgrade(config, "base")
    tables_after_downgrade = set(inspect(engine).get_table_names())
    assert "app_settings" not in tables_after_downgrade
    assert "event_log" not in tables_after_downgrade
    assert "camera_profiles" not in tables_after_downgrade


def test_storage_service_modes_local_and_postgres(monkeypatch):
    monkeypatch.setattr(storage_module.settings, "storage_mode", "local")
    local_service = StorageService()
    assert local_service.health_db_label() == "local"

    class HealthySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def execute(self, statement):  # noqa: ANN001
            return statement

    monkeypatch.setattr(storage_module.settings, "storage_mode", "postgres")
    monkeypatch.setattr(storage_module, "SessionLocal", lambda: HealthySession())
    postgres_service = StorageService()
    assert postgres_service.health_db_label() == "connected"
