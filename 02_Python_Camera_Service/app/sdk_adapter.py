from __future__ import annotations

import ctypes
import logging
import os
import re
import threading
import time
from ctypes import POINTER, byref, c_bool, c_char_p, c_int, c_ushort
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.config import settings

logger = logging.getLogger("camera-service.sdk")


class SdkErrorCode(str, Enum):
    NOT_CONNECTED = "NOT_CONNECTED"
    DLL_LOAD_FAILED = "DLL_LOAD_FAILED"
    SDK_CALL_FAILED = "SDK_CALL_FAILED"
    INVALID_STATUS = "INVALID_STATUS"


class SdkError(Exception):
    def __init__(self, code: SdkErrorCode, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


STATUS_MESSAGES: dict[int, str] = {
    0: "camera detected and ok",
    1: "no camera detected",
    2: "could not open USB device",
    3: "write config table failed",
    4: "write read request failed",
    5: "no trigger signal",
    6: "new camera detected",
    7: "unknown camera id",
    8: "parameter out of range",
    9: "no new data",
    10: "camera busy",
    11: "cooling turned off",
    12: "measurement stopped",
    13: "burst mode too much pixels",
    14: "timing table not found",
    15: "not critical",
    16: "illegal binning/crop combination",
}


@dataclass
class CameraInfo:
    model_id: int
    model_name: str


@dataclass
class CameraCapabilities:
    camera_x_size: int
    camera_y_size: int
    pixel_size_um: int
    max_binx: int
    max_biny: int
    has_shutter: bool
    sensor_name: str


class BaseSdkAdapter:
    def connect(self, camera_index: int) -> CameraInfo:
        raise NotImplementedError

    def disconnect(self, camera_index: int) -> None:
        raise NotImplementedError

    def capabilities(self, camera_index: int, has_shutter: bool) -> CameraCapabilities:
        raise NotImplementedError

    def start_exposure(self, camera_index: int, duration_sec: float, light: bool) -> None:
        raise NotImplementedError

    def is_exposure_busy(self, camera_index: int) -> bool:
        raise NotImplementedError

    def read_measurement_data(self, camera_index: int, width: int, height: int) -> bytes:
        raise NotImplementedError

    def stop_exposure(self, camera_index: int) -> None:
        raise NotImplementedError

    def get_temperatures(self, camera_index: int) -> tuple[int, int]:
        raise NotImplementedError

    def set_target_temperature(self, camera_index: int, target_temp_c: int) -> None:
        raise NotImplementedError

    def switch_off_cooling(self, camera_index: int) -> None:
        raise NotImplementedError


    def set_readout_speed(self, camera_index: int, speed_khz: int) -> None:
        raise NotImplementedError

    def set_sensor_output_mode(self, camera_index: int, mode: int) -> None:
        raise NotImplementedError


class MockGreatEyesSdkAdapter(BaseSdkAdapter):
    def __init__(self) -> None:
        self._connected = False
        self._model_id = 9000
        self._model_name = "GreatEyes 9.0 (Mock)"
        self._exp_end_ts = 0.0
        self._ccd_temp_c = 20
        self._backside_temp_c = 32
        self._target_temp_c = 20
        self._cooling_enabled = False
        self._readout_speed_khz = 1000
        self._sensor_output_mode = 0

    def connect(self, camera_index: int) -> CameraInfo:
        self._connected = True
        return CameraInfo(model_id=self._model_id, model_name=self._model_name)

    def disconnect(self, camera_index: int) -> None:
        self._connected = False

    def capabilities(self, camera_index: int, has_shutter: bool) -> CameraCapabilities:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        return CameraCapabilities(
            camera_x_size=2048,
            camera_y_size=2052,
            pixel_size_um=13,
            max_binx=4,
            max_biny=4,
            has_shutter=has_shutter,
            sensor_name="GreatEyes 9.0",
        )

    def start_exposure(self, camera_index: int, duration_sec: float, light: bool) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._exp_end_ts = time.monotonic() + max(0.05, duration_sec)

    def is_exposure_busy(self, camera_index: int) -> bool:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        return time.monotonic() < self._exp_end_ts

    def read_measurement_data(self, camera_index: int, width: int, height: int) -> bytes:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        pixel_count = max(1, width * height)
        return b"\x00\x00" * pixel_count

    def stop_exposure(self, camera_index: int) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._exp_end_ts = 0.0

    def get_temperatures(self, camera_index: int) -> tuple[int, int]:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        if self._cooling_enabled:
            if self._ccd_temp_c > self._target_temp_c:
                self._ccd_temp_c -= 1
            elif self._ccd_temp_c < self._target_temp_c:
                self._ccd_temp_c += 1
        else:
            self._ccd_temp_c = min(20, self._ccd_temp_c + 1)
        self._backside_temp_c = max(20, self._ccd_temp_c + 12)
        return self._ccd_temp_c, self._backside_temp_c

    def set_target_temperature(self, camera_index: int, target_temp_c: int) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._target_temp_c = target_temp_c
        self._cooling_enabled = True

    def switch_off_cooling(self, camera_index: int) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._cooling_enabled = False
        self._target_temp_c = self._ccd_temp_c

    def set_readout_speed(self, camera_index: int, speed_khz: int) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._readout_speed_khz = speed_khz

    def set_sensor_output_mode(self, camera_index: int, mode: int) -> None:
        if not self._connected:
            raise SdkError(SdkErrorCode.NOT_CONNECTED, "camera is not connected")
        self._sensor_output_mode = mode


class NativeGreatEyesSdkAdapter(BaseSdkAdapter):
    def __init__(self, dll_path: str) -> None:
        if not dll_path:
            raise SdkError(SdkErrorCode.DLL_LOAD_FAILED, "SDK_DLL_PATH is empty")
        self._dll_path = dll_path
        try:
            self.lib = ctypes.CDLL(dll_path)
        except OSError as exc:
            raise SdkError(SdkErrorCode.DLL_LOAD_FAILED, f"failed to load DLL: {exc}") from exc
        logger.info("SDK loaded dll_path=%s", dll_path)

        self.lib.ConnectCamera.argtypes = [POINTER(c_int), POINTER(c_char_p), POINTER(c_int), c_int]
        self.lib.ConnectCamera.restype = c_bool

        self.lib.DisconnectCamera.argtypes = [POINTER(c_int), c_int]
        self.lib.DisconnectCamera.restype = c_bool

        self.lib.InitCamera.argtypes = [POINTER(c_int), c_int]
        self.lib.InitCamera.restype = c_bool

        self.lib.SetupCameraInterface.argtypes = [c_int, c_char_p, POINTER(c_int), c_int]
        self.lib.SetupCameraInterface.restype = c_bool

        self.lib.ConnectToSingleCameraServer.argtypes = [c_int]
        self.lib.ConnectToSingleCameraServer.restype = c_bool

        self.lib.ConnectToMultiCameraServer.argtypes = []
        self.lib.ConnectToMultiCameraServer.restype = c_bool

        self.lib.DisconnectCameraServer.argtypes = [c_int]
        self.lib.DisconnectCameraServer.restype = c_bool

        self._has_legacy_set_connection_type = hasattr(self.lib, "SetConnectionType")
        if self._has_legacy_set_connection_type:
            self.lib.SetConnectionType.argtypes = [c_int, c_char_p, POINTER(c_int)]
            self.lib.SetConnectionType.restype = c_bool

        self._has_legacy_connect_to_server = hasattr(self.lib, "ConnectToCameraServer")
        if self._has_legacy_connect_to_server:
            self.lib.ConnectToCameraServer.argtypes = []
            self.lib.ConnectToCameraServer.restype = c_bool

        self.lib.GetNumberOfConnectedCams.argtypes = []
        self.lib.GetNumberOfConnectedCams.restype = c_int

        self.lib.SetReadOutSpeed.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.SetReadOutSpeed.restype = c_bool

        self.lib.SetupSensorOutputMode.argtypes = [c_int, c_int]
        self.lib.SetupSensorOutputMode.restype = c_bool

        self.lib.SetBitDepth.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.SetBitDepth.restype = c_bool

        self.lib.SetBusyTimeout.argtypes = [c_int]
        self.lib.SetBusyTimeout.restype = c_bool

        self.lib.GetImageSize.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(c_int), c_int]
        self.lib.GetImageSize.restype = c_bool

        self.lib.GetSizeOfPixel.argtypes = [c_int]
        self.lib.GetSizeOfPixel.restype = c_int

        self.lib.GetMaxBinningX.argtypes = [POINTER(c_int), c_int]
        self.lib.GetMaxBinningX.restype = c_int

        self.lib.GetMaxBinningY.argtypes = [POINTER(c_int), c_int]
        self.lib.GetMaxBinningY.restype = c_int

        self.lib.SetExposure.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.SetExposure.restype = c_bool

        self._use_dyn_bitdepth_api = hasattr(self.lib, "StartMeasurement_DynBitDepth") and hasattr(
            self.lib, "GetMeasurementData_DynBitDepth"
        )
        if self._use_dyn_bitdepth_api:
            self.lib.StartMeasurement_DynBitDepth.argtypes = [c_bool, c_bool, c_bool, c_bool, POINTER(c_int), c_int]
            self.lib.StartMeasurement_DynBitDepth.restype = c_bool
            self.lib.GetMeasurementData_DynBitDepth.argtypes = [ctypes.c_void_p, POINTER(c_int), c_int]
            self.lib.GetMeasurementData_DynBitDepth.restype = c_bool

        self.lib.StartMeasurement.argtypes = [c_bool, c_bool, c_bool, c_bool, c_int, POINTER(c_int), c_int]
        self.lib.StartMeasurement.restype = c_bool

        self.lib.DllIsBusy.argtypes = [c_int]
        self.lib.DllIsBusy.restype = c_bool

        self.lib.GetMeasurementData.argtypes = [POINTER(c_ushort), POINTER(c_int), POINTER(c_int), POINTER(c_int), c_int]
        self.lib.GetMeasurementData.restype = c_bool

        self.lib.StopMeasurement.argtypes = [c_int]
        self.lib.StopMeasurement.restype = c_bool

        self.lib.TemperatureControl_Init.argtypes = [c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), c_int]
        self.lib.TemperatureControl_Init.restype = c_int

        self.lib.TemperatureControl_Setup.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.TemperatureControl_Setup.restype = c_int

        self.lib.TemperatureControl_SetTemperatureLevel.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.TemperatureControl_SetTemperatureLevel.restype = c_bool

        self.lib.TemperatureControl_GetTemperature.argtypes = [c_int, POINTER(c_int), POINTER(c_int), c_int]
        self.lib.TemperatureControl_GetTemperature.restype = c_bool

        self.lib.TemperatureControl_SetTemperature.argtypes = [c_int, POINTER(c_int), c_int]
        self.lib.TemperatureControl_SetTemperature.restype = c_bool

        self.lib.TemperatureControl_SwitchOff.argtypes = [POINTER(c_int), c_int]
        self.lib.TemperatureControl_SwitchOff.restype = c_bool

        self._cooling_initialized = False
        self._server_connected = False
        self._cooling_min_temp: int | None = None
        self._cooling_max_temp: int | None = None
        self._cooling_levels: int = 0
        self._sdk_lock = threading.RLock()

    def _candidate_ini_paths(self) -> list[Path]:
        dll_ini = Path(self._dll_path).with_name("greateyes.ini")
        program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "greateyes" / "2" / "greateyes.ini"
        # Keep deterministic order, skip duplicates.
        unique: list[Path] = []
        for path in (dll_ini, program_data):
            if path not in unique:
                unique.append(path)
        return unique

    @staticmethod
    def _replace_or_add_key(block: str, key: str, value: str, newline: str) -> str:
        key_pattern = re.compile(rf"(?im)^{re.escape(key)}=.*$")
        if key_pattern.search(block):
            return key_pattern.sub(f"{key}={value}", block, count=1)
        return f"{block}{newline}{key}={value}"

    def _sync_network_profile_to_ini(self, camera_index: int) -> None:
        has_address = bool(settings.sdk_camera_address.strip())
        has_interface = settings.sdk_camera_interface >= 0
        if not has_address and not has_interface:
            return

        address_key = f"Camera{camera_index}_Address"
        interface_key = f"Camera{camera_index}_Interface"
        camera_section_pattern = re.compile(r"(?is)(\[Camera\].*?)(\n\[|$)")

        for ini_path in self._candidate_ini_paths():
            if not ini_path.exists():
                continue
            try:
                raw = ini_path.read_text(encoding="utf-8", errors="ignore")
                newline = "\r\n" if "\r\n" in raw else "\n"
                match = camera_section_pattern.search(raw)
                if not match:
                    continue

                camera_block = match.group(1)
                updated_block = camera_block
                if has_address:
                    updated_block = self._replace_or_add_key(
                        updated_block,
                        address_key,
                        settings.sdk_camera_address.strip(),
                        newline,
                    )
                if has_interface:
                    updated_block = self._replace_or_add_key(
                        updated_block,
                        interface_key,
                        str(settings.sdk_camera_interface),
                        newline,
                    )

                if updated_block != camera_block:
                    start, end = match.span(1)
                    new_raw = f"{raw[:start]}{updated_block}{raw[end:]}"
                    ini_path.write_text(new_raw, encoding="utf-8")
            except OSError:
                # Ini sync is a best-effort pre-step. Connection will still try normal SDK flow.
                continue

    def _is_network_mode(self) -> bool:
        if settings.sdk_camera_interface == 3:
            return True
        return bool(settings.sdk_camera_address.strip())

    def _prepare_transport(self, camera_index: int) -> None:
        if not self._is_network_mode():
            return

        # Reset stale server sessions before preparing a new network link.
        self._network_unlock_sequence(camera_index)
        self._sync_network_profile_to_ini(camera_index)

        status = c_int()
        connection_type = settings.sdk_camera_interface if settings.sdk_camera_interface >= 0 else 3
        ip_raw = settings.sdk_camera_address.strip().encode("ascii", errors="ignore")
        ip_arg = c_char_p(ip_raw if ip_raw else None)
        logger.info(
            "SDK transport prepare camera_index=%s connection_type=%s address=%s",
            camera_index,
            connection_type,
            settings.sdk_camera_address.strip(),
        )

        ok_interface = False
        for step in range(1, 4):
            status = c_int()
            ok_interface = self.lib.SetupCameraInterface(connection_type, ip_arg, byref(status), camera_index)
            if ok_interface:
                break
            if status.value != 10:
                self._raise_if_failed(ok_interface, status.value, "SetupCameraInterface")
            logger.warning("SDK transport busy at SetupCameraInterface step=%s/3", step)
            self._network_unlock_sequence(camera_index)
            time.sleep(0.4)

        if not ok_interface:
            logger.warning("SDK transport switching to legacy network path")
            self._prepare_transport_legacy(camera_index, connection_type, ip_arg)
            return

        ok_server = self.lib.ConnectToSingleCameraServer(camera_index)
        if not ok_server:
            ok_server = self.lib.ConnectToMultiCameraServer()
        if not ok_server:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "ConnectTo*CameraServer failed")
        logger.info("SDK transport connected camera_index=%s", camera_index)
        self._server_connected = True

    def _prepare_transport_legacy(self, camera_index: int, connection_type: int, ip_arg: c_char_p) -> None:
        if not self._has_legacy_set_connection_type:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "legacy SetConnectionType is unavailable")
        status = c_int()
        ok_conn_type = self.lib.SetConnectionType(connection_type, ip_arg, byref(status))
        self._raise_if_failed(ok_conn_type, status.value, "SetConnectionType")

        ok_server = False
        if self._has_legacy_connect_to_server:
            ok_server = self.lib.ConnectToCameraServer()
        if not ok_server:
            ok_server = self.lib.ConnectToSingleCameraServer(camera_index)
        if not ok_server:
            ok_server = self.lib.ConnectToMultiCameraServer()
        if not ok_server:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "Legacy ConnectTo*CameraServer failed")
        logger.info("SDK legacy transport connected camera_index=%s", camera_index)
        self._server_connected = True

    def _network_unlock_sequence(self, camera_index: int) -> None:
        logger.info("SDK unlock sequence camera_index=%s", camera_index)
        try:
            status = c_int()
            self.lib.DisconnectCamera(byref(status), camera_index)
        except Exception:
            pass
        for addr in (camera_index, 0, 1, 2, 3):
            try:
                self.lib.DisconnectCameraServer(addr)
            except Exception:
                continue
        self._server_connected = False
        time.sleep(0.15)

    def _disconnect_server_best_effort(self, camera_index: int) -> None:
        logger.info("SDK transport disconnect best effort camera_index=%s", camera_index)
        for addr in (camera_index, 0):
            try:
                self.lib.DisconnectCameraServer(addr)
            except Exception:
                continue
        self._server_connected = False

    def _post_connect_configuration(self, camera_index: int) -> None:
        status = c_int()
        ok_busy = self.lib.SetBusyTimeout(max(0, settings.sdk_busy_timeout_ms))
        if not ok_busy:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "SetBusyTimeout failed")

        ok_speed = self.lib.SetReadOutSpeed(settings.sdk_readout_speed, byref(status), camera_index)
        self._raise_if_failed(ok_speed, status.value, "SetReadOutSpeed")

        ok_output = self.lib.SetupSensorOutputMode(settings.sdk_sensor_output_mode, camera_index)
        if not ok_output:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "SetupSensorOutputMode failed")

        status = c_int()
        ok_depth = self.lib.SetBitDepth(settings.sdk_bit_depth, byref(status), camera_index)
        self._raise_if_failed(ok_depth, status.value, "SetBitDepth")

    @staticmethod
    def _raise_if_failed(ok: bool, status_code: int, operation: str) -> None:
        if ok:
            return
        message = STATUS_MESSAGES.get(status_code, "unknown status")
        raise SdkError(
            SdkErrorCode.SDK_CALL_FAILED,
            f"{operation} failed: {message}",
            status_code=status_code,
        )

    def connect(self, camera_index: int) -> CameraInfo:
        attempts = 5 if self._is_network_mode() else 1
        last_error: Exception | None = None
        with self._sdk_lock:
            for attempt in range(1, attempts + 1):
                try:
                    logger.info("SDK connect attempt=%s/%s camera_index=%s", attempt, attempts, camera_index)
                    self._prepare_transport(camera_index)

                    if not self._is_network_mode():
                        # Required by SDK for direct USB / MultiCam path.
                        _ = self.lib.GetNumberOfConnectedCams()

                    model_id = c_int()
                    model_str = c_char_p()
                    status = c_int()

                    ok = self.lib.ConnectCamera(byref(model_id), byref(model_str), byref(status), camera_index)
                    self._raise_if_failed(ok, status.value, "ConnectCamera")

                    init_status = c_int()
                    ok_init = self.lib.InitCamera(byref(init_status), camera_index)
                    self._raise_if_failed(ok_init, init_status.value, "InitCamera")
                    self._post_connect_configuration(camera_index)

                    raw_name = model_str.value.decode("utf-8", errors="ignore") if model_str.value else "GreatEyes"
                    logger.info(
                        "SDK connect success camera_index=%s model_id=%s model_name=%s",
                        camera_index,
                        model_id.value,
                        raw_name,
                    )
                    return CameraInfo(model_id=model_id.value, model_name=raw_name)
                except Exception as exc:
                    last_error = exc
                    logger.exception("SDK connect failed attempt=%s camera_index=%s", attempt, camera_index)
                    if self._is_network_mode():
                        self._disconnect_server_best_effort(camera_index)
                    if isinstance(exc, SdkError) and exc.status_code == 10 and attempt < attempts:
                        time.sleep(min(2.0, 0.3 * attempt))
                        continue
                    raise

        if last_error:
            raise last_error
        raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "connect failed")

    def disconnect(self, camera_index: int) -> None:
        with self._sdk_lock:
            logger.info("SDK disconnect camera_index=%s", camera_index)
            status = c_int()
            ok = self.lib.DisconnectCamera(byref(status), camera_index)
            if self._server_connected:
                self._disconnect_server_best_effort(camera_index)
            self._cooling_initialized = False
            self._cooling_min_temp = None
            self._cooling_max_temp = None
            self._cooling_levels = 0
            if not ok and status.value != 10:
                self._raise_if_failed(ok, status.value, "DisconnectCamera")

    def capabilities(self, camera_index: int, has_shutter: bool) -> CameraCapabilities:
        width = c_int()
        height = c_int()
        bytes_per_pixel = c_int()
        ok = self.lib.GetImageSize(byref(width), byref(height), byref(bytes_per_pixel), camera_index)
        if not ok:
            raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "GetImageSize failed")

        pixel_size = self.lib.GetSizeOfPixel(camera_index)

        status_x = c_int()
        status_y = c_int()
        max_binx = self.lib.GetMaxBinningX(byref(status_x), camera_index)
        max_biny = self.lib.GetMaxBinningY(byref(status_y), camera_index)

        return CameraCapabilities(
            camera_x_size=width.value,
            camera_y_size=height.value,
            pixel_size_um=pixel_size,
            max_binx=max_binx,
            max_biny=max_biny,
            has_shutter=has_shutter,
            sensor_name="GreatEyes 9.0",
        )

    def start_exposure(self, camera_index: int, duration_sec: float, light: bool) -> None:
        with self._sdk_lock:
            exposure_ms = max(1, int(duration_sec * 1000))
            logger.info(
                "SDK exposure start camera_index=%s duration_sec=%s exposure_ms=%s light=%s dyn=%s",
                camera_index,
                duration_sec,
                exposure_ms,
                light,
                self._use_dyn_bitdepth_api,
            )
            status = c_int()
            ok_set = self.lib.SetExposure(exposure_ms, byref(status), camera_index)
            self._raise_if_failed(ok_set, status.value, "SetExposure")

            ok = False
            if self._use_dyn_bitdepth_api:
                try:
                    ok = self.lib.StartMeasurement_DynBitDepth(False, False, bool(light), False, byref(status), camera_index)
                except OSError:
                    logger.exception("SDK dyn StartMeasurement crashed, fallback to classic API")
                    ok = False
                if not ok and status.value == 0:
                    try:
                        ok = self.lib.StartMeasurement(False, False, bool(light), False, exposure_ms, byref(status), camera_index)
                    except OSError as exc:
                        raise SdkError(SdkErrorCode.SDK_CALL_FAILED, f"StartMeasurement crashed: {exc}") from exc
            else:
                try:
                    ok = self.lib.StartMeasurement(False, False, bool(light), False, exposure_ms, byref(status), camera_index)
                except OSError as exc:
                    raise SdkError(SdkErrorCode.SDK_CALL_FAILED, f"StartMeasurement crashed: {exc}") from exc
            self._raise_if_failed(ok, status.value, "StartMeasurement")

    def is_exposure_busy(self, camera_index: int) -> bool:
        return bool(self.lib.DllIsBusy(camera_index))

    def read_measurement_data(self, camera_index: int, width: int, height: int) -> bytes:
        with self._sdk_lock:
            pixel_count = width * height
            if pixel_count <= 0:
                raise SdkError(SdkErrorCode.INVALID_STATUS, "invalid image size")
            logger.info("SDK read data camera_index=%s width=%s height=%s pixels=%s", camera_index, width, height, pixel_count)
            frame = (c_ushort * pixel_count)()
            status = c_int()
            if self._use_dyn_bitdepth_api:
                try:
                    ok = self.lib.GetMeasurementData_DynBitDepth(frame, byref(status), camera_index)
                except OSError:
                    logger.exception("SDK dyn GetMeasurementData crashed, fallback to classic API")
                    ok = False
                if not ok and status.value == 0:
                    write_bytes = c_int()
                    read_bytes = c_int()
                    try:
                        ok = self.lib.GetMeasurementData(frame, byref(write_bytes), byref(read_bytes), byref(status), camera_index)
                    except OSError as exc:
                        raise SdkError(SdkErrorCode.SDK_CALL_FAILED, f"GetMeasurementData crashed: {exc}") from exc
            else:
                write_bytes = c_int()
                read_bytes = c_int()
                try:
                    ok = self.lib.GetMeasurementData(frame, byref(write_bytes), byref(read_bytes), byref(status), camera_index)
                except OSError as exc:
                    raise SdkError(SdkErrorCode.SDK_CALL_FAILED, f"GetMeasurementData crashed: {exc}") from exc
            self._raise_if_failed(ok, status.value, "GetMeasurementData")
            return ctypes.string_at(frame, pixel_count * ctypes.sizeof(c_ushort))

    def stop_exposure(self, camera_index: int) -> None:
        with self._sdk_lock:
            ok = self.lib.StopMeasurement(camera_index)
            if not ok:
                raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "StopMeasurement failed")

    def _ensure_cooling_initialized(self, camera_index: int) -> None:
        if self._cooling_initialized:
            return
        logger.info("SDK cooling init camera_index=%s hw_option=%s", camera_index, settings.cooling_hardware_option)
        min_temp = c_int()
        max_temp = c_int()
        status = c_int()
        levels = self.lib.TemperatureControl_Init(
            settings.cooling_hardware_option,
            byref(min_temp),
            byref(max_temp),
            byref(status),
            camera_index,
        )
        use_level_mode = levels <= 0
        if levels > 0 and min_temp.value == 0 and max_temp.value == 0:
            # New API returns non-zero levels but no usable absolute range. Prefer level-mode path.
            use_level_mode = True

        if use_level_mode:
            # Older / model-specific SDK path: setup by cooler levels instead of absolute target range.
            levels = self.lib.TemperatureControl_Setup(settings.cooling_hardware_option, byref(status), camera_index)
            if levels <= 0:
                message = STATUS_MESSAGES.get(status.value, "temperature init failed")
                raise SdkError(SdkErrorCode.SDK_CALL_FAILED, f"TemperatureControl_Init failed: {message}", status.value)
            self._cooling_min_temp = None
            self._cooling_max_temp = None
        else:
            self._cooling_min_temp = min_temp.value
            self._cooling_max_temp = max_temp.value
        self._cooling_levels = levels
        self._cooling_initialized = True
        logger.info(
            "SDK cooling initialized camera_index=%s levels=%s min=%s max=%s",
            camera_index,
            self._cooling_levels,
            self._cooling_min_temp,
            self._cooling_max_temp,
        )

    def get_temperatures(self, camera_index: int) -> tuple[int, int]:
        with self._sdk_lock:
            self._ensure_cooling_initialized(camera_index)
            sensor = c_int()
            backside = c_int()
            status_sensor = c_int()
            status_backside = c_int()

            ok_sensor = self.lib.TemperatureControl_GetTemperature(0, byref(sensor), byref(status_sensor), camera_index)
            self._raise_if_failed(ok_sensor, status_sensor.value, "TemperatureControl_GetTemperature(sensor)")

            ok_backside = self.lib.TemperatureControl_GetTemperature(1, byref(backside), byref(status_backside), camera_index)
            self._raise_if_failed(ok_backside, status_backside.value, "TemperatureControl_GetTemperature(backside)")
            return sensor.value, backside.value

    def set_target_temperature(self, camera_index: int, target_temp_c: int) -> None:
        with self._sdk_lock:
            self._ensure_cooling_initialized(camera_index)
            if self._cooling_min_temp is not None and self._cooling_max_temp is not None:
                if target_temp_c < self._cooling_min_temp or target_temp_c > self._cooling_max_temp:
                    raise SdkError(
                        SdkErrorCode.INVALID_STATUS,
                        f"target_temp_c out of range {self._cooling_min_temp}..{self._cooling_max_temp}",
                    )
                status = c_int()
                ok = self.lib.TemperatureControl_SetTemperature(target_temp_c, byref(status), camera_index)
                self._raise_if_failed(ok, status.value, "TemperatureControl_SetTemperature")
                return

            # Legacy cooler-level mode fallback:
            # no absolute temperature range is available from SDK, so map target
            # temperature to the available discrete cooling levels.
            if self._cooling_levels <= 0:
                raise SdkError(SdkErrorCode.INVALID_STATUS, "cooling levels are unavailable")
            status = c_int()
            desired_level = self._map_target_temp_to_level(target_temp_c)
            ok = self.lib.TemperatureControl_SetTemperatureLevel(desired_level, byref(status), camera_index)
            self._raise_if_failed(ok, status.value, "TemperatureControl_SetTemperatureLevel")

    def _map_target_temp_to_level(self, target_temp_c: int) -> int:
        """Business rule for SDK level-mode cooling.

        Level mode does not expose min/max absolute temperatures, only an integer
        level range [1..N]. We use a deterministic linear mapping from a
        business-approved virtual range:
        - cold end:  -80 C -> level N
        - warm end:  +20 C -> level 1
        Values outside range are clamped.
        """
        if self._cooling_levels <= 0:
            raise SdkError(SdkErrorCode.INVALID_STATUS, "cooling levels are unavailable")

        virtual_min_c = -80
        virtual_max_c = 20
        clamped_target = max(virtual_min_c, min(virtual_max_c, target_temp_c))
        cold_ratio = (virtual_max_c - clamped_target) / float(virtual_max_c - virtual_min_c)
        mapped = int(round(1 + cold_ratio * (self._cooling_levels - 1)))
        return max(1, min(self._cooling_levels, mapped))

    def switch_off_cooling(self, camera_index: int) -> None:
        with self._sdk_lock:
            self._ensure_cooling_initialized(camera_index)
            status = c_int()
            ok = self.lib.TemperatureControl_SwitchOff(byref(status), camera_index)
            self._raise_if_failed(ok, status.value, "TemperatureControl_SwitchOff")

    def set_readout_speed(self, camera_index: int, speed_khz: int) -> None:
        with self._sdk_lock:
            status = c_int()
            ok = self.lib.SetReadOutSpeed(speed_khz, byref(status), camera_index)
            self._raise_if_failed(ok, status.value, "SetReadOutSpeed")

    def set_sensor_output_mode(self, camera_index: int, mode: int) -> None:
        with self._sdk_lock:
            ok = self.lib.SetupSensorOutputMode(mode, camera_index)
            if not ok:
                raise SdkError(SdkErrorCode.SDK_CALL_FAILED, "SetupSensorOutputMode failed")
