from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.repository import (
    DEFAULT_SETTINGS,
    activate_camera_profile,
    create_camera_profile,
    close_camera_session,
    create_exposure_job,
    list_camera_profiles,
    list_events,
    load_settings,
    save_exposure_image_meta,
    save_settings,
    start_camera_session,
    update_camera_profile,
    update_exposure_job,
    write_event,
)

logger = logging.getLogger("camera-service.storage")


class StorageService:
    def __init__(self) -> None:
        self.mode = settings.storage_mode.lower()
        self._db_disabled_until_monotonic = 0.0
        self.local_path = Path(settings.local_storage_path)
        self.settings_file = self.local_path / "settings.json"
        self.events_file = self.local_path / "events.jsonl"
        self.profiles_file = self.local_path / "camera_profiles.json"
        if self.mode == "local":
            self.local_path.mkdir(parents=True, exist_ok=True)

    def _db_temporarily_unavailable(self) -> bool:
        return time.monotonic() < self._db_disabled_until_monotonic

    def _mark_db_unavailable(self, cooldown_sec: float = 60.0) -> None:
        self._db_disabled_until_monotonic = max(
            self._db_disabled_until_monotonic,
            time.monotonic() + cooldown_sec,
        )

    def health_db_label(self) -> str:
        if self.mode == "local":
            return "local"
        if self._db_temporarily_unavailable():
            return "unavailable"
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            return "connected"
        except Exception:
            self._mark_db_unavailable()
            return "unavailable"

    def get_settings(self) -> dict:
        if self.mode == "local":
            merged = DEFAULT_SETTINGS.copy()
            if self.settings_file.exists():
                merged.update(json.loads(self.settings_file.read_text(encoding="utf-8")))
            return merged
        try:
            with SessionLocal() as db:
                return load_settings(db)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in get_settings; using defaults: %s", exc)
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, payload: dict) -> dict:
        if self.mode == "local":
            current = self.get_settings()
            current.update({k: v for k, v in payload.items() if v is not None})
            self.settings_file.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            return current
        if self._db_temporarily_unavailable():
            current = DEFAULT_SETTINGS.copy()
            current.update({k: v for k, v in payload.items() if v is not None})
            return current
        try:
            with SessionLocal() as db:
                return save_settings(db, payload)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in save_settings; returning in-memory merge: %s", exc)
            current = DEFAULT_SETTINGS.copy()
            current.update({k: v for k, v in payload.items() if v is not None})
            return current

    def list_camera_profiles(self) -> list[dict]:
        if self.mode == "local":
            if not self.profiles_file.exists():
                return []
            return json.loads(self.profiles_file.read_text(encoding="utf-8"))
        if self._db_temporarily_unavailable():
            return []
        try:
            with SessionLocal() as db:
                return list_camera_profiles(db)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in list_camera_profiles; returning empty list: %s", exc)
            return []

    def create_camera_profile(self, payload: dict) -> dict:
        if self.mode == "local":
            profiles = self.list_camera_profiles()
            record = {
                "profile_id": payload["profile_id"],
                "name": payload["name"],
                "is_default": False,
                "is_active": False,
                "sdk_camera_address": payload["sdk_camera_address"],
                "sdk_camera_port": payload["sdk_camera_port"],
                "sdk_camera_interface": payload["sdk_camera_interface"],
                "sdk_camera_index": payload["sdk_camera_index"],
                "temperature_hardware_option": payload["temperature_hardware_option"],
                "readout_speed": payload["readout_speed"],
                "gain_mode": payload["gain_mode"],
            }
            profiles.append(record)
            self.profiles_file.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
            return record
        with SessionLocal() as db:
            try:
                return create_camera_profile(
                    db,
                    name=payload["name"],
                    sdk_camera_address=payload["sdk_camera_address"],
                    sdk_camera_port=payload["sdk_camera_port"],
                    sdk_camera_interface=payload["sdk_camera_interface"],
                    sdk_camera_index=payload["sdk_camera_index"],
                    temperature_hardware_option=payload["temperature_hardware_option"],
                    readout_speed=payload["readout_speed"],
                    gain_mode=payload["gain_mode"],
                )
            except Exception as exc:
                logger.warning("DB unavailable in create_camera_profile: %s", exc)
                raise

    def update_camera_profile(self, profile_id: str, payload: dict) -> dict | None:
        if self.mode == "local":
            profiles = self.list_camera_profiles()
            updated: dict | None = None
            for row in profiles:
                if row.get("profile_id") != profile_id:
                    continue
                for key, value in payload.items():
                    if value is not None and key in row:
                        row[key] = value
                updated = row
                break
            if updated is None:
                return None
            self.profiles_file.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
            return updated
        if self._db_temporarily_unavailable():
            logger.warning("DB unavailable in update_camera_profile: cooldown active")
            raise RuntimeError("database unavailable")
        try:
            with SessionLocal() as db:
                return update_camera_profile(db, profile_id=profile_id, payload=payload)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in update_camera_profile: %s", exc)
            raise

    def activate_camera_profile(self, profile_id: str) -> dict | None:
        if self.mode == "local":
            profiles = self.list_camera_profiles()
            target = None
            for row in profiles:
                row["is_active"] = row.get("profile_id") == profile_id
                if row["is_active"]:
                    target = row
            if target is None:
                return None
            self.profiles_file.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
            return target
        if self._db_temporarily_unavailable():
            logger.warning("DB unavailable in activate_camera_profile: cooldown active")
            raise RuntimeError("database unavailable")
        try:
            with SessionLocal() as db:
                return activate_camera_profile(db, profile_id=profile_id)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in activate_camera_profile: %s", exc)
            raise

    def write_event(self, event_type: str, message: str, level: str = "INFO", correlation_id: str | None = None) -> None:
        if self.mode == "local":
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "source": "camera-service",
                "event_type": event_type,
                "message": message,
                "correlation_id": correlation_id,
            }
            with self.events_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")
            return
        if self._db_temporarily_unavailable():
            return
        try:
            with SessionLocal() as db:
                write_event(db, event_type=event_type, message=message, level=level, correlation_id=correlation_id)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in write_event; skipping event_type=%s: %s", event_type, exc)

    def read_events(self, limit: int = 100) -> list[dict]:
        safe_limit = max(1, min(limit, 500))
        if self.mode == "local":
            if not self.events_file.exists():
                return []
            lines = self.events_file.read_text(encoding="utf-8").splitlines()
            result = []
            for raw_line in reversed(lines[-safe_limit:]):
                try:
                    result.append(json.loads(raw_line))
                except json.JSONDecodeError:
                    continue
            return result
        if self._db_temporarily_unavailable():
            return []
        try:
            with SessionLocal() as db:
                return list_events(db, limit=safe_limit)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in read_events; returning empty list: %s", exc)
            return []

    def start_camera_session(self, camera_index: int, model_id: int, model_name: str) -> str | None:
        if self.mode == "local":
            return None
        if self._db_temporarily_unavailable():
            return None
        try:
            with SessionLocal() as db:
                return start_camera_session(db, camera_index=camera_index, model_id=model_id, model_name=model_name)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in start_camera_session; continuing without session id: %s", exc)
            return None

    def close_camera_session(self, session_id: str | None, status: str = "disconnected", error_message: str | None = None) -> None:
        if self.mode == "local" or not session_id:
            return
        if self._db_temporarily_unavailable():
            return
        try:
            with SessionLocal() as db:
                close_camera_session(db, session_id=session_id, status=status, error_message=error_message)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in close_camera_session; skipping close: %s", exc)

    def create_exposure_job(
        self,
        exposure_id: str,
        session_id: str | None,
        duration_sec: float,
        light_frame: bool,
        state: str,
    ) -> None:
        if self.mode == "local":
            return
        if self._db_temporarily_unavailable():
            return
        try:
            with SessionLocal() as db:
                create_exposure_job(
                    db,
                    exposure_id=exposure_id,
                    session_id=session_id,
                    duration_sec=duration_sec,
                    light_frame=light_frame,
                    state=state,
                )
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in create_exposure_job; skipping persist: %s", exc)

    def update_exposure_job(self, exposure_id: str, state: str, error_message: str | None = None) -> None:
        if self.mode == "local":
            return
        if self._db_temporarily_unavailable():
            return
        try:
            with SessionLocal() as db:
                update_exposure_job(db, exposure_id=exposure_id, state=state, error_message=error_message)
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in update_exposure_job; skipping persist: %s", exc)

    def save_exposure_image_meta(
        self,
        exposure_id: str,
        width: int,
        height: int,
        pixel_type: str,
        orientation: str,
        bin_x: int,
        bin_y: int,
        start_x: int,
        start_y: int,
    ) -> None:
        if self.mode == "local":
            return
        if self._db_temporarily_unavailable():
            return
        try:
            with SessionLocal() as db:
                save_exposure_image_meta(
                    db,
                    exposure_id=exposure_id,
                    width=width,
                    height=height,
                    pixel_type=pixel_type,
                    orientation=orientation,
                    bin_x=bin_x,
                    bin_y=bin_y,
                    start_x=start_x,
                    start_y=start_y,
                )
        except Exception as exc:
            self._mark_db_unavailable()
            logger.warning("DB unavailable in save_exposure_image_meta; skipping persist: %s", exc)


storage_service = StorageService()
