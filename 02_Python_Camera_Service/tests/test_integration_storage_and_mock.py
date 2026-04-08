import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_integration_mock_sdk_connect_expose_and_fetch_image():
    connect = client.post("/api/v1/camera/connect")
    assert connect.status_code == 200
    assert connect.json()["connected"] is True

    start = client.post("/api/v1/camera/exposures", json={"duration_sec": 0.2, "light": True})
    assert start.status_code == 200
    exposure_id = start.json()["exposure_id"]

    time.sleep(0.3)

    status = client.get(f"/api/v1/camera/exposures/{exposure_id}/status")
    assert status.status_code == 200
    assert status.json()["state"] == "completed"
    assert status.json()["image_ready"] is True
    assert status.json()["percent"] == 100

    latest = client.get("/api/v1/camera/images/latest")
    assert latest.status_code == 200
    assert latest.json()["exposure_id"] == exposure_id

    disconnect = client.post("/api/v1/camera/disconnect")
    assert disconnect.status_code == 200


def test_integration_local_storage_logs_endpoint_returns_items():
    client.get("/api/v1/health")
    client.post("/api/v1/camera/connect")
    client.post("/api/v1/camera/disconnect")

    logs = client.get("/api/v1/logs/events?limit=20")
    assert logs.status_code == 200
    payload = logs.json()
    assert "items" in payload
    assert len(payload["items"]) > 0
    assert any(item.get("event_type") == "camera_connected" for item in payload["items"])


def test_lifecycle_logging_for_exposure_and_warmup_completion():
    client.post("/api/v1/camera/connect")
    started = client.post("/api/v1/camera/exposures", json={"duration_sec": 0.1, "light": True}).json()
    exposure_id = started["exposure_id"]
    time.sleep(0.2)
    client.get(f"/api/v1/camera/exposures/{exposure_id}/status")

    warm_started = client.post(
        "/api/v1/camera/cooling/warmup",
        json={"target_temp_c": 0, "temp_step_c": 10, "power_step_percent": 50, "step_interval_sec": 0.1},
    ).json()
    time.sleep(0.4)
    client.get(f"/api/v1/camera/cooling/warmup/{warm_started['warmup_job_id']}/status")
    client.post("/api/v1/camera/disconnect")

    logs = client.get("/api/v1/logs/events?limit=100")
    assert logs.status_code == 200
    event_types = [item.get("event_type") for item in logs.json()["items"]]
    assert "exposure_completed" in event_types
    assert "warmup_completed" in event_types
