from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="camera-service")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CameraProfile(Base):
    __tablename__ = "camera_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sdk_camera_address: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    sdk_camera_port: Mapped[int] = mapped_column(Integer, nullable=False, default=12345)
    sdk_camera_interface: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    sdk_camera_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    temperature_hardware_option: Mapped[int] = mapped_column(Integer, nullable=False, default=42223)
    readout_speed: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    gain_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    cooler_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_temp_c: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bin_x: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bin_y: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    num_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exposure_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CameraSession(Base):
    __tablename__ = "camera_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sdk_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    host_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="connected")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExposureJob(Base):
    __tablename__ = "exposure_job"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("camera_session.id"), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("camera_profiles.id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    light_frame: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExposureImageMeta(Base):
    __tablename__ = "exposure_image_meta"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    exposure_id: Mapped[str] = mapped_column(String(64), ForeignKey("exposure_job.id"), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    bit_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=16)
    pixel_type: Mapped[str] = mapped_column(String(32), nullable=False, default="uint16")
    orientation: Mapped[str] = mapped_column(String(64), nullable=False, default="top_left_origin")
    bin_x: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bin_y: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
