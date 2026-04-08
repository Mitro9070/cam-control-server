from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
from ctypes import byref, c_bool, c_char_p, c_int


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


SCENARIOS: list[dict] = [
    {
        "name": "cdll_baseline",
        "loader": "cdll",
        "calls": [],
    },
    {
        "name": "windll_baseline",
        "loader": "windll",
        "calls": [],
    },
    {
        "name": "cdll_connect_server_ip_port",
        "loader": "cdll",
        "calls": [
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 12345], "restype": "bool"},
        ],
    },
    {
        "name": "windll_connect_server_ip_port",
        "loader": "windll",
        "calls": [
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 12345], "restype": "bool"},
        ],
    },
    {
        "name": "windll_connect_server_ip_index0",
        "loader": "windll",
        "calls": [
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 0], "restype": "bool"},
        ],
    },
    {
        "name": "windll_single_server_ip_port_idx0",
        "loader": "windll",
        "calls": [
            {"fn": "ConnectToSingleCameraServer", "argtypes": ["str", "int", "int"], "args": ["ip", 12345, 0], "restype": "bool"},
        ],
    },
    {
        "name": "windll_single_server_ip_idx0_idx0",
        "loader": "windll",
        "calls": [
            {"fn": "ConnectToSingleCameraServer", "argtypes": ["str", "int", "int"], "args": ["ip", 0, 0], "restype": "bool"},
        ],
    },
    {
        "name": "windll_set_conn_type_3",
        "loader": "windll",
        "calls": [
            {"fn": "SetConnectionType", "argtypes": ["int"], "args": [3], "restype": "bool"},
        ],
    },
    {
        "name": "windll_setup_iface_3_0",
        "loader": "windll",
        "calls": [
            {"fn": "SetupCameraInterface", "argtypes": ["int", "int"], "args": [3, 0], "restype": "bool"},
        ],
    },
    {
        "name": "windll_set_conn_3_then_server",
        "loader": "windll",
        "calls": [
            {"fn": "SetConnectionType", "argtypes": ["int"], "args": [3], "restype": "bool"},
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 12345], "restype": "bool"},
        ],
    },
    {
        "name": "windll_setup_3_0_then_server",
        "loader": "windll",
        "calls": [
            {"fn": "SetupCameraInterface", "argtypes": ["int", "int"], "args": [3, 0], "restype": "bool"},
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 12345], "restype": "bool"},
        ],
    },
    {
        "name": "windll_setup_3_0_server_single",
        "loader": "windll",
        "calls": [
            {"fn": "SetupCameraInterface", "argtypes": ["int", "int"], "args": [3, 0], "restype": "bool"},
            {"fn": "ConnectToCameraServer", "argtypes": ["str", "int"], "args": ["ip", 12345], "restype": "bool"},
            {"fn": "ConnectToSingleCameraServer", "argtypes": ["str", "int", "int"], "args": ["ip", 12345, 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_init_camera_status_idx",
        "loader": "cdll",
        "calls": [
            {"fn": "InitCamera", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_check_camera_status_idx",
        "loader": "cdll",
        "calls": [
            {"fn": "CheckCamera", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_check_camera_pro_status_idx",
        "loader": "cdll",
        "calls": [
            {"fn": "CheckCameraPro", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_setup_iface_status_idx",
        "loader": "cdll",
        "calls": [
            {"fn": "SetupCameraInterface", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_setup_iface_3_idx0_init",
        "loader": "cdll",
        "calls": [
            {"fn": "SetupCameraInterface", "argtypes": ["int", "int"], "args": [3, 0], "restype": "bool"},
            {"fn": "InitCamera", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_check_camera_no_args",
        "loader": "cdll",
        "calls": [
            {"fn": "CheckCamera", "argtypes": [], "args": [], "restype": "bool"},
        ],
    },
    {
        "name": "cdll_init_camera_no_args",
        "loader": "cdll",
        "calls": [
            {"fn": "InitCamera", "argtypes": [], "args": [], "restype": "bool"},
        ],
    },
    {
        "name": "windll_init_camera_status_idx",
        "loader": "windll",
        "calls": [
            {"fn": "InitCamera", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
    {
        "name": "windll_check_camera_status_idx",
        "loader": "windll",
        "calls": [
            {"fn": "CheckCamera", "argtypes": ["ptr_int", "int"], "args": ["status_ptr", 0], "restype": "bool"},
        ],
    },
]


def _to_ctype_argtype(name: str):
    if name == "int":
        return c_int
    if name == "str":
        return c_char_p
    if name == "ptr_int":
        return ctypes.POINTER(c_int)
    raise ValueError(f"unsupported argtype {name}")


def _to_ctype_arg(value):
    if isinstance(value, str) and value == "ip":
        return c_char_p(args.camera_ip.encode("ascii", errors="ignore"))
    if isinstance(value, int):
        return c_int(value)
    if isinstance(value, str) and value == "status_ptr":
        return byref(c_int())
    raise ValueError(f"unsupported arg {value!r}")


def _run_child(dll_path: str, scenario_name: str, camera_index: int):
    scenario = next((item for item in SCENARIOS if item["name"] == scenario_name), None)
    if scenario is None:
        return {"scenario": scenario_name, "error": "scenario_not_found"}

    try:
        if scenario["loader"] == "windll":
            lib = ctypes.WinDLL(dll_path)
        else:
            lib = ctypes.CDLL(dll_path)
    except Exception as exc:
        return {"scenario": scenario_name, "error": f"dll_load_failed: {exc!r}"}

    call_results = []
    for call in scenario["calls"]:
        fn_name = call["fn"]
        fn = getattr(lib, fn_name, None)
        if fn is None:
            call_results.append({"fn": fn_name, "result": "missing"})
            continue
        try:
            fn.argtypes = [_to_ctype_argtype(name) for name in call["argtypes"]]
            if call.get("restype") == "bool":
                fn.restype = c_bool
            args_casted = [_to_ctype_arg(arg) for arg in call["args"]]
            value = fn(*args_casted)
            call_results.append({"fn": fn_name, "result": "ok", "return": bool(value) if isinstance(value, bool) else int(value)})
        except Exception as exc:
            call_results.append({"fn": fn_name, "result": "exception", "error": repr(exc)})

    connect = getattr(lib, "ConnectCamera", None)
    if connect is None:
        return {"scenario": scenario_name, "calls": call_results, "error": "connect_camera_missing"}

    try:
        connect.argtypes = [ctypes.POINTER(c_int), ctypes.POINTER(c_char_p), ctypes.POINTER(c_int), c_int]
        connect.restype = c_bool
        model_id = c_int()
        model_str = c_char_p()
        status = c_int()
        ok = bool(connect(byref(model_id), byref(model_str), byref(status), c_int(camera_index)))
        name = model_str.value.decode("utf-8", errors="ignore") if model_str.value else None
        return {
            "scenario": scenario_name,
            "loader": scenario["loader"],
            "calls": call_results,
            "connect_ok": ok,
            "connect_status": status.value,
            "connect_status_message": STATUS_MESSAGES.get(status.value, "unknown status"),
            "model_id": model_id.value,
            "model_name": name,
        }
    except Exception as exc:
        return {"scenario": scenario_name, "loader": scenario["loader"], "calls": call_results, "error": f"connect_exception: {exc!r}"}


def _run_parent(dll_path: str, camera_index: int, timeout_sec: int):
    summary = []
    for scenario in SCENARIOS:
        proc = subprocess.run(
            [
                sys.executable,
                __file__,
                "--child",
                "--dll-path",
                dll_path,
                "--scenario",
                scenario["name"],
                "--camera-index",
                str(camera_index),
                "--camera-ip",
                args.camera_ip,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if proc.returncode != 0:
            summary.append({"scenario": scenario["name"], "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()})
            continue
        raw = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        try:
            summary.append(json.loads(raw))
        except json.JSONDecodeError:
            summary.append({"scenario": scenario["name"], "error": "bad_json_output", "raw": raw})
    print(json.dumps({"camera_ip": args.camera_ip, "camera_index": camera_index, "results": summary}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll-path", required=True)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--camera-ip", default="192.168.31.234")
    parser.add_argument("--timeout-sec", type=int, default=10)
    parser.add_argument("--scenario", default="")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()

    if args.child:
        result = _run_child(args.dll_path, args.scenario, args.camera_index)
        print(json.dumps(result, ensure_ascii=False))
    else:
        _run_parent(args.dll_path, args.camera_index, args.timeout_sec)
