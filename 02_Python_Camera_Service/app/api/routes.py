import logging
import uuid

from fastapi import APIRouter, HTTPException, Response

from app.camera_runtime import camera_runtime
from app.config import settings
from app.schemas import (
    FitsExportRequest,
    FitsExportResponse,
    CoolingControllerModeRequest,
    CoolingControllerStatusResponse,
    CoolingTelemetryResponse,
    CameraProfileCreateRequest,
    CameraProfileListResponse,
    CameraProfileResponse,
    CameraProfileUpdateRequest,
    CoolerPowerRequest,
    CoolingStatusResponse,
    CameraCapabilitiesResponse,
    CameraStateResponse,
    ConnectResponse,
    DisconnectResponse,
    ExposureResponse,
    ExposureStartRequest,
    HealthResponse,
    ImageMetadataResponse,
    ImageResizeRequest,
    ImageResizeResponse,
    LatestImageResponse,
    EventLogListResponse,
    TargetTemperatureRequest,
    WarmupResponse,
    WarmupStartRequest,
    RoiBinningRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from app.sdk_adapter import SdkError
from app.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _apply_runtime_settings_from_profile(profile: dict) -> None:
    settings.sdk_camera_address = str(profile.get("sdk_camera_address", ""))
    settings.sdk_camera_port = int(profile.get("sdk_camera_port", 12345))
    settings.sdk_camera_interface = int(profile.get("sdk_camera_interface", -1))
    settings.camera_index = int(profile.get("sdk_camera_index", 0))
    settings.cooling_hardware_option = int(profile.get("temperature_hardware_option", 42223))
    settings.sdk_readout_speed = int(profile.get("readout_speed", settings.sdk_readout_speed))
    if profile.get("gain_mode") is not None:
        settings.sdk_sensor_output_mode = int(profile["gain_mode"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    storage_service.write_event(event_type="health_check", message="health endpoint called")
    return HealthResponse(
        status="ok",
        storage_mode=settings.storage_mode,
        db=storage_service.health_db_label(),
    )


@router.get("/camera/state", response_model=CameraStateResponse)
def camera_state() -> CameraStateResponse:
    state = camera_runtime.state
    return CameraStateResponse(
        connected=state.connected,
        camera_state=state.camera_state,
        image_ready=state.image_ready,
        active_exposure_id=state.active_exposure_id,
    )


@router.post("/camera/connect", response_model=ConnectResponse)
def connect_camera() -> ConnectResponse:
    already_connected = camera_runtime.state.connected
    try:
        state = camera_runtime.connect()
    except SdkError as exc:
        storage_service.write_event(event_type="camera_connect_failed", message=str(exc), level="ERROR")
        raise HTTPException(status_code=500, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    if not already_connected:
        session_id = storage_service.start_camera_session(
            camera_index=settings.camera_index,
            model_id=state.camera_info.model_id,
            model_name=state.camera_info.model_name,
        )
        camera_runtime.set_active_session_id(session_id)
        storage_service.write_event(event_type="camera_connected", message=f"connected: {state.camera_info.model_name}")
    return ConnectResponse(
        connected=True,
        camera_model_id=state.camera_info.model_id,
        camera_model_name=state.camera_info.model_name,
        camera_state=state.camera_state,
    )


@router.post("/camera/disconnect", response_model=DisconnectResponse)
def disconnect_camera() -> DisconnectResponse:
    try:
        state = camera_runtime.disconnect()
    except SdkError as exc:
        storage_service.write_event(event_type="camera_disconnect_failed", message=str(exc), level="ERROR")
        raise HTTPException(status_code=500, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.close_camera_session(camera_runtime.state.active_session_id, status="disconnected")
    storage_service.write_event(event_type="camera_disconnected", message="camera disconnected")
    return DisconnectResponse(connected=state.connected, camera_state=state.camera_state)


@router.get("/camera/capabilities", response_model=CameraCapabilitiesResponse)
def get_camera_capabilities() -> CameraCapabilitiesResponse:
    try:
        payload = camera_runtime.capabilities()
    except SdkError as exc:
        storage_service.write_event(event_type="camera_capabilities_failed", message=str(exc), level="ERROR")
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    return CameraCapabilitiesResponse(**payload)


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    payload = storage_service.get_settings()
    return SettingsResponse(**payload)


@router.put("/settings", response_model=SettingsResponse)
def put_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    payload = storage_service.save_settings(request.model_dump())
    if payload.get("sdk_camera_address") is not None:
        settings.sdk_camera_address = str(payload["sdk_camera_address"])
    if payload.get("sdk_camera_port") is not None:
        settings.sdk_camera_port = int(payload["sdk_camera_port"])
    if payload.get("sdk_camera_interface") is not None:
        settings.sdk_camera_interface = int(payload["sdk_camera_interface"])
    if payload.get("camera_index") is not None:
        settings.camera_index = int(payload["camera_index"])
    if payload.get("temperature_hardware_option") is not None:
        settings.cooling_hardware_option = int(payload["temperature_hardware_option"])
    if payload.get("readout_speed") is not None:
        settings.sdk_readout_speed = int(payload["readout_speed"])
    if payload.get("fits_export_bitpix") is not None:
        settings.fits_export_bitpix = int(payload["fits_export_bitpix"])
    if payload.get("default_gain_mode") is not None:
        settings.sdk_sensor_output_mode = int(payload["default_gain_mode"])
    storage_service.write_event(event_type="settings_updated", message="camera defaults updated")
    if camera_runtime.state.connected:
        try:
            camera_runtime.apply_sdk_imaging_settings()
        except SdkError as exc:
            logger.warning("apply_sdk_imaging_settings failed: %s", exc)
    return SettingsResponse(**payload)


@router.get("/camera/profiles", response_model=CameraProfileListResponse)
def get_camera_profiles() -> CameraProfileListResponse:
    return CameraProfileListResponse(items=storage_service.list_camera_profiles())


@router.post("/camera/profiles", response_model=CameraProfileResponse)
def create_camera_profile(request: CameraProfileCreateRequest) -> CameraProfileResponse:
    payload = request.model_dump()
    payload["profile_id"] = str(uuid.uuid4())
    created = storage_service.create_camera_profile(payload)
    storage_service.write_event(event_type="camera_profile_created", message=f"profile={created['name']}")
    return CameraProfileResponse(**created)


@router.put("/camera/profiles/{profile_id}", response_model=CameraProfileResponse)
def put_camera_profile(profile_id: str, request: CameraProfileUpdateRequest) -> CameraProfileResponse:
    updated = storage_service.update_camera_profile(profile_id=profile_id, payload=request.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail={"error_code": "PROFILE_NOT_FOUND", "message": "profile not found"})
    storage_service.write_event(event_type="camera_profile_updated", message=f"profile={updated['name']}")
    return CameraProfileResponse(**updated)


@router.post("/camera/profiles/{profile_id}/activate", response_model=CameraProfileResponse)
def activate_profile(profile_id: str) -> CameraProfileResponse:
    if camera_runtime.state.connected:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "CAMERA_CONNECTED", "message": "disconnect camera before activating profile"},
        )
    profile = storage_service.activate_camera_profile(profile_id=profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail={"error_code": "PROFILE_NOT_FOUND", "message": "profile not found"})
    _apply_runtime_settings_from_profile(profile)
    storage_service.save_settings(
        {
            "sdk_camera_address": profile["sdk_camera_address"],
            "sdk_camera_port": profile["sdk_camera_port"],
            "sdk_camera_interface": profile["sdk_camera_interface"],
            "camera_index": profile["sdk_camera_index"],
            "temperature_hardware_option": profile["temperature_hardware_option"],
            "readout_speed": profile["readout_speed"],
            "default_gain_mode": profile["gain_mode"],
        }
    )
    storage_service.write_event(event_type="camera_profile_activated", message=f"profile={profile['name']}")
    return CameraProfileResponse(**profile)


@router.put("/camera/config/roi-binning")
def put_roi_binning(request: RoiBinningRequest):
    try:
        camera_runtime.set_roi_binning(
            bin_x=request.bin_x,
            bin_y=request.bin_y,
            num_x=request.num_x,
            num_y=request.num_y,
            start_x=request.start_x,
            start_y=request.start_y,
        )
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="roi_binning_updated", message="roi/binning updated")
    return {"status": "ok"}


@router.post("/camera/exposures", response_model=ExposureResponse)
def start_exposure(request: ExposureStartRequest) -> ExposureResponse:
    try:
        job = camera_runtime.start_exposure(duration_sec=request.duration_sec, light=request.light)
    except SdkError as exc:
        storage_service.write_event(event_type="exposure_start_failed", message=str(exc), level="ERROR")
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    except Exception as exc:
        storage_service.write_event(event_type="exposure_start_failed", message=str(exc), level="ERROR")
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(exc)}) from exc
    storage_service.write_event(event_type="exposure_started", message=f"exposure {job.exposure_id} started")
    storage_service.create_exposure_job(
        exposure_id=job.exposure_id,
        session_id=camera_runtime.state.active_session_id,
        duration_sec=request.duration_sec,
        light_frame=request.light,
        state=job.state,
    )
    return ExposureResponse(
        exposure_id=job.exposure_id,
        state=job.state,
        image_ready=job.image_ready,
        percent=job.percent,
        error=job.error,
    )


@router.get("/camera/exposures/{exposure_id}/status", response_model=ExposureResponse)
def exposure_status(exposure_id: str) -> ExposureResponse:
    try:
        job = camera_runtime.exposure_status(exposure_id)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    if job.state == "completed" and not job.completion_logged:
        storage_service.write_event(event_type="exposure_completed", message=f"exposure {exposure_id} completed")
        storage_service.update_exposure_job(exposure_id=exposure_id, state="completed", error_message=job.error)
        try:
            latest = camera_runtime.latest_image()
            if latest.get("exposure_id") == exposure_id:
                storage_service.save_exposure_image_meta(
                    exposure_id=exposure_id,
                    width=int(latest["width"]),
                    height=int(latest["height"]),
                    pixel_type=str(latest["pixel_type"]),
                    orientation=str(latest["orientation"]),
                    bin_x=int(latest["bin_x"]),
                    bin_y=int(latest["bin_y"]),
                    start_x=int(camera_runtime.state.start_x),
                    start_y=int(camera_runtime.state.start_y),
                )
        except SdkError:
            pass
        job.completion_logged = True
    elif job.state in {"error", "aborted", "stopped"}:
        storage_service.update_exposure_job(exposure_id=exposure_id, state=job.state, error_message=job.error)
    return ExposureResponse(
        exposure_id=job.exposure_id,
        state=job.state,
        image_ready=job.image_ready,
        percent=job.percent,
        error=job.error,
    )


@router.post("/camera/exposures/{exposure_id}/abort", response_model=ExposureResponse)
def abort_exposure(exposure_id: str) -> ExposureResponse:
    try:
        job = camera_runtime.abort_exposure(exposure_id)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="exposure_aborted", message=f"exposure {exposure_id} aborted")
    storage_service.update_exposure_job(exposure_id=exposure_id, state="aborted", error_message=job.error)
    return ExposureResponse(
        exposure_id=job.exposure_id,
        state=job.state,
        image_ready=job.image_ready,
        percent=job.percent,
        error=job.error,
    )


@router.post("/camera/exposures/{exposure_id}/stop", response_model=ExposureResponse)
def stop_exposure(exposure_id: str) -> ExposureResponse:
    try:
        job = camera_runtime.stop_exposure(exposure_id)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="exposure_stopped", message=f"exposure {exposure_id} stopped")
    storage_service.update_exposure_job(exposure_id=exposure_id, state="stopped", error_message=job.error)
    return ExposureResponse(
        exposure_id=job.exposure_id,
        state=job.state,
        image_ready=job.image_ready,
        percent=job.percent,
        error=job.error,
    )


@router.get("/camera/images/latest", response_model=LatestImageResponse)
def latest_image(include_pixel_data: bool = True) -> LatestImageResponse:
    try:
        payload = camera_runtime.latest_image()
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    if not include_pixel_data:
        payload = dict(payload)
        payload["pixel_data_base64"] = None
    return LatestImageResponse(**payload)


@router.get("/camera/images/latest/raw")
def latest_image_raw() -> Response:
    try:
        meta, frame_bytes = camera_runtime.latest_image_bytes()
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    headers = {
        "X-Exposure-Id": str(meta.get("exposure_id", "")),
        "X-Width": str(meta.get("width", "")),
        "X-Height": str(meta.get("height", "")),
        "X-Pixel-Type": str(meta.get("pixel_type", "uint16")),
        "X-Orientation": str(meta.get("orientation", "top_left_origin")),
        "X-Bin-X": str(meta.get("bin_x", 1)),
        "X-Bin-Y": str(meta.get("bin_y", 1)),
    }
    return Response(content=frame_bytes, media_type="application/octet-stream", headers=headers)


@router.get("/camera/images/latest/metadata", response_model=ImageMetadataResponse)
def latest_image_metadata() -> ImageMetadataResponse:
    try:
        payload = camera_runtime.latest_image_metadata()
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    return ImageMetadataResponse(**payload)


@router.post("/camera/images/latest/resize", response_model=ImageResizeResponse)
def resize_latest_image(request: ImageResizeRequest) -> ImageResizeResponse:
    try:
        payload = camera_runtime.resize_latest_image(width=request.width, height=request.height)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(
        event_type="image_resized",
        message=f"resize latest image to {request.width}x{request.height}",
    )
    return ImageResizeResponse(**payload)


@router.post("/camera/images/latest/export/fits", response_model=FitsExportResponse)
def export_latest_fits(request: FitsExportRequest) -> FitsExportResponse:
    try:
        payload = camera_runtime.export_latest_image_fits(filename=request.file_name)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(
        event_type="image_export_fits",
        message=f"fits exported: {payload['file_name']}",
    )
    return FitsExportResponse(**payload)


@router.put("/camera/cooling/power", response_model=CoolingStatusResponse)
def set_cooling_power(request: CoolerPowerRequest) -> CoolingStatusResponse:
    logger.info(
        "API cooling_power cooler_on=%s cooler_power_percent=%s",
        request.cooler_on,
        request.cooler_power_percent,
    )
    try:
        payload = camera_runtime.set_cooler_power(
            cooler_on=request.cooler_on,
            cooler_power_percent=request.cooler_power_percent,
        )
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="cooling_power_updated", message="cooling power updated")
    return CoolingStatusResponse(**payload)


@router.put("/camera/cooling/target", response_model=CoolingStatusResponse)
def set_target_temperature(request: TargetTemperatureRequest) -> CoolingStatusResponse:
    logger.info("API cooling_target target_temp_c=%s", request.target_temp_c)
    try:
        payload = camera_runtime.set_target_temperature(request.target_temp_c)
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="cooling_target_updated", message="cooling target updated")
    return CoolingStatusResponse(**payload)


@router.get("/camera/cooling/status", response_model=CoolingStatusResponse)
def get_cooling_status() -> CoolingStatusResponse:
    try:
        payload = camera_runtime.cooling_status()
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    return CoolingStatusResponse(**payload)


@router.get("/camera/cooling/controller/status", response_model=CoolingControllerStatusResponse)
def get_cooling_controller_status() -> CoolingControllerStatusResponse:
    payload = camera_runtime.controller_status()
    logger.info("API cooling_controller_status %s", payload)
    return CoolingControllerStatusResponse(**payload)


@router.put("/camera/cooling/controller/mode", response_model=CoolingControllerStatusResponse)
def put_cooling_controller_mode(request: CoolingControllerModeRequest) -> CoolingControllerStatusResponse:
    logger.info("API cooling_controller_mode mode=%s", request.mode)
    try:
        payload = camera_runtime.set_controller_mode(request.mode)
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="cooling_controller_mode_updated", message=f"mode={request.mode}")
    return CoolingControllerStatusResponse(**payload)


@router.get("/camera/cooling/debug")
def get_cooling_debug():
    return camera_runtime.cooling_debug()


@router.get("/camera/cooling/telemetry", response_model=CoolingTelemetryResponse)
def get_cooling_telemetry(limit: int = 120) -> CoolingTelemetryResponse:
    return CoolingTelemetryResponse(items=camera_runtime.cooling_telemetry(limit=limit))


@router.post("/camera/cooling/warmup", response_model=WarmupResponse)
def start_warmup(request: WarmupStartRequest) -> WarmupResponse:
    try:
        job = camera_runtime.start_warmup(
            target_temp_c=request.target_temp_c,
            temp_step_c=request.temp_step_c,
            power_step_percent=request.power_step_percent,
            step_interval_sec=request.step_interval_sec,
        )
    except SdkError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    storage_service.write_event(event_type="warmup_started", message=f"warmup {job.warmup_job_id} started")
    return WarmupResponse(
        warmup_job_id=job.warmup_job_id,
        state=job.state,
        current_temp_c=job.current_temp_c,
        current_power_percent=job.current_power_percent,
        target_temp_c=job.target_temp_c,
        error=job.error,
    )


@router.get("/camera/cooling/warmup/{warmup_job_id}", response_model=WarmupResponse)
def get_warmup_status(warmup_job_id: str) -> WarmupResponse:
    try:
        job = camera_runtime.warmup_status(warmup_job_id)
    except SdkError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc.code), "message": str(exc)}) from exc
    if job.state == "completed" and not job.completion_logged:
        storage_service.write_event(event_type="warmup_completed", message=f"warmup {warmup_job_id} completed")
        job.completion_logged = True
    return WarmupResponse(
        warmup_job_id=job.warmup_job_id,
        state=job.state,
        current_temp_c=job.current_temp_c,
        current_power_percent=job.current_power_percent,
        target_temp_c=job.target_temp_c,
        error=job.error,
    )


@router.get("/camera/cooling/warmup/{warmup_job_id}/status", response_model=WarmupResponse)
def get_warmup_status_legacy(warmup_job_id: str) -> WarmupResponse:
    return get_warmup_status(warmup_job_id)


@router.get("/logs/events", response_model=EventLogListResponse)
def get_events(limit: int = 100) -> EventLogListResponse:
    return EventLogListResponse(items=storage_service.read_events(limit=limit))
