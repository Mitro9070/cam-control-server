from pydantic_settings import BaseSettings, SettingsConfigDict


READOUT_SPEED_OPTIONS = (50, 100, 250, 500, 1000, 3000, 5000)
GAIN_MODE_OPTIONS = ("0", "1")
FITS_EXPORT_BITPIX_OPTIONS = (16, 32)


class Settings(BaseSettings):
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 3037
    log_level: str = "INFO"

    storage_mode: str = "postgres"
    local_storage_path: str = "./.local_storage"

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_username: str = "postgres"
    db_password: str = "postgres"
    db_database: str = "astro_camera"
    db_sslmode: str = "prefer"

    sdk_mode: str = "native"
    sdk_dll_path: str = ""
    sdk_camera_address: str = ""
    sdk_camera_interface: int = -1
    sdk_camera_port: int = 12345
    sdk_readout_speed: int = 1000
    sdk_sensor_output_mode: int = 0
    sdk_bit_depth: int = 2
    sdk_busy_timeout_ms: int = 3000
    camera_index: int = 0
    camera_has_shutter: bool = True
    cooling_hardware_option: int = 42223
    fits_export_bitpix: int = 32

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
            f"?sslmode={self.db_sslmode}"
        )


settings = Settings()
