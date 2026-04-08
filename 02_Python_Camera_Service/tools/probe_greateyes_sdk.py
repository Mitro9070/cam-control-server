from __future__ import annotations

import argparse
import ctypes
import json
import os
from ctypes import byref, c_bool, c_char_p, c_int
from dataclasses import asdict, dataclass


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
class ProbeResult:
    index: int
    ok: bool
    status: int
    status_message: str
    model_id: int
    model_name: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe greateyes SDK ConnectCamera results.")
    parser.add_argument("--dll-path", required=True, help="Path to greateyes.dll")
    parser.add_argument("--max-index", type=int, default=3, help="Max camera index to test")
    return parser.parse_args()


def run_probe(dll_path: str, max_index: int) -> list[ProbeResult]:
    os.add_dll_directory(os.path.dirname(dll_path))
    lib = ctypes.CDLL(dll_path)
    lib.ConnectCamera.argtypes = [ctypes.POINTER(c_int), ctypes.POINTER(c_char_p), ctypes.POINTER(c_int), c_int]
    lib.ConnectCamera.restype = c_bool
    lib.DisconnectCamera.argtypes = [ctypes.POINTER(c_int), c_int]
    lib.DisconnectCamera.restype = c_bool

    results: list[ProbeResult] = []
    for camera_index in range(0, max_index + 1):
        model_id = c_int()
        model_str = c_char_p()
        status = c_int()
        ok = bool(lib.ConnectCamera(byref(model_id), byref(model_str), byref(status), camera_index))
        model_name = model_str.value.decode("utf-8", errors="ignore") if model_str.value else None
        results.append(
            ProbeResult(
                index=camera_index,
                ok=ok,
                status=status.value,
                status_message=STATUS_MESSAGES.get(status.value, "unknown status"),
                model_id=model_id.value,
                model_name=model_name,
            )
        )
        if ok:
            disconnect_status = c_int()
            lib.DisconnectCamera(byref(disconnect_status), camera_index)
    return results


def main() -> None:
    args = parse_args()
    results = run_probe(args.dll_path, args.max_index)
    payload = {"dll_path": args.dll_path, "results": [asdict(item) for item in results]}
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
