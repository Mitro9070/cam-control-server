"""Regression tests for cooling / warmup (Замечания3: stable target in API/UI, cooler off)."""

from __future__ import annotations

import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_operator_target_not_overwritten_by_controller_loop(client: TestClient):
    """API target_temp_c must stay the operator setpoint, not ramp intermediates."""
    client.post("/api/v1/camera/connect")
    client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 50})
    client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -10})
    time.sleep(2.6)
    s = client.get("/api/v1/camera/cooling/status").json()
    assert s["target_temp_c"] == -10, s

    client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 5})
    s2 = client.get("/api/v1/camera/cooling/status").json()
    assert s2["target_temp_c"] == 5, s2

    time.sleep(3.0)
    s3 = client.get("/api/v1/camera/cooling/status").json()
    assert s3["target_temp_c"] == 5, s3

    client.post("/api/v1/camera/disconnect")


def test_warm_target_while_cooler_already_on(client: TestClient):
    """Changing setpoint while cooler is on must apply new target immediately (no stale control_target)."""
    client.post("/api/v1/camera/connect")
    client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 60})
    client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -15})
    time.sleep(0.2)
    r = client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 0})
    assert r.status_code == 200
    assert r.json()["target_temp_c"] == 0
    client.post("/api/v1/camera/disconnect")


def test_cooler_off_reflected_in_status(client: TestClient):
    client.post("/api/v1/camera/connect")
    client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 40})
    client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -10})
    off = client.put("/api/v1/camera/cooling/power", json={"cooler_on": False})
    assert off.status_code == 200
    assert off.json()["cooler_on"] is False
    st = client.get("/api/v1/camera/cooling/status").json()
    assert st["cooler_on"] is False
    assert st["cooler_power_percent"] == 0
    client.post("/api/v1/camera/disconnect")


def test_cooling_runtime_logs_on_set_target(client: TestClient, caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="camera-service.runtime")
    client.post("/api/v1/camera/connect")
    client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 30})
    client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -5})
    msgs = [r.message for r in caplog.records if r.name == "camera-service.runtime"]
    assert any("COOLING_TRACE" in m and "'reason': 'set_target'" in m for m in msgs), msgs
    client.post("/api/v1/camera/disconnect")
