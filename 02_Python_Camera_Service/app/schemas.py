from pydantic import BaseModel, Field, field_validator

from app.config import FITS_EXPORT_BITPIX_OPTIONS, GAIN_MODE_OPTIONS, READOUT_SPEED_OPTIONS


class HealthResponse(BaseModel):
    status: str
    storage_mode: str
    db: str


class CameraStateResponse(BaseModel):
    connected: bool
    camera_state: str
    image_ready: bool
    active_exposure_id: str | None


class ConnectResponse(BaseModel):
    connected: bool
    camera_model_id: int
    camera_model_name: str
    camera_state: str


class DisconnectResponse(BaseModel):
    connected: bool
    camera_state: str


class CameraCapabilitiesResponse(BaseModel):
    camera_x_size: int
    camera_y_size: int
    pixel_size_um: int
    max_binx: int
    max_biny: int
    has_shutter: bool
    sensor_name: str


class SettingsResponse(BaseModel):
    readout_speed: int
    default_gain_mode: str
    default_cooler_level: int
    has_shutter: bool
    sensor_name_override: str
    sdk_camera_address: str = ""
    sdk_camera_port: int = 12345
    sdk_camera_interface: int = -1
    camera_index: int = 0
    temperature_hardware_option: int = 42223
    fits_export_bitpix: int = 32


class SettingsUpdateRequest(BaseModel):
    readout_speed: int | None = None
    default_gain_mode: str | None = None
    default_cooler_level: int | None = None
    has_shutter: bool | None = None
    sensor_name_override: str | None = None
    sdk_camera_address: str | None = None
    sdk_camera_port: int | None = None
    sdk_camera_interface: int | None = None
    camera_index: int | None = None
    temperature_hardware_option: int | None = None
    fits_export_bitpix: int | None = None

    @field_validator("readout_speed")
    @classmethod
    def validate_readout_speed(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in READOUT_SPEED_OPTIONS:
            raise ValueError(f"readout_speed must be one of {READOUT_SPEED_OPTIONS}")
        return value

    @field_validator("default_gain_mode")
    @classmethod
    def validate_gain_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in GAIN_MODE_OPTIONS:
            raise ValueError(f"default_gain_mode must be one of {GAIN_MODE_OPTIONS}")
        return value

    @field_validator("sdk_camera_port")
    @classmethod
    def validate_camera_port(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 65535:
            raise ValueError("sdk_camera_port must be in range 1..65535")
        return value

    @field_validator("fits_export_bitpix")
    @classmethod
    def validate_fits_export_bitpix(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in FITS_EXPORT_BITPIX_OPTIONS:
            raise ValueError(f"fits_export_bitpix must be one of {FITS_EXPORT_BITPIX_OPTIONS}")
        return value


class CameraProfileResponse(BaseModel):
    profile_id: str
    name: str
    is_default: bool
    is_active: bool
    sdk_camera_address: str
    sdk_camera_port: int
    sdk_camera_interface: int
    sdk_camera_index: int
    temperature_hardware_option: int
    readout_speed: int
    gain_mode: str


class CameraProfileListResponse(BaseModel):
    items: list[CameraProfileResponse]


class CameraProfileCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    sdk_camera_address: str = ""
    sdk_camera_port: int = 12345
    sdk_camera_interface: int = -1
    sdk_camera_index: int = 0
    temperature_hardware_option: int = 42223
    readout_speed: int = 500
    gain_mode: str = "1"

    @field_validator("readout_speed")
    @classmethod
    def validate_readout_speed(cls, value: int) -> int:
        if value not in READOUT_SPEED_OPTIONS:
            raise ValueError(f"readout_speed must be one of {READOUT_SPEED_OPTIONS}")
        return value

    @field_validator("gain_mode")
    @classmethod
    def validate_gain_mode(cls, value: str) -> str:
        if value not in GAIN_MODE_OPTIONS:
            raise ValueError(f"gain_mode must be one of {GAIN_MODE_OPTIONS}")
        return value

    @field_validator("sdk_camera_port")
    @classmethod
    def validate_camera_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("sdk_camera_port must be in range 1..65535")
        return value


class CameraProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    sdk_camera_address: str | None = None
    sdk_camera_port: int | None = None
    sdk_camera_interface: int | None = None
    sdk_camera_index: int | None = None
    temperature_hardware_option: int | None = None
    readout_speed: int | None = None
    gain_mode: str | None = None

    @field_validator("readout_speed")
    @classmethod
    def validate_readout_speed(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in READOUT_SPEED_OPTIONS:
            raise ValueError(f"readout_speed must be one of {READOUT_SPEED_OPTIONS}")
        return value

    @field_validator("gain_mode")
    @classmethod
    def validate_gain_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in GAIN_MODE_OPTIONS:
            raise ValueError(f"gain_mode must be one of {GAIN_MODE_OPTIONS}")
        return value

    @field_validator("sdk_camera_port")
    @classmethod
    def validate_camera_port(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 65535:
            raise ValueError("sdk_camera_port must be in range 1..65535")
        return value


class ExposureStartRequest(BaseModel):
    duration_sec: float
    light: bool = True


class ExposureResponse(BaseModel):
    exposure_id: str
    state: str
    image_ready: bool
    percent: int = 0
    error: str | None = None


class RoiBinningRequest(BaseModel):
    bin_x: int = Field(default=1, ge=1)
    bin_y: int = Field(default=1, ge=1)
    num_x: int = Field(default=2048, ge=1)
    num_y: int = Field(default=2052, ge=1)
    start_x: int = Field(default=0, ge=0)
    start_y: int = Field(default=0, ge=0)


class LatestImageResponse(BaseModel):
    exposure_id: str
    width: int
    height: int
    pixel_type: str
    orientation: str
    bin_x: int
    bin_y: int
    sample_pixels: list[int]
    pixel_data_base64: str | None = None


class ImageMetadataResponse(BaseModel):
    exposure_id: str
    width: int
    height: int
    pixel_type: str
    orientation: str
    bin_x: int
    bin_y: int
    sample_pixels: list[int]
    ccd_temp_c: int
    target_temp_c: int
    readout_speed: int
    gain_mode: str


class ImageResizeRequest(BaseModel):
    width: int = Field(ge=1, le=8192)
    height: int = Field(ge=1, le=8192)


class ImageResizeResponse(BaseModel):
    exposure_id: str
    width: int
    height: int
    pixel_type: str
    orientation: str
    bin_x: int
    bin_y: int
    sample_pixels: list[int]
    pixel_data_base64: str


class FitsExportRequest(BaseModel):
    file_name: str | None = None


class FitsExportResponse(BaseModel):
    file_name: str
    file_path: str
    bytes_written: int
    exposure_id: str
    width: int
    height: int
    fits_bitpix: int = 32
    sensor_bit_depth: int = 16


class CoolerPowerRequest(BaseModel):
    cooler_on: bool
    cooler_power_percent: int | None = None


class TargetTemperatureRequest(BaseModel):
    target_temp_c: int


class CoolingStatusResponse(BaseModel):
    cooler_on: bool
    target_temp_c: int
    ccd_temp_c: int
    backside_temp_c: int
    cooler_power_percent: int


class WarmupStartRequest(BaseModel):
    target_temp_c: int = 0
    temp_step_c: int = 5
    power_step_percent: int = 10
    step_interval_sec: float = 0.5


class WarmupResponse(BaseModel):
    warmup_job_id: str
    state: str
    current_temp_c: int
    current_power_percent: int
    target_temp_c: int | None = None
    error: str | None = None


class CoolingControllerModeRequest(BaseModel):
    mode: str = Field(pattern="^(safe|balanced|fast)$")


class CoolingControllerStatusResponse(BaseModel):
    mode: str
    requested_target_temp_c: float
    control_target_temp_c: float
    integral_term: float
    cooler_power_percent: int
    running_warmup: bool
    last_alert: str | None = None


class CoolingTelemetryItem(BaseModel):
    timestamp: str
    mode: str
    requested_target_temp_c: float
    control_target_temp_c: float
    ccd_temp_c: float
    backside_temp_c: float
    cooler_power_percent: int
    alert: str | None = None


class CoolingTelemetryResponse(BaseModel):
    items: list[CoolingTelemetryItem]


class EventLogItem(BaseModel):
    id: int | None = None
    level: str
    source: str
    event_type: str
    message: str
    correlation_id: str | None = None
    created_at: str | None = None
    timestamp: str | None = None


class EventLogListResponse(BaseModel):
    items: list[EventLogItem]
