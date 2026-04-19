from __future__ import annotations

import base64
import logging
import re
import struct
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.sdk_adapter import BaseSdkAdapter, CameraCapabilities, CameraInfo, MockGreatEyesSdkAdapter, NativeGreatEyesSdkAdapter, SdkError, SdkErrorCode
from app.storage import storage_service

logger = logging.getLogger("camera-service.runtime")

RUNTIME_VERSION = "2.4"


@dataclass
class RuntimeState:
    connected: bool = False
    camera_state: str = "disconnected"
    image_ready: bool = False
    active_exposure_id: str | None = None
    camera_info: CameraInfo | None = None
    capabilities: CameraCapabilities | None = None
    bin_x: int = 1
    bin_y: int = 1
    num_x: int = 2048
    num_y: int = 2052
    start_x: int = 0
    start_y: int = 0
    cooler_on: bool = False
    ccd_temp_c: int = 20
    target_temp_c: int = 20
    cooler_power_percent: int = 0
    active_session_id: str | None = None


@dataclass
class ExposureJob:
    exposure_id: str
    duration_sec: float
    light: bool
    state: str
    image_ready: bool
    percent: int = 0
    error: str | None = None
    completion_logged: bool = False
    bin_x: int = 1
    bin_y: int = 1
    num_x: int = 2048
    num_y: int = 2052
    start_x: int = 0
    start_y: int = 0


@dataclass
class WarmupJob:
    warmup_job_id: str
    state: str
    target_temp_c: int
    temp_step_c: int
    power_step_percent: int
    step_interval_sec: float
    current_temp_c: int
    current_power_percent: int
    previous_controller_mode: str = "balanced"
    error: str | None = None
    completion_logged: bool = False


@dataclass
class CoolingTelemetrySample:
    timestamp: str
    mode: str
    requested_target_temp_c: float
    control_target_temp_c: float
    ccd_temp_c: float
    backside_temp_c: float
    cooler_power_percent: int
    alert: str | None = None


class CameraRuntime:
    def __init__(self) -> None:
        self._state = RuntimeState()
        self._adapter = self._create_adapter()
        self._exposures: dict[str, ExposureJob] = {}
        self._latest_image: dict | None = None
        self._latest_frame_bytes: bytes | None = None
        self._warmups: dict[str, WarmupJob] = {}
        self._lock = threading.Lock()
        self._controller_mode = "balanced"
        self._requested_target_temp_c = float(self._state.target_temp_c)
        self._control_target_temp_c = float(self._state.target_temp_c)
        self._integral_term = 0.0
        self._last_alert: str | None = None
        self._telemetry: list[CoolingTelemetrySample] = []
        self._last_control_apply_at = 0.0
        self._last_applied_target_temp: int | None = None
        self._controller_thread = threading.Thread(target=self._cooling_control_loop, daemon=True)
        self._controller_thread.start()
        self._exports_dir = Path(__file__).resolve().parents[1] / "exports"
        self._exports_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _controller_profiles() -> dict[str, dict]:
        return {
            "safe": {"ramp_c_per_min": 0.25, "kp": 6.0, "ki": 0.03, "u_max": 70.0, "deadband": 0.25},
            "balanced": {"ramp_c_per_min": 0.6, "kp": 8.0, "ki": 0.05, "u_max": 85.0, "deadband": 0.2},
            "fast": {"ramp_c_per_min": 1.2, "kp": 10.0, "ki": 0.08, "u_max": 95.0, "deadband": 0.15},
        }

    def set_controller_mode(self, mode: str) -> dict:
        mode_key = mode.lower().strip()
        if mode_key not in self._controller_profiles():
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="controller mode must be safe|balanced|fast")
        with self._lock:
            self._controller_mode = mode_key
            # Prevent old integral from causing step jumps after mode switch.
            self._integral_term = 0.0
        return self.controller_status()

    def _has_running_warmup(self) -> bool:
        return any(job.state == "running" for job in self._warmups.values())

    def controller_status(self) -> dict:
        with self._lock:
            return {
                "mode": self._controller_mode,
                "requested_target_temp_c": round(self._requested_target_temp_c, 3),
                "control_target_temp_c": round(self._control_target_temp_c, 3),
                "integral_term": round(self._integral_term, 3),
                "cooler_power_percent": self._state.cooler_power_percent,
                "running_warmup": self._has_running_warmup(),
                "last_alert": self._last_alert,
            }

    def cooling_telemetry(self, limit: int = 120) -> list[dict]:
        safe_limit = max(1, min(limit, 1000))
        with self._lock:
            return [asdict(item) for item in self._telemetry[-safe_limit:]]

    def _append_telemetry(self, backside_temp_c: float, alert: str | None = None) -> None:
        sample = CoolingTelemetrySample(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=self._controller_mode,
            requested_target_temp_c=self._requested_target_temp_c,
            control_target_temp_c=self._control_target_temp_c,
            ccd_temp_c=float(self._state.ccd_temp_c),
            backside_temp_c=float(backside_temp_c),
            cooler_power_percent=int(self._state.cooler_power_percent),
            alert=alert,
        )
        self._telemetry.append(sample)
        if len(self._telemetry) > 2000:
            self._telemetry = self._telemetry[-2000:]

    def _log_cooling_state(self, reason: str, **extra: object) -> None:
        payload = {
            "reason": reason,
            "v": RUNTIME_VERSION,
            "cooler_on": self._state.cooler_on,
            "state_target": self._state.target_temp_c,
            "requested": round(self._requested_target_temp_c, 3),
            "control": round(self._control_target_temp_c, 3),
            "ccd": self._state.ccd_temp_c,
            "power": self._state.cooler_power_percent,
            "integral": round(self._integral_term, 3),
            "last_sdk_target": self._last_applied_target_temp,
            "alert": self._last_alert,
        }
        payload.update(extra)
        logger.info("COOLING_TRACE %s", payload)

    def _retry_apply_target_with_fallback(self, exc: SdkError) -> bool:
        match = re.search(r"out of range\s+(-?\d+)\.\.(-?\d+)", str(exc))
        if match is None:
            return False
        low = int(match.group(1))
        high = int(match.group(2))
        fallback_target = int(round(min(max(self._requested_target_temp_c, low), high)))
        if self._last_applied_target_temp == fallback_target:
            return False
        self._adapter.set_target_temperature(settings.camera_index, fallback_target)
        self._control_target_temp_c = float(fallback_target)
        self._last_applied_target_temp = fallback_target
        self._last_control_apply_at = time.monotonic()
        self._last_alert = f"apply_target_clamped:{low}..{high}"
        self._log_cooling_state(
            "apply_target_clamped",
            fallback_target=fallback_target,
            range_low=low,
            range_high=high,
        )
        return True

    def _cooling_control_loop(self) -> None:
        logger.info("cooling controller thread started (RUNTIME_VERSION=%s)", RUNTIME_VERSION)
        while True:
            time.sleep(1.0)
            with self._lock:
                if not self._state.connected or not self._state.cooler_on:
                    continue
                if self._has_running_warmup():
                    continue
                profile = self._controller_profiles()[self._controller_mode]
                ramp_per_sec = float(profile["ramp_c_per_min"]) / 60.0
                if self._control_target_temp_c < self._requested_target_temp_c:
                    self._control_target_temp_c = min(
                        self._requested_target_temp_c,
                        self._control_target_temp_c + ramp_per_sec,
                    )
                else:
                    self._control_target_temp_c = max(
                        self._requested_target_temp_c,
                        self._control_target_temp_c - ramp_per_sec,
                    )

                try:
                    ccd_temp, backside_temp = self._adapter.get_temperatures(settings.camera_index)
                    self._state.ccd_temp_c = ccd_temp
                    self._last_alert = None
                except SdkError:
                    self._append_telemetry(backside_temp_c=max(self._state.ccd_temp_c + 12, 20), alert="temperature_read_failed")
                    continue

                # Self-heal stale control target after reconnect / manual power toggles.
                # If CCD is on one side of the requested target and control target is
                # on the opposite side, the controller will clamp power to zero and
                # stop moving. Snap back to the operator request in that case.
                ccd_vs_requested = float(self._state.ccd_temp_c) - self._requested_target_temp_c
                control_vs_requested = self._control_target_temp_c - self._requested_target_temp_c
                if (ccd_vs_requested >= 0 and control_vs_requested < 0) or (
                    ccd_vs_requested <= 0 and control_vs_requested > 0
                ):
                    self._control_target_temp_c = float(self._requested_target_temp_c)
                    self._integral_term = 0.0
                    self._log_cooling_state("control_target_resync")

                if backside_temp >= 55:
                    self._state.cooler_power_percent = 0
                    self._last_alert = "backside_overheat"
                    self._append_telemetry(backside_temp_c=backside_temp, alert=self._last_alert)
                    try:
                        self._adapter.switch_off_cooling(settings.camera_index)
                    except SdkError:
                        pass
                    self._state.cooler_on = False
                    self._state.target_temp_c = int(self._state.ccd_temp_c)
                    self._requested_target_temp_c = float(self._state.target_temp_c)
                    self._control_target_temp_c = float(self._state.target_temp_c)
                    self._integral_term = 0.0
                    continue

                # Positive error = CCD warmer than target = need more cooling power.
                error = float(self._state.ccd_temp_c) - self._control_target_temp_c
                proportional = float(profile["kp"]) * error
                deadband = float(profile["deadband"])
                if abs(error) > deadband:
                    candidate_integral = self._integral_term + float(profile["ki"]) * error
                else:
                    candidate_integral = self._integral_term * 0.95
                unclamped = proportional + candidate_integral
                u_max = float(profile["u_max"])
                clamped = max(0.0, min(u_max, unclamped))

                saturated_high = clamped >= u_max and error > 0
                saturated_low = clamped <= 0.0 and error < 0
                if not saturated_high and not saturated_low:
                    self._integral_term = candidate_integral

                self._state.cooler_power_percent = int(round(clamped))
                now = time.monotonic()
                target_to_apply = int(round(self._control_target_temp_c))
                if (
                    self._last_applied_target_temp is None
                    or abs(target_to_apply - self._last_applied_target_temp) >= 1
                ) and (now - self._last_control_apply_at) >= 1.5:
                    try:
                        self._adapter.set_target_temperature(settings.camera_index, target_to_apply)
                        self._last_applied_target_temp = target_to_apply
                        self._last_control_apply_at = now
                        logger.info(
                            "cooling controller apply_sdk target_to_apply=%s requested_target=%s control_target=%s ccd=%s",
                            target_to_apply,
                            self._requested_target_temp_c,
                            self._control_target_temp_c,
                            self._state.ccd_temp_c,
                        )
                    except SdkError as exc:
                        if not self._retry_apply_target_with_fallback(exc):
                            self._last_alert = f"apply_target_failed:{exc}"
                self._log_cooling_state("tick", error=round(error, 3), target_to_apply=target_to_apply)
                self._append_telemetry(backside_temp_c=backside_temp, alert=self._last_alert)

    @staticmethod
    def _create_adapter() -> BaseSdkAdapter:
        if settings.sdk_mode == "native":
            return NativeGreatEyesSdkAdapter(settings.sdk_dll_path)
        return MockGreatEyesSdkAdapter()

    @property
    def state(self) -> RuntimeState:
        return self._state

    def connect(self) -> RuntimeState:
        # If already connected & SDK responds, preserve cooling state (MaxIm DL
        # creates a fresh COM object on every launch and calls connect again).
        if self._state.connected and self._state.camera_info is not None:
            try:
                self._adapter.get_temperatures(settings.camera_index)
                logger.info(
                    "CONNECT already_connected=True, preserving cooling state "
                    "cooler_on=%s target=%s ccd=%s v=%s",
                    self._state.cooler_on,
                    self._state.target_temp_c,
                    self._state.ccd_temp_c,
                    RUNTIME_VERSION,
                )
                return self._state
            except SdkError:
                logger.warning("CONNECT already_connected=True but SDK check failed, re-connecting")

        logger.info("CONNECT camera_index=%s runtime_version=%s", settings.camera_index, RUNTIME_VERSION)
        info = self._adapter.connect(settings.camera_index)
        caps = self._adapter.capabilities(settings.camera_index, settings.camera_has_shutter)
        self._state.connected = True
        self._state.camera_state = "idle"
        self._state.image_ready = False
        self._state.active_exposure_id = None
        self._state.camera_info = info
        self._state.capabilities = caps
        self._state.cooler_on = False
        self._state.ccd_temp_c = 20
        self._state.target_temp_c = 20
        self._state.cooler_power_percent = 0
        self._requested_target_temp_c = float(self._state.target_temp_c)
        self._control_target_temp_c = float(self._state.target_temp_c)
        self._integral_term = 0.0
        self._last_alert = None
        self._state.num_x = caps.camera_x_size
        self._state.num_y = caps.camera_y_size
        self._log_cooling_state("connect_fresh")
        return self._state

    def disconnect(self) -> RuntimeState:
        if self._state.connected:
            self._adapter.disconnect(settings.camera_index)
        self._state.connected = False
        self._state.camera_state = "disconnected"
        self._state.image_ready = False
        self._state.active_exposure_id = None
        self._state.cooler_on = False
        self._state.cooler_power_percent = 0
        self._state.active_session_id = None
        self._integral_term = 0.0
        self._last_alert = None
        return self._state

    def apply_sdk_imaging_settings(self) -> None:
        if not self._state.connected:
            return
        with self._lock:
            self._adapter.set_readout_speed(settings.camera_index, int(settings.sdk_readout_speed))
            self._adapter.set_sensor_output_mode(settings.camera_index, int(settings.sdk_sensor_output_mode))

    def capabilities(self) -> dict:
        if not self._state.connected or self._state.capabilities is None:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        return asdict(self._state.capabilities)

    @staticmethod
    def _validate_roi_geometry(
        sensor_width: int,
        sensor_height: int,
        bin_x: int,
        bin_y: int,
        num_x: int,
        num_y: int,
        start_x: int,
        start_y: int,
    ) -> None:
        if start_x < 0 or start_y < 0:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="start_x/start_y must be >= 0")
        if num_x <= 0 or num_y <= 0:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="num_x/num_y must be > 0")
        max_start_x = (sensor_width // bin_x) - 1
        max_start_y = (sensor_height // bin_y) - 1
        if start_x > max_start_x or start_y > max_start_y:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="start_x/start_y exceed binned sensor bounds")
        roi_sensor_width = num_x * bin_x
        roi_sensor_height = num_y * bin_y
        if roi_sensor_width <= 0 or roi_sensor_height <= 0:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="ROI geometry must be positive")
        sensor_start_x = start_x * bin_x
        sensor_start_y = start_y * bin_y
        if sensor_start_x + roi_sensor_width > sensor_width or sensor_start_y + roi_sensor_height > sensor_height:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="ROI exceeds sensor bounds")

    @classmethod
    def _crop_and_bin_frame_bytes(
        cls,
        frame_bytes: bytes,
        frame_width: int,
        frame_height: int,
        *,
        bin_x: int,
        bin_y: int,
        num_x: int,
        num_y: int,
        start_x: int,
        start_y: int,
    ) -> tuple[int, int, bytes]:
        cls._validate_roi_geometry(frame_width, frame_height, bin_x, bin_y, num_x, num_y, start_x, start_y)
        expected_bytes = frame_width * frame_height * 2
        if len(frame_bytes) < expected_bytes:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="frame payload is smaller than expected")

        pixels = cls._decode_u16_le(frame_bytes[:expected_bytes])
        sensor_start_x = start_x * bin_x
        sensor_start_y = start_y * bin_y
        roi_sensor_width = num_x * bin_x
        roi_sensor_height = num_y * bin_y
        roi_pixels = [0] * (roi_sensor_width * roi_sensor_height)

        for y in range(roi_sensor_height):
            src_offset = (sensor_start_y + y) * frame_width + sensor_start_x
            dst_offset = y * roi_sensor_width
            roi_pixels[dst_offset : dst_offset + roi_sensor_width] = pixels[src_offset : src_offset + roi_sensor_width]

        if bin_x == 1 and bin_y == 1:
            return num_x, num_y, cls._encode_u16_le(roi_pixels)

        binned_pixels = [0] * (num_x * num_y)
        for out_y in range(num_y):
            src_y = out_y * bin_y
            for out_x in range(num_x):
                src_x = out_x * bin_x
                total = 0
                for by in range(bin_y):
                    row_offset = (src_y + by) * roi_sensor_width + src_x
                    total += sum(roi_pixels[row_offset : row_offset + bin_x])
                binned_pixels[out_y * num_x + out_x] = min(65535, total)

        return num_x, num_y, cls._encode_u16_le(binned_pixels)

    def set_roi_binning(self, bin_x: int, bin_y: int, num_x: int, num_y: int, start_x: int, start_y: int) -> None:
        caps = self._state.capabilities
        if not self._state.connected or caps is None:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        if bin_x < 1 or bin_x > caps.max_binx:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message=f"bin_x out of range 1..{caps.max_binx}")
        if bin_y < 1 or bin_y > caps.max_biny:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message=f"bin_y out of range 1..{caps.max_biny}")
        self._validate_roi_geometry(caps.camera_x_size, caps.camera_y_size, bin_x, bin_y, num_x, num_y, start_x, start_y)

        self._state.bin_x = bin_x
        self._state.bin_y = bin_y
        self._state.num_x = num_x
        self._state.num_y = num_y
        self._state.start_x = start_x
        self._state.start_y = start_y

    def start_exposure(self, duration_sec: float, light: bool) -> ExposureJob:
        if not self._state.connected:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        if duration_sec <= 0:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="duration_sec must be > 0")

        with self._lock:
            exposure_id = str(uuid.uuid4())
            self._adapter.start_exposure(settings.camera_index, duration_sec, light)
            job = ExposureJob(
                exposure_id=exposure_id,
                duration_sec=duration_sec,
                light=light,
                state="exposing",
                image_ready=False,
                bin_x=self._state.bin_x,
                bin_y=self._state.bin_y,
                num_x=self._state.num_x,
                num_y=self._state.num_y,
                start_x=self._state.start_x,
                start_y=self._state.start_y,
            )
            self._exposures[exposure_id] = job
            self._state.active_exposure_id = exposure_id
            self._state.camera_state = "exposing"
            self._state.image_ready = False
            thread = threading.Thread(target=self._monitor_exposure, args=(exposure_id,), daemon=True)
            thread.start()
            return job

    @staticmethod
    def _first_pixels(frame_bytes: bytes, max_count: int = 8) -> list[int]:
        count = min(max_count, len(frame_bytes) // 2)
        return [int.from_bytes(frame_bytes[i * 2 : i * 2 + 2], "little", signed=False) for i in range(count)]

    def _monitor_exposure(self, exposure_id: str) -> None:
        job = self._exposures.get(exposure_id)
        duration_sec = job.duration_sec if job else 0.5
        started_at = time.monotonic()
        deadline = time.monotonic() + max(5.0, duration_sec + 10.0)
        while self._adapter.is_exposure_busy(settings.camera_index):
            if time.monotonic() >= deadline:
                with self._lock:
                    timeout_job = self._exposures.get(exposure_id)
                    if timeout_job and timeout_job.state == "exposing":
                        timeout_job.state = "error"
                        timeout_job.error = "exposure timeout waiting for DllIsBusy=false"
                        self._state.camera_state = "error"
                        self._state.image_ready = False
                        self._state.active_exposure_id = None
                try:
                    self._adapter.stop_exposure(settings.camera_index)
                except SdkError:
                    pass
                return
            time.sleep(0.05)
            if job and duration_sec > 0:
                elapsed = max(0.0, time.monotonic() - started_at)
                progress = int(min(95.0, (elapsed / max(duration_sec, 0.1)) * 100.0))
                with self._lock:
                    running_job = self._exposures.get(exposure_id)
                    if running_job and running_job.state == "exposing":
                        running_job.percent = max(running_job.percent, progress)

        with self._lock:
            job = self._exposures.get(exposure_id)
            if job is None or job.state in {"aborted", "stopped"}:
                return
            try:
                bin_x = job.bin_x
                bin_y = job.bin_y
                num_x = job.num_x
                num_y = job.num_y
                start_x = job.start_x
                start_y = job.start_y

                # Native SDK path still reads a full-frame payload because
                # smaller buffers can trigger vendor DLL overruns/access violations.
                # Apply ROI/binning in managed code before exposing ImageArray.
                if settings.sdk_mode == "native" and self._state.capabilities is not None:
                    raw_width = self._state.capabilities.camera_x_size
                    raw_height = self._state.capabilities.camera_y_size
                    frame_bytes = self._adapter.read_measurement_data(settings.camera_index, raw_width, raw_height)
                    width, height, frame_bytes = self._crop_and_bin_frame_bytes(
                        frame_bytes,
                        raw_width,
                        raw_height,
                        bin_x=bin_x,
                        bin_y=bin_y,
                        num_x=num_x,
                        num_y=num_y,
                        start_x=start_x,
                        start_y=start_y,
                    )
                else:
                    width = num_x
                    height = num_y
                    frame_bytes = self._adapter.read_measurement_data(settings.camera_index, width, height)
                job.state = "completed"
                job.image_ready = True
                job.percent = 100
                self._state.camera_state = "idle"
                self._state.image_ready = True
                self._latest_frame_bytes = frame_bytes
                self._latest_image = {
                    "exposure_id": exposure_id,
                    "width": width,
                    "height": height,
                    "pixel_type": "uint16",
                    "orientation": "top_left_origin",
                    "bin_x": bin_x,
                    "bin_y": bin_y,
                    "sample_pixels": self._first_pixels(frame_bytes),
                    "pixel_data_base64": base64.b64encode(frame_bytes).decode("ascii"),
                }
            except Exception as exc:
                job.state = "error"
                job.error = str(exc)
                job.percent = 100
                self._state.camera_state = "error"
                self._state.image_ready = False

    def exposure_status(self, exposure_id: str) -> ExposureJob:
        job = self._exposures.get(exposure_id)
        if not job:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="exposure not found")
        return job

    def abort_exposure(self, exposure_id: str) -> ExposureJob:
        with self._lock:
            job = self.exposure_status(exposure_id)
            try:
                self._adapter.stop_exposure(settings.camera_index)
            except SdkError:
                # Exposure may already be completed in SDK by the time abort is requested.
                pass
            job.state = "aborted"
            job.image_ready = False
            job.percent = 100
            self._state.camera_state = "idle"
            self._state.image_ready = False
            self._state.active_exposure_id = None
            return job

    def stop_exposure(self, exposure_id: str) -> ExposureJob:
        with self._lock:
            job = self.exposure_status(exposure_id)
            try:
                self._adapter.stop_exposure(settings.camera_index)
            except SdkError:
                # Exposure may already be completed in SDK by the time stop is requested.
                pass
            job.state = "stopped"
            job.image_ready = False
            job.percent = 100
            self._state.camera_state = "idle"
            self._state.image_ready = False
            self._state.active_exposure_id = None
            return job

    def latest_image(self) -> dict:
        if not self._latest_image:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="no image available")
        return self._latest_image

    def latest_image_bytes(self) -> tuple[dict, bytes]:
        if not self._latest_image or self._latest_frame_bytes is None:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="no image available")
        return self._latest_image, self._latest_frame_bytes

    def latest_image_metadata(self) -> dict:
        if not self._latest_image:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="no image available")
        return {
            "exposure_id": str(self._latest_image.get("exposure_id", "")),
            "width": int(self._latest_image.get("width", 0)),
            "height": int(self._latest_image.get("height", 0)),
            "pixel_type": str(self._latest_image.get("pixel_type", "uint16")),
            "orientation": str(self._latest_image.get("orientation", "top_left_origin")),
            "bin_x": int(self._latest_image.get("bin_x", self._state.bin_x)),
            "bin_y": int(self._latest_image.get("bin_y", self._state.bin_y)),
            "sample_pixels": list(self._latest_image.get("sample_pixels", [])),
            "ccd_temp_c": int(self._state.ccd_temp_c),
            "target_temp_c": int(self._state.target_temp_c),
            "readout_speed": int(settings.sdk_readout_speed),
            "gain_mode": "unknown",
        }

    @staticmethod
    def _decode_u16_le(frame_bytes: bytes) -> list[int]:
        count = len(frame_bytes) // 2
        if count <= 0:
            return []
        return list(struct.unpack("<" + "H" * count, frame_bytes))

    @staticmethod
    def _encode_u16_le(values: list[int]) -> bytes:
        if not values:
            return b""
        return struct.pack("<" + "H" * len(values), *[max(0, min(65535, int(v))) for v in values])

    @staticmethod
    def _resize_nearest_u16(src: list[int], src_w: int, src_h: int, dst_w: int, dst_h: int) -> list[int]:
        if src_w <= 0 or src_h <= 0 or dst_w <= 0 or dst_h <= 0:
            return []
        out = [0] * (dst_w * dst_h)
        for y in range(dst_h):
            sy = min(src_h - 1, int((y * src_h) / dst_h))
            row_src = sy * src_w
            row_dst = y * dst_w
            for x in range(dst_w):
                sx = min(src_w - 1, int((x * src_w) / dst_w))
                out[row_dst + x] = src[row_src + sx]
        return out

    def resize_latest_image(self, width: int, height: int) -> dict:
        meta, frame_bytes = self.latest_image_bytes()
        src_w = int(meta.get("width", 0))
        src_h = int(meta.get("height", 0))
        pixels = self._decode_u16_le(frame_bytes)
        resized = self._resize_nearest_u16(pixels, src_w, src_h, width, height)
        resized_bytes = self._encode_u16_le(resized)
        return {
            "exposure_id": str(meta.get("exposure_id", "")),
            "width": width,
            "height": height,
            "pixel_type": "uint16",
            "orientation": str(meta.get("orientation", "top_left_origin")),
            "bin_x": int(meta.get("bin_x", 1)),
            "bin_y": int(meta.get("bin_y", 1)),
            "sample_pixels": self._first_pixels(resized_bytes),
            "pixel_data_base64": base64.b64encode(resized_bytes).decode("ascii"),
        }

    @staticmethod
    def _fits_card(key: str, value: str) -> bytes:
        text = f"{key:<8}= {value}"
        return text[:80].ljust(80).encode("ascii")

    def _build_fits_header(self, width: int, height: int, exposure_id: str, bitpix: int) -> bytes:
        # Camera buffer is uint16 ADU; 16 = classic FITS int16 + BZERO 32768; 32 = widened int32 BE.
        if bitpix == 16:
            cards = [
                self._fits_card("SIMPLE", "T"),
                self._fits_card("BITPIX", "16"),
                self._fits_card("NAXIS", "2"),
                self._fits_card("NAXIS1", str(width)),
                self._fits_card("NAXIS2", str(height)),
                self._fits_card("BZERO", "32768"),
                self._fits_card("BSCALE", "1"),
                self._fits_card("BUNIT", "'ADU'"),
                self._fits_card("CAMBITS", "16"),
                self._fits_card("EXPID", f"'{exposure_id[:60]}'"),
                self._fits_card("CCDTEMP", str(int(self._state.ccd_temp_c))),
                self._fits_card("TARGTEMP", str(int(self._state.target_temp_c))),
                self._fits_card("READSPD", str(int(settings.sdk_readout_speed))),
                self._fits_card("END", ""),
            ]
        else:
            cards = [
                self._fits_card("SIMPLE", "T"),
                self._fits_card("BITPIX", "32"),
                self._fits_card("NAXIS", "2"),
                self._fits_card("NAXIS1", str(width)),
                self._fits_card("NAXIS2", str(height)),
                self._fits_card("BZERO", "0"),
                self._fits_card("BSCALE", "1"),
                self._fits_card("BUNIT", "'ADU'"),
                self._fits_card("CAMBITS", "16"),
                self._fits_card("EXPID", f"'{exposure_id[:60]}'"),
                self._fits_card("CCDTEMP", str(int(self._state.ccd_temp_c))),
                self._fits_card("TARGTEMP", str(int(self._state.target_temp_c))),
                self._fits_card("READSPD", str(int(settings.sdk_readout_speed))),
                self._fits_card("END", ""),
            ]
        header = b"".join(cards)
        pad = (2880 - (len(header) % 2880)) % 2880
        return header + (b" " * pad)

    @staticmethod
    def _u16le_to_fits_i16be(frame_bytes: bytes) -> bytes:
        values = CameraRuntime._decode_u16_le(frame_bytes)
        signed_vals = [int(v) - 32768 for v in values]
        if not signed_vals:
            return b""
        data = struct.pack(">" + "h" * len(signed_vals), *signed_vals)
        pad = (2880 - (len(data) % 2880)) % 2880
        return data + (b"\0" * pad)

    @staticmethod
    def _u16le_to_fits_i32be(frame_bytes: bytes) -> bytes:
        """FITS BITPIX=32: big-endian signed int32 per pixel; uint16 ADU 0..65535 unchanged."""
        n = len(frame_bytes) // 2
        if n <= 0:
            return b""
        values = struct.unpack("<" + "H" * n, frame_bytes)
        data = struct.pack(">" + "i" * n, *[int(v) for v in values])
        pad = (2880 - (len(data) % 2880)) % 2880
        return data + (b"\0" * pad)

    def export_latest_image_fits(self, filename: str | None = None) -> dict:
        meta, frame_bytes = self.latest_image_bytes()
        width = int(meta.get("width", 0))
        height = int(meta.get("height", 0))
        exposure_id = str(meta.get("exposure_id", ""))
        safe_name = (filename or f"exposure_{exposure_id}.fits").strip()
        if not safe_name.lower().endswith(".fits"):
            safe_name += ".fits"
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        target = self._exports_dir / safe_name
        # Avoid accidental overwrite in long sessions.
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            target = self._exports_dir / f"{target.stem}_{stamp}{target.suffix}"
        stored = storage_service.get_settings()
        bitpix = int(stored.get("fits_export_bitpix", settings.fits_export_bitpix))
        if bitpix not in (16, 32):
            bitpix = 32
        header = self._build_fits_header(width=width, height=height, exposure_id=exposure_id, bitpix=bitpix)
        data = self._u16le_to_fits_i16be(frame_bytes) if bitpix == 16 else self._u16le_to_fits_i32be(frame_bytes)
        target.write_bytes(header + data)
        return {
            "file_name": target.name,
            "file_path": str(target),
            "bytes_written": int(target.stat().st_size),
            "exposure_id": exposure_id,
            "width": width,
            "height": height,
            "fits_bitpix": bitpix,
            "sensor_bit_depth": 16,
        }

    def set_active_session_id(self, session_id: str | None) -> None:
        self._state.active_session_id = session_id

    def set_cooler_power(self, cooler_on: bool, cooler_power_percent: int | None = None) -> dict:
        if not self._state.connected:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        if not cooler_on:
            with self._lock:
                try:
                    ccd_live, _ = self._adapter.get_temperatures(settings.camera_index)
                    self._state.ccd_temp_c = ccd_live
                except SdkError:
                    pass
                try:
                    self._adapter.switch_off_cooling(settings.camera_index)
                except SdkError as exc:
                    # Some SDK builds report "camera busy" while cooler is transitioning.
                    # Keep API idempotent for client software and proceed with local state off.
                    if "camera busy" not in str(exc).lower():
                        raise
                self._state.cooler_on = False
                self._state.cooler_power_percent = 0
                # Preserve the operator's setpoint even when cooling is toggled off.
                # MaxIm DL / ASCOM clients may briefly clear CoolerOn while still
                # expecting SetCCDTemperature to remain the authoritative target.
                self._integral_term = 0.0
                self._last_applied_target_temp = None
            self._log_cooling_state("cooler_off")
            return {
                "cooler_on": False,
                "target_temp_c": self._state.target_temp_c,
                "ccd_temp_c": self._state.ccd_temp_c,
                "backside_temp_c": max(self._state.ccd_temp_c + 12, 20),
                "cooler_power_percent": 0,
            }

        with self._lock:
            self._state.cooler_on = True
            # Starting cooling must follow the operator target immediately, not
            # a stale ambient/off-state control target.
            self._control_target_temp_c = float(self._requested_target_temp_c)
            if cooler_power_percent is not None:
                self._state.cooler_power_percent = max(0, min(100, cooler_power_percent))
                # Seed integral so the PI starts near the operator's requested power.
                self._integral_term = float(self._state.cooler_power_percent)
            else:
                self._integral_term = 0.0
                if self._state.cooler_power_percent == 0:
                    self._state.cooler_power_percent = 50

            # Send stored target to SDK immediately so cooling starts without
            # waiting for the 1-second control loop tick.
            apply_temp = int(round(self._requested_target_temp_c))
            try:
                self._adapter.set_target_temperature(settings.camera_index, apply_temp)
                self._last_applied_target_temp = apply_temp
                self._last_control_apply_at = time.monotonic()
            except SdkError as exc:
                if not self._retry_apply_target_with_fallback(exc):
                    self._last_alert = f"cooler_on_apply_failed:{exc}"
        self._log_cooling_state("cooler_on", requested_power=cooler_power_percent, sdk_target=apply_temp)
        return self.cooling_status()

    def set_target_temperature(self, target_temp_c: int) -> dict:
        if not self._state.connected:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        with self._lock:
            prev_requested = self._requested_target_temp_c
            prev_control = self._control_target_temp_c
            prev_state_target = self._state.target_temp_c

            # Store target regardless of cooler state -- ASCOM clients may set
            # SetCCDTemperature before enabling CoolerOn.
            self._requested_target_temp_c = float(target_temp_c)
            self._state.target_temp_c = int(target_temp_c)
            # Snap control target so the ramp loop does NOT send old values to SDK.
            self._control_target_temp_c = float(target_temp_c)
            self._integral_term = 0.0

            sdk_sent = False
            if self._state.cooler_on:
                apply_temp = int(target_temp_c)
                self._adapter.set_target_temperature(settings.camera_index, apply_temp)
                self._last_applied_target_temp = apply_temp
                self._last_control_apply_at = time.monotonic()
                sdk_sent = True

            self._log_cooling_state(
                "set_target",
                op_target=target_temp_c,
                sdk_sent=sdk_sent,
                prev_state_target=prev_state_target,
                prev_requested=prev_requested,
                prev_control=round(prev_control, 3),
            )
        return self.cooling_status()

    def cooling_status(self) -> dict:
        if self._state.connected:
            try:
                ccd_temp, backside_temp = self._adapter.get_temperatures(settings.camera_index)
                self._state.ccd_temp_c = ccd_temp
                return {
                    "cooler_on": self._state.cooler_on,
                    "target_temp_c": self._state.target_temp_c,
                    "ccd_temp_c": ccd_temp,
                    "backside_temp_c": backside_temp,
                    "cooler_power_percent": self._state.cooler_power_percent,
                }
            except SdkError:
                # Keep status endpoint stable for ASCOM clients even if SDK
                # transiently reports busy for temperature polling.
                return {
                    "cooler_on": self._state.cooler_on,
                    "target_temp_c": self._state.target_temp_c,
                    "ccd_temp_c": self._state.ccd_temp_c,
                    "backside_temp_c": max(self._state.ccd_temp_c + 12, 20),
                    "cooler_power_percent": self._state.cooler_power_percent,
                }
        return {
            "cooler_on": False,
            "target_temp_c": self._state.target_temp_c,
            "ccd_temp_c": self._state.ccd_temp_c,
            "backside_temp_c": max(self._state.ccd_temp_c + 12, 20),
            "cooler_power_percent": 0,
        }

    def cooling_debug(self) -> dict:
        """Snapshot of every cooling-related variable for diagnostic purposes."""
        with self._lock:
            return {
                "runtime_version": RUNTIME_VERSION,
                "state.target_temp_c": self._state.target_temp_c,
                "state.ccd_temp_c": self._state.ccd_temp_c,
                "state.cooler_on": self._state.cooler_on,
                "state.cooler_power_percent": self._state.cooler_power_percent,
                "requested_target_temp_c": round(self._requested_target_temp_c, 4),
                "control_target_temp_c": round(self._control_target_temp_c, 4),
                "integral_term": round(self._integral_term, 4),
                "last_applied_target_temp": self._last_applied_target_temp,
                "controller_mode": self._controller_mode,
                "running_warmup": self._has_running_warmup(),
            }

    def start_warmup(self, target_temp_c: int, temp_step_c: int, power_step_percent: int, step_interval_sec: float) -> WarmupJob:
        if not self._state.connected:
            raise SdkError(code=SdkErrorCode.NOT_CONNECTED, message="camera is not connected")
        with self._lock:
            warmup_id = str(uuid.uuid4())
            job = WarmupJob(
                warmup_job_id=warmup_id,
                state="running",
                target_temp_c=target_temp_c,
                temp_step_c=max(1, temp_step_c),
                power_step_percent=max(1, power_step_percent),
                step_interval_sec=max(0.1, step_interval_sec),
                current_temp_c=self._state.ccd_temp_c,
                current_power_percent=self._state.cooler_power_percent,
                previous_controller_mode=self._controller_mode,
            )
            self._warmups[warmup_id] = job
            self._state.cooler_on = True
            self._controller_mode = "safe"
            logger.info(
                "cooling warmup start id=%s final_target=%s step_c=%s power_step=%s interval=%s",
                warmup_id,
                job.target_temp_c,
                job.temp_step_c,
                job.power_step_percent,
                job.step_interval_sec,
            )
            thread = threading.Thread(target=self._run_warmup, args=(warmup_id,), daemon=True)
            thread.start()
            return job

    def _run_warmup(self, warmup_id: str) -> None:
        try:
            while True:
                with self._lock:
                    job = self._warmups.get(warmup_id)
                    if not job or job.state != "running":
                        return

                    next_target = min(job.target_temp_c, self._state.target_temp_c + job.temp_step_c)
                    try:
                        self._adapter.set_target_temperature(settings.camera_index, next_target)
                    except SdkError as exc:
                        match = re.search(r"out of range\s+(-?\d+)\.\.(-?\d+)", str(exc))
                        if match is None:
                            job.state = "error"
                            job.error = str(exc)
                            logger.exception("cooling warmup failed id=%s", warmup_id)
                            return
                        low = int(match.group(1))
                        high = int(match.group(2))
                        clamped = int(max(low, min(high, next_target)))
                        self._adapter.set_target_temperature(settings.camera_index, clamped)
                        # If requested warm-up endpoint is outside SDK range,
                        # run warm-up to the nearest valid endpoint.
                        if job.target_temp_c > high:
                            job.target_temp_c = high
                        elif job.target_temp_c < low:
                            job.target_temp_c = low
                        next_target = clamped
                        job.error = f"clamped_to_sdk_range:{low}..{high}"
                        logger.warning(
                            "cooling warmup clamp id=%s requested_target=%s clamped_target=%s range=%s..%s",
                            warmup_id,
                            job.target_temp_c,
                            next_target,
                            low,
                            high,
                        )

                    self._state.target_temp_c = next_target
                    logger.info(
                        "cooling warmup step id=%s next_target=%s job_final=%s ccd=%s power%%=%s",
                        warmup_id,
                        next_target,
                        job.target_temp_c,
                        self._state.ccd_temp_c,
                        self._state.cooler_power_percent,
                    )
                    self._requested_target_temp_c = float(next_target)
                    self._control_target_temp_c = float(next_target)

                    if self._state.cooler_power_percent > 0:
                        self._state.cooler_power_percent = max(0, self._state.cooler_power_percent - job.power_step_percent)

                    ccd_temp, _ = self._adapter.get_temperatures(settings.camera_index)
                    self._state.ccd_temp_c = ccd_temp
                    job.current_temp_c = ccd_temp
                    job.current_power_percent = self._state.cooler_power_percent

                    if self._state.ccd_temp_c >= job.target_temp_c and self._state.cooler_power_percent == 0:
                        # Warm-up completed: switch from open-loop warm-up steps
                        # to closed-loop regulation at the final target.
                        self._state.cooler_on = True
                        self._state.target_temp_c = job.target_temp_c
                        self._requested_target_temp_c = float(job.target_temp_c)
                        self._control_target_temp_c = float(job.target_temp_c)
                        self._integral_term = 0.0
                        self._last_applied_target_temp = int(job.target_temp_c)
                        self._last_control_apply_at = time.monotonic()
                        self._controller_mode = job.previous_controller_mode
                        job.state = "completed"
                        logger.info(
                            "cooling warmup completed id=%s hold_target=%s restore_mode=%s",
                            warmup_id,
                            job.target_temp_c,
                            self._controller_mode,
                        )
                        return
                time.sleep(self._warmups[warmup_id].step_interval_sec)
        except Exception as exc:
            with self._lock:
                job = self._warmups.get(warmup_id)
                if job and job.state == "running":
                    job.state = "error"
                    job.error = str(exc)
            logger.exception("cooling warmup unhandled failure id=%s", warmup_id)

    def warmup_status(self, warmup_id: str) -> WarmupJob:
        job = self._warmups.get(warmup_id)
        if not job:
            raise SdkError(code=SdkErrorCode.INVALID_STATUS, message="warmup job not found")
        return job


camera_runtime = CameraRuntime()
