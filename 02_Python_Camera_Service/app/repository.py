import json
import socket
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting, CameraProfile, CameraSession, EventLog, ExposureImageMeta, ExposureJob


DEFAULT_SETTINGS = {
    "readout_speed": 500,
    "default_gain_mode": "1",
    "default_cooler_level": 1,
    "has_shutter": True,
    "sensor_name_override": "GreatEyes 9.0",
    "sdk_camera_address": "",
    "sdk_camera_port": 12345,
    "sdk_camera_interface": -1,
    "camera_index": 0,
    "temperature_hardware_option": 42223,
    "fits_export_bitpix": 32,
}


def load_settings(db: Session) -> dict:
    merged = DEFAULT_SETTINGS.copy()
    record = db.execute(select(AppSetting).where(AppSetting.key == "camera.defaults")).scalar_one_or_none()
    if record is not None:
        merged.update(json.loads(record.value_json))
    return merged


def save_settings(db: Session, payload: dict) -> dict:
    current = load_settings(db)
    current.update({k: v for k, v in payload.items() if v is not None})

    record = db.execute(select(AppSetting).where(AppSetting.key == "camera.defaults")).scalar_one_or_none()
    if record is None:
        record = AppSetting(key="camera.defaults", value_json=json.dumps(current, ensure_ascii=False))
        db.add(record)
    else:
        record.value_json = json.dumps(current, ensure_ascii=False)
    db.commit()
    return current


def write_event(db: Session, event_type: str, message: str, level: str = "INFO", correlation_id: str | None = None) -> None:
    db.add(
        EventLog(
            level=level,
            source="camera-service",
            event_type=event_type,
            message=message,
            correlation_id=correlation_id,
        )
    )
    db.commit()


def list_events(db: Session, limit: int = 100) -> list[dict]:
    stmt = select(EventLog).order_by(EventLog.id.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": row.id,
            "level": row.level,
            "source": row.source,
            "event_type": row.event_type,
            "message": row.message,
            "correlation_id": row.correlation_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def start_camera_session(db: Session, camera_index: int, model_id: int, model_name: str) -> str:
    session_id = str(uuid.uuid4())
    record = CameraSession(
        id=session_id,
        camera_index=camera_index,
        model_id=model_id,
        model_name=model_name,
        sdk_version="native",
        host_name=socket.gethostname(),
        connected_at=datetime.now(timezone.utc),
        status="connected",
    )
    db.add(record)
    db.commit()
    return session_id


def close_camera_session(db: Session, session_id: str, status: str = "disconnected", error_message: str | None = None) -> None:
    record = db.execute(select(CameraSession).where(CameraSession.id == session_id)).scalar_one_or_none()
    if record is None:
        return
    record.status = status
    record.error_message = error_message
    record.disconnected_at = datetime.now(timezone.utc)
    db.commit()


def create_exposure_job(
    db: Session,
    exposure_id: str,
    session_id: str | None,
    duration_sec: float,
    light_frame: bool,
    state: str,
) -> None:
    record = ExposureJob(
        id=exposure_id,
        session_id=session_id,
        duration_sec=duration_sec,
        light_frame=light_frame,
        state=state,
        started_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()


def update_exposure_job(db: Session, exposure_id: str, state: str, error_message: str | None = None) -> None:
    record = db.execute(select(ExposureJob).where(ExposureJob.id == exposure_id)).scalar_one_or_none()
    if record is None:
        return
    record.state = state
    record.error_message = error_message
    if state in {"completed", "aborted", "stopped", "error"}:
        record.finished_at = datetime.now(timezone.utc)
    db.commit()


def save_exposure_image_meta(
    db: Session,
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
    existing = db.execute(select(ExposureImageMeta).where(ExposureImageMeta.exposure_id == exposure_id)).scalar_one_or_none()
    if existing is not None:
        return
    record = ExposureImageMeta(
        id=str(uuid.uuid4()),
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
    db.add(record)
    db.commit()


def list_camera_profiles(db: Session) -> list[dict]:
    rows = db.execute(select(CameraProfile).order_by(CameraProfile.name.asc())).scalars().all()
    return [
        {
            "profile_id": row.id,
            "name": row.name,
            "is_default": row.is_default,
            "is_active": row.is_active,
            "sdk_camera_address": row.sdk_camera_address,
            "sdk_camera_port": row.sdk_camera_port,
            "sdk_camera_interface": row.sdk_camera_interface,
            "sdk_camera_index": row.sdk_camera_index,
            "temperature_hardware_option": row.temperature_hardware_option,
            "readout_speed": row.readout_speed,
            "gain_mode": row.gain_mode,
        }
        for row in rows
    ]


def create_camera_profile(
    db: Session,
    name: str,
    sdk_camera_address: str,
    sdk_camera_port: int,
    sdk_camera_interface: int,
    sdk_camera_index: int,
    temperature_hardware_option: int,
    readout_speed: int,
    gain_mode: str,
) -> dict:
    record = CameraProfile(
        id=str(uuid.uuid4()),
        name=name,
        sdk_camera_address=sdk_camera_address,
        sdk_camera_port=sdk_camera_port,
        sdk_camera_interface=sdk_camera_interface,
        sdk_camera_index=sdk_camera_index,
        temperature_hardware_option=temperature_hardware_option,
        readout_speed=readout_speed,
        gain_mode=gain_mode,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "profile_id": record.id,
        "name": record.name,
        "is_default": record.is_default,
        "is_active": record.is_active,
        "sdk_camera_address": record.sdk_camera_address,
        "sdk_camera_port": record.sdk_camera_port,
        "sdk_camera_interface": record.sdk_camera_interface,
        "sdk_camera_index": record.sdk_camera_index,
        "temperature_hardware_option": record.temperature_hardware_option,
        "readout_speed": record.readout_speed,
        "gain_mode": record.gain_mode,
    }


def update_camera_profile(
    db: Session,
    profile_id: str,
    payload: dict,
) -> dict | None:
    record = db.execute(select(CameraProfile).where(CameraProfile.id == profile_id)).scalar_one_or_none()
    if record is None:
        return None
    for key, value in payload.items():
        if value is not None and hasattr(record, key):
            setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return {
        "profile_id": record.id,
        "name": record.name,
        "is_default": record.is_default,
        "is_active": record.is_active,
        "sdk_camera_address": record.sdk_camera_address,
        "sdk_camera_port": record.sdk_camera_port,
        "sdk_camera_interface": record.sdk_camera_interface,
        "sdk_camera_index": record.sdk_camera_index,
        "temperature_hardware_option": record.temperature_hardware_option,
        "readout_speed": record.readout_speed,
        "gain_mode": record.gain_mode,
    }


def activate_camera_profile(db: Session, profile_id: str) -> dict | None:
    rows = db.execute(select(CameraProfile)).scalars().all()
    target: CameraProfile | None = None
    for row in rows:
        row.is_active = row.id == profile_id
        if row.id == profile_id:
            target = row
    if target is None:
        db.rollback()
        return None
    db.commit()
    db.refresh(target)
    return {
        "profile_id": target.id,
        "name": target.name,
        "is_default": target.is_default,
        "is_active": target.is_active,
        "sdk_camera_address": target.sdk_camera_address,
        "sdk_camera_port": target.sdk_camera_port,
        "sdk_camera_interface": target.sdk_camera_interface,
        "sdk_camera_index": target.sdk_camera_index,
        "temperature_hardware_option": target.temperature_hardware_option,
        "readout_speed": target.readout_speed,
        "gain_mode": target.gain_mode,
    }
