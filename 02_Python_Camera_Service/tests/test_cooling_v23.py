"""Regression tests for cooling v2.4 (Замечания4: target jump-back, PI sign, connect reset, cooler-off override).

Scenarios from production (Zvenigorod):
  1. Set target=5  ->  camera cools to 5, overshoots to 1, stabilises ~5-7
  2. Set target=-7 from MaxIm DL (ASCOM)  ->  target shows -7 for 2 sec then jumps back to 5
  3. cooler_power_percent shows 0% while actively cooling (PI sign inverted)
  4. connect() resets target to 20 every time MaxIm DL reconnects
  5. set_target_temperature forces cooler_on=True, overriding manual cooler-off
  6. set_cooler_power(True) doesn't send target to SDK immediately
  7. stale control_target above SDK max keeps power=0 and blocks cooling
"""
from __future__ import annotations

import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.camera_runtime import RUNTIME_VERSION, camera_runtime
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _connect_and_cool(client: TestClient, target: int) -> dict:
    client.post("/api/v1/camera/connect")
    client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
    r = client.put("/api/v1/camera/cooling/target", json={"target_temp_c": target})
    assert r.status_code == 200
    return r.json()


class TestRuntimeVersion:
    def test_version_is_2_4(self):
        assert RUNTIME_VERSION == "2.4"

    def test_debug_endpoint_returns_version(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        r = client.get("/api/v1/camera/cooling/debug")
        assert r.status_code == 200
        data = r.json()
        assert data["runtime_version"] == "2.4"
        client.post("/api/v1/camera/disconnect")


class TestConnectPreservesCoolingState:
    """BUG: connect() used to reset target_temp_c=20 every time MaxIm DL connects."""

    def test_second_connect_preserves_target(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -10})

        # Simulate MaxIm DL reconnecting (new COM object -> POST /camera/connect)
        r2 = client.post("/api/v1/camera/connect")
        assert r2.status_code == 200

        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["target_temp_c"] == -10, f"target was reset by second connect! {s}"
        assert s["cooler_on"] is True, f"cooler_on was reset by second connect! {s}"
        client.post("/api/v1/camera/disconnect")

    def test_second_connect_preserves_cooler_on(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 5})
        time.sleep(1.0)

        client.post("/api/v1/camera/connect")  # MaxIm DL reconnect
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["state.cooler_on"] is True
        assert dbg["state.target_temp_c"] == 5
        assert dbg["requested_target_temp_c"] == 5.0
        client.post("/api/v1/camera/disconnect")

    def test_connect_after_disconnect_does_reset(self, client: TestClient):
        """After explicit disconnect, connect must reinitialise normally."""
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -15})
        client.post("/api/v1/camera/disconnect")

        client.post("/api/v1/camera/connect")
        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["target_temp_c"] == 20, "fresh connect should start at 20"
        assert s["cooler_on"] is False
        client.post("/api/v1/camera/disconnect")


class TestTargetNeverJumpsBack:
    """Core bug: operator sets target=-7 but after ~2 s the API reports 5 again."""

    def test_target_stable_after_set(self, client: TestClient):
        _connect_and_cool(client, 5)
        time.sleep(2.5)

        r = client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -7})
        assert r.json()["target_temp_c"] == -7

        for _ in range(5):
            time.sleep(1.0)
            s = client.get("/api/v1/camera/cooling/status").json()
            assert s["target_temp_c"] == -7, f"target jumped back! status={s}"

        client.post("/api/v1/camera/disconnect")

    def test_rapid_target_changes(self, client: TestClient):
        _connect_and_cool(client, 10)
        targets = [5, 0, -5, -10, -15, -7]
        for t in targets:
            client.put("/api/v1/camera/cooling/target", json={"target_temp_c": t})
            time.sleep(0.1)

        time.sleep(3.0)
        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["target_temp_c"] == -7, f"target should be -7, got {s}"
        client.post("/api/v1/camera/disconnect")

    def test_debug_shows_consistent_state(self, client: TestClient):
        _connect_and_cool(client, -12)
        time.sleep(0.5)
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["state.target_temp_c"] == -12
        assert dbg["requested_target_temp_c"] == -12.0
        assert dbg["control_target_temp_c"] == -12.0
        assert dbg["last_applied_target_temp"] == -12
        client.post("/api/v1/camera/disconnect")


class TestCoolerOnOff:
    """BUG: unchecking cooler_on in UI had no effect because set_target_temperature
    forced cooler_on=True."""

    def test_cooler_off_stays_off(self, client: TestClient):
        _connect_and_cool(client, -5)
        time.sleep(0.5)

        off = client.put("/api/v1/camera/cooling/power", json={"cooler_on": False})
        assert off.json()["cooler_on"] is False
        assert off.json()["target_temp_c"] == -5

        # Status must also show cooler_on=False
        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["cooler_on"] is False
        assert s["cooler_power_percent"] == 0
        assert s["target_temp_c"] == -5
        client.post("/api/v1/camera/disconnect")

    def test_set_target_does_not_turn_cooler_on(self, client: TestClient):
        """Setting target while cooler is off must NOT re-enable it."""
        client.post("/api/v1/camera/connect")
        # Cooler is OFF by default after first connect
        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["cooler_on"] is False

        # Set target while cooler is off
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -10})
        s2 = client.get("/api/v1/camera/cooling/status").json()
        assert s2["cooler_on"] is False, f"set_target_temperature turned cooler on! {s2}"
        assert s2["target_temp_c"] == -10, "target should be stored even with cooler off"
        client.post("/api/v1/camera/disconnect")

    def test_cooler_off_then_on_uses_stored_target(self, client: TestClient):
        """Turn cooler off, set a new target, turn cooler on -- new target must be used."""
        _connect_and_cool(client, 5)
        time.sleep(0.5)

        client.put("/api/v1/camera/cooling/power", json={"cooler_on": False})
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -10})

        on = client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        assert on.json()["cooler_on"] is True

        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["state.target_temp_c"] == -10
        assert dbg["last_applied_target_temp"] == -10, "SDK should have received -10 on cooler-on"
        client.post("/api/v1/camera/disconnect")

    def test_cooler_off_is_not_overridden_by_status_poll(self, client: TestClient):
        """After cooler off, repeated status polls must NOT flip cooler back on."""
        _connect_and_cool(client, -5)
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": False})

        for _ in range(5):
            s = client.get("/api/v1/camera/cooling/status").json()
            assert s["cooler_on"] is False, f"status poll flipped cooler on! {s}"
            assert s["target_temp_c"] == -5, f"cooler_off rewrote target to CCD! {s}"
            time.sleep(0.5)

        client.post("/api/v1/camera/disconnect")

    def test_cooler_off_preserves_operator_target(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 5})
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        off = client.put("/api/v1/camera/cooling/power", json={"cooler_on": False})
        assert off.status_code == 200
        assert off.json()["target_temp_c"] == 5
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["state.target_temp_c"] == 5
        assert dbg["requested_target_temp_c"] == 5.0
        assert dbg["control_target_temp_c"] == 5.0
        client.post("/api/v1/camera/disconnect")


class TestPIControllerSign:
    """cooler_power_percent must be >0 when CCD is warmer than target."""

    def test_power_positive_while_cooling(self, client: TestClient):
        _connect_and_cool(client, -10)
        time.sleep(3.0)
        s = client.get("/api/v1/camera/cooling/status").json()
        if s["ccd_temp_c"] > s["target_temp_c"]:
            assert s["cooler_power_percent"] > 0, (
                f"PI sign wrong: CCD={s['ccd_temp_c']} > target={s['target_temp_c']} "
                f"but power={s['cooler_power_percent']}"
            )
        client.post("/api/v1/camera/disconnect")

    def test_power_zero_when_ccd_at_or_below_target(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 25})
        time.sleep(3.0)
        s = client.get("/api/v1/camera/cooling/status").json()
        assert s["cooler_power_percent"] == 0, (
            f"Power should be 0 when target ({s['target_temp_c']}) >= CCD ({s['ccd_temp_c']})"
        )
        client.post("/api/v1/camera/disconnect")


class TestCoolerPowerSdkSync:
    """set_cooler_power(True) must send target to SDK immediately."""

    def test_cooler_on_sends_target_to_sdk(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -8})

        on = client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        assert on.json()["cooler_on"] is True

        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["last_applied_target_temp"] == -8, (
            f"SDK should have received -8 immediately: {dbg}"
        )
        client.post("/api/v1/camera/disconnect")

    def test_explicit_power_seeds_integral(self, client: TestClient):
        """When cooler_power_percent=70 is explicitly set, integral should start near 70."""
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -15})
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 70})
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["integral_term"] == 70.0, f"integral should be seeded to 70: {dbg}"
        client.post("/api/v1/camera/disconnect")

    def test_cooler_on_snaps_stale_control_target_to_requested(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        runtime = camera_runtime
        with runtime._lock:  # noqa: SLF001 - regression setup for stale off-state controller
            runtime._requested_target_temp_c = 10.0
            runtime._state.target_temp_c = 10
            runtime._control_target_temp_c = 21.438
            runtime._state.ccd_temp_c = 10
            runtime._last_applied_target_temp = None

        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True})
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["control_target_temp_c"] == 10.0, dbg
        assert dbg["last_applied_target_temp"] == 10, dbg
        client.post("/api/v1/camera/disconnect")

    def test_apply_target_range_error_recovers_to_requested_target(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        runtime = camera_runtime
        with runtime._lock:  # noqa: SLF001 - controlled regression setup
            runtime._state.cooler_on = True
            runtime._requested_target_temp_c = 10.0
            runtime._state.target_temp_c = 10
            runtime._control_target_temp_c = 21.438
            runtime._state.ccd_temp_c = 10
            runtime._last_applied_target_temp = None
            runtime._last_control_apply_at = 0.0

        time.sleep(2.2)
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["last_applied_target_temp"] == 10, dbg
        assert dbg["control_target_temp_c"] == 10.0, dbg
        assert dbg["state.cooler_power_percent"] == 0, dbg
        client.post("/api/v1/camera/disconnect")


class TestControlLoopDoesNotOverrideSDK:
    def test_control_target_snapped(self, client: TestClient):
        _connect_and_cool(client, 5)
        time.sleep(2.0)

        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -7})
        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["control_target_temp_c"] == -7.0, f"control target not snapped: {dbg}"
        assert dbg["last_applied_target_temp"] == -7
        client.post("/api/v1/camera/disconnect")

    def test_control_loop_does_not_revert_sdk_target(self, client: TestClient):
        _connect_and_cool(client, 5)
        time.sleep(2.0)

        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": -7})
        time.sleep(4.0)

        dbg = client.get("/api/v1/camera/cooling/debug").json()
        assert dbg["last_applied_target_temp"] == -7, f"control loop reverted SDK target: {dbg}"
        assert dbg["state.target_temp_c"] == -7
        assert dbg["requested_target_temp_c"] == -7.0
        client.post("/api/v1/camera/disconnect")


class TestWarmupBehavior:
    def test_warmup_completion_keeps_regulation_enabled(self, client: TestClient):
        client.post("/api/v1/camera/connect")
        client.put("/api/v1/camera/cooling/target", json={"target_temp_c": 2})
        client.put("/api/v1/camera/cooling/power", json={"cooler_on": True, "cooler_power_percent": 20})
        start = client.post(
            "/api/v1/camera/cooling/warmup",
            json={"target_temp_c": 2, "temp_step_c": 5, "power_step_percent": 10, "step_interval_sec": 0.1},
        )
        assert start.status_code == 200
        warmup_id = start.json()["warmup_job_id"]

        status_payload = None
        for _ in range(50):
            time.sleep(0.1)
            status_payload = client.get(f"/api/v1/camera/cooling/warmup/{warmup_id}/status").json()
            if status_payload["state"] == "completed":
                break
        assert status_payload is not None
        assert status_payload["state"] == "completed", status_payload
        assert status_payload["target_temp_c"] == 2, status_payload

        st = client.get("/api/v1/camera/cooling/status").json()
        assert st["cooler_on"] is True, st
        assert st["target_temp_c"] == 2, st
        ctrl = client.get("/api/v1/camera/cooling/controller/status").json()
        assert ctrl["mode"] == "balanced", ctrl
        client.post("/api/v1/camera/disconnect")


class TestLogging:
    def test_set_target_logs_version(self, client: TestClient, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO, logger="camera-service.runtime")
        _connect_and_cool(client, -5)
        msgs = [r.message for r in caplog.records if r.name == "camera-service.runtime"]
        assert any("COOLING_TRACE" in m and "'reason': 'set_target'" in m and "'v': '2.4'" in m for m in msgs), msgs
        client.post("/api/v1/camera/disconnect")

    def test_connect_logs_version(self, client: TestClient, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO, logger="camera-service.runtime")
        client.post("/api/v1/camera/connect")
        msgs = [r.message for r in caplog.records if r.name == "camera-service.runtime"]
        assert any("CONNECT" in m and "2.4" in m for m in msgs), msgs
        client.post("/api/v1/camera/disconnect")
