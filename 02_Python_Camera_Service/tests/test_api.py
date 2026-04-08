import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_settings_roundtrip():
    get_response = client.get("/api/v1/settings")
    assert get_response.status_code == 200
    assert get_response.json()["sensor_name_override"] == "GreatEyes 9.0"
    assert get_response.json().get("fits_export_bitpix") == 32

    put_response = client.put(
        "/api/v1/settings",
        json={"readout_speed": 1000, "has_shutter": True},
    )
    assert put_response.status_code == 200
    assert put_response.json()["readout_speed"] == 1000


def test_settings_validation_readout_speed():
    bad = client.put("/api/v1/settings", json={"readout_speed": 777})
    assert bad.status_code == 422


def test_settings_validation_fits_export_bitpix():
    bad = client.put("/api/v1/settings", json={"fits_export_bitpix": 8})
    assert bad.status_code == 422


def test_camera_profiles_crud_and_activate():
    create = client.post(
        "/api/v1/camera/profiles",
        json={
            "name": "scope-a",
            "sdk_camera_address": "192.168.31.234",
            "sdk_camera_port": 12345,
            "sdk_camera_interface": 3,
            "sdk_camera_index": 0,
            "temperature_hardware_option": 42223,
            "readout_speed": 1000,
            "gain_mode": "1",
        },
    )
    assert create.status_code == 200
    profile = create.json()
    assert profile["name"] == "scope-a"

    list_resp = client.get("/api/v1/camera/profiles")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 1

    update = client.put(
        f"/api/v1/camera/profiles/{profile['profile_id']}",
        json={"readout_speed": 500, "gain_mode": "0"},
    )
    assert update.status_code == 200
    assert update.json()["readout_speed"] == 500
    assert update.json()["gain_mode"] == "0"

    activate = client.post(f"/api/v1/camera/profiles/{profile['profile_id']}/activate")
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True


def test_connect_capabilities_disconnect():
    connect_response = client.post("/api/v1/camera/connect")
    assert connect_response.status_code == 200
    assert connect_response.json()["connected"] is True

    state_response = client.get("/api/v1/camera/state")
    assert state_response.status_code == 200
    assert state_response.json()["camera_state"] == "idle"

    caps_response = client.get("/api/v1/camera/capabilities")
    assert caps_response.status_code == 200
    assert caps_response.json()["camera_x_size"] == 2048

    disconnect_response = client.post("/api/v1/camera/disconnect")
    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["connected"] is False


def test_exposure_flow():
    client.post("/api/v1/camera/connect")

    roi_response = client.put(
        "/api/v1/camera/config/roi-binning",
        json={"bin_x": 1, "bin_y": 1, "num_x": 128, "num_y": 128, "start_x": 0, "start_y": 0},
    )
    assert roi_response.status_code == 200

    start_response = client.post("/api/v1/camera/exposures", json={"duration_sec": 0.1, "light": True})
    assert start_response.status_code == 200
    exposure_id = start_response.json()["exposure_id"]

    time.sleep(0.2)

    status_response = client.get(f"/api/v1/camera/exposures/{exposure_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "completed"
    assert status_response.json()["image_ready"] is True
    assert status_response.json()["percent"] == 100

    image_response = client.get("/api/v1/camera/images/latest")
    assert image_response.status_code == 200
    payload = image_response.json()
    assert payload["width"] == 128
    assert payload["height"] == 128
    assert payload["pixel_data_base64"]

    raw_image = client.get("/api/v1/camera/images/latest/raw")
    assert raw_image.status_code == 200
    assert raw_image.headers["x-width"] == "128"
    assert len(raw_image.content) == 128 * 128 * 2

    metadata = client.get("/api/v1/camera/images/latest/metadata")
    assert metadata.status_code == 200
    assert metadata.json()["width"] == 128
    assert metadata.json()["height"] == 128

    resized = client.post("/api/v1/camera/images/latest/resize", json={"width": 64, "height": 64})
    assert resized.status_code == 200
    resized_payload = resized.json()
    assert resized_payload["width"] == 64
    assert resized_payload["height"] == 64
    assert resized_payload["pixel_data_base64"]

    fits_export = client.post("/api/v1/camera/images/latest/export/fits", json={"file_name": "pytest_export.fits"})
    assert fits_export.status_code == 200
    fits_payload = fits_export.json()
    assert fits_payload["file_name"].lower().endswith(".fits")
    assert fits_payload["bytes_written"] > 0
    assert fits_payload.get("fits_bitpix") == 32
    assert fits_payload.get("sensor_bit_depth") == 16

    hdr = Path(fits_payload["file_path"]).read_bytes()[:2880]
    assert b"BITPIX" in hdr
    assert b"BITPIX  =                   32" in hdr or b"BITPIX  = 32" in hdr

    client.post("/api/v1/camera/disconnect")


def test_abort_exposure():
    client.post("/api/v1/camera/connect")
    start_response = client.post("/api/v1/camera/exposures", json={"duration_sec": 1.0, "light": True})
    exposure_id = start_response.json()["exposure_id"]
    abort_response = client.post(f"/api/v1/camera/exposures/{exposure_id}/abort")
    assert abort_response.status_code == 200
    assert abort_response.json()["state"] == "aborted"
    client.post("/api/v1/camera/disconnect")


def test_cooling_and_warmup_flow():
    client.post("/api/v1/camera/connect")

    power_on = client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 80})
    assert power_on.status_code == 200
    assert power_on.json()["cooler_on"] is True
    assert power_on.json()["cooler_power_percent"] == 80

    set_target = client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -20})
    assert set_target.status_code == 200
    assert set_target.json()["target_temp_c"] == -20

    status = client.get("/api/v1/camera/cooling/status")
    assert status.status_code == 200
    assert "ccd_temp_c" in status.json()

    controller_status = client.get("/api/v1/camera/cooling/controller/status")
    assert controller_status.status_code == 200
    assert controller_status.json()["mode"] in {"safe", "balanced", "fast"}

    controller_mode = client.put("/api/v1/camera/cooling/controller/mode", json={"mode": "safe"})
    assert controller_mode.status_code == 200
    assert controller_mode.json()["mode"] == "safe"

    warmup = client.post(
        "/api/v1/camera/cooling/warmup",
        json={
            "target_temp_c": 0,
            "temp_step_c": 10,
            "power_step_percent": 50,
            "step_interval_sec": 0.1,
        },
    )
    assert warmup.status_code == 200
    warmup_id = warmup.json()["warmup_job_id"]

    time.sleep(0.4)
    warmup_status = client.get(f"/api/v1/camera/cooling/warmup/{warmup_id}/status")
    assert warmup_status.status_code == 200
    assert warmup_status.json()["state"] in {"running", "completed"}

    final_status = client.get("/api/v1/camera/cooling/status")
    assert final_status.status_code == 200
    assert "cooler_power_percent" in final_status.json()

    telemetry = client.get("/api/v1/camera/cooling/telemetry?limit=20")
    assert telemetry.status_code == 200
    assert isinstance(telemetry.json()["items"], list)

    client.post("/api/v1/camera/disconnect")


def test_roi_binning_validation():
    client.post("/api/v1/camera/connect")
    bad = client.put(
        "/api/v1/camera/config/roi-binning",
        json={"bin_x": 0, "bin_y": 1, "num_x": 128, "num_y": 128, "start_x": 0, "start_y": 0},
    )
    assert bad.status_code == 422

    out_of_bounds = client.put(
        "/api/v1/camera/config/roi-binning",
        json={"bin_x": 1, "bin_y": 1, "num_x": 5000, "num_y": 128, "start_x": 0, "start_y": 0},
    )
    assert out_of_bounds.status_code == 400

    client.post("/api/v1/camera/disconnect")
