#!/usr/bin/env python3
"""Source-pinned reset/fault extension for the unchanged W19 compact adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ADAPTER = "rtl/gpu/ot_gpu_payload_assemble.sv"
BENCH = "rtl/test/tb_w19_payload_reset_fault.sv"
PREFLIGHT = "results/uarch/w19_payload_current_preflight_20261001.json"
ADAPTER_SHA = "355f01e90ccba32fca58339ea65d0b0bc87b906b7fe9b59d57eb6fc04636baa4"
CASES = (
    "reset_partial_record_tag_reuse", "reset_stalled_response",
    "reset_full_tag_credits", "finite_sector_window_backpressure",
    "sector_out_of_descriptor", "duplicate_consumed_sector",
    "duplicate_simultaneous_sector", "stale_epoch_after_reset",
    "duplicate_live_request_tag", "request_ordinal_skip",
    "zero_length_descriptor", "reset_partial_line_bridge",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work, record_path = args.work.resolve(), args.record.resolve()
    if record_path.exists() or work.exists():
        parser.error("use fresh work and record paths; retained verdicts are immutable")
    if work.is_relative_to(root) or record_path.is_relative_to(root):
        parser.error("run outside the pinned source worktree")
    # Reject untracked source too, so the recorded commit reconstructs this gate.
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
    if status:
        parser.error("commit source first; gate requires a clean pinned worktree")
    pin = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    paths = (ADAPTER, BENCH, PREFLIGHT, "tools/w19_payload_reset_fault_gate.py")
    hashes = {p: digest(root / p) for p in paths}
    record = {
        "schema": "opentallas.w19.payload_reset_fault.v1",
        "status": "fail", "source_commit": pin, "source_sha256": hashes,
        "adapter_original_source": "3b15b18e997ad0a05cc7acf474a7329847e38845",
        "scope": "unchanged production 136-byte sector/tag adapter; protocol verification only",
        "expected_cases": list(CASES), "passed_cases": [],
        "enabled_default": False,
        "model_currency": "retained preflight only; combined unified-model refresh is parent-owned and pending",
        "adoption": {
            "enabled": False,
            "measured_gain": "FAIL retained: compact 240 versus padded 233 cycles for two historical slices; not token rate",
            "in_context_SS_FF": "pending",
            "hub_routing_layer_check": "pending",
            "model_single_user_gain_at_least_1_percent": "pending",
        },
        "limitations": [
            "Synthetic byte oracle verifies all 128 weight and eight exponent bytes; no fresh checkpoint golden run.",
            "Historical 60-case arithmetic evidence is not promoted to this source commit or current main.",
            "No new hardware, physical stream, timing closure, full-rank token, or cycle-rate claim.",
            "W13 hardening and Qwen composition remain with their existing owners.",
        ],
    }
    work.mkdir(parents=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)

    def run(command, name):
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=60)
        (work / (name + ".stdout")).write_text(result.stdout)
        (work / (name + ".stderr")).write_text(result.stderr)
        record.setdefault("commands", []).append({
            "argv": command, "exit_code": result.returncode,
            "stdout_sha256": digest(work / (name + ".stdout")),
            "stderr_sha256": digest(work / (name + ".stderr")),
        })
        if result.returncode:
            raise RuntimeError(f"{name} exited {result.returncode}")
        return result.stdout

    try:
        if hashes[ADAPTER] != ADAPTER_SHA:
            raise RuntimeError("adapter differs from retained production source")
        model = json.loads((root / PREFLIGHT).read_text())
        expected = {"enabled_default": False, "sector_window": 16,
                    "tag_depth": 16, "reservoir_bytes": 512, "replicas_per_die": 32}
        for key, value in expected.items():
            if model[key] != value:
                raise RuntimeError(f"preflight mismatch: {key}")
        if model["ports_Bpc"]["fetch_read"] != 128 or model["ports_Bpc"]["sm_response_write"] != 136:
            raise RuntimeError("preflight payload port mismatch")
        record["preflight_parameters"] = expected
        record["simulator_version"] = run(["iverilog", "-V"], "version").splitlines()[0]
        executable = str(work / "gate.vvp")
        run(["iverilog", "-g2012", "-s", "tb_w19_payload_reset_fault",
             "-o", executable, ADAPTER, BENCH], "compile")
        output = run(["vvp", executable], "simulate")
        passed = re.findall(r"^CASE (\w+) PASS$", output, re.MULTILINE)
        record["passed_cases"] = passed
        if passed != list(CASES) or "RESET_FAULT PASS cases=12 default_off=1 tightly_packed_bytes=136" not in output.splitlines():
            raise RuntimeError("missing, duplicate, or unexpected case receipts")
        record["status"] = "pass"
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)
    # Exclusive create preserves prior failures even if another process races us.
    with record_path.open("x") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"{record['status'].upper()}: {len(record['passed_cases'])}/{len(CASES)} reset/fault cases; {record_path}")
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
