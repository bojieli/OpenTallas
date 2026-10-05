#!/usr/bin/env python3
"""Source-pinned concurrent two-user V4.1 index/KV arbiter comparison.

This isolates K-port arbitration from HBM DRAM timing; the die's W port is a
separate behavioural model and is deliberately outside the measurement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/chip/ot_chip_v41x_hbm_rsp_pipe.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb.sv",
    "rtl/test/tb_chip_v41x_hbm_arb_concurrent.sv",
]
PATTERN = re.compile(
    r"PASS pipe=(\d+) cycles=(\d+) b_done=(\d+) k_done=(\d+) "
    r"b_lat_sum=(\d+) k_lat_sum=(\d+) b_max=(\d+) k_max=(\d+) "
    r"b_u0=(\d+) b_u1=(\d+) k_u0=(\d+) k_u1=(\d+) "
    r"bg=(\d+) kg=(\d+) cont=(\d+)"
)
FIELDS = ("pipe", "cycles", "index_responses", "kv_responses", "index_latency_sum_cycles",
          "kv_latency_sum_cycles", "index_latency_max_cycles", "kv_latency_max_cycles",
          "index_user0", "index_user1", "kv_user0", "kv_user1", "index_grants",
          "kv_grants", "contended_cycles")


def run(pipe: bool, out: Path) -> dict:
    exe = out / ("pipe.out" if pipe else "direct.out")
    cmd = ["iverilog", "-g2012", *( ["-DHDC_KARB_PIPE"] if pipe else []),
           "-s", "tb_chip_v41x_hbm_arb_concurrent", "-o", str(exe), *SOURCES]
    b = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    s = subprocess.run(["vvp", str(exe)], cwd=ROOT, text=True, capture_output=True, check=True)
    m = PATTERN.search(s.stdout)
    if not m:
        raise RuntimeError(f"no exact completion: {s.stdout[-1000:]} {s.stderr[-1000:]}")
    d = dict(zip(FIELDS, (int(v) for v in m.groups())))
    if d["index_responses"] != 8192 or d["kv_responses"] != 2048 or any(
        d[k] != n for k, n in (("index_user0", 4096), ("index_user1", 4096),
                             ("kv_user0", 1024), ("kv_user1", 1024))
    ):
        raise RuntimeError(f"wrong completed traffic: {d}")
    d["index_mean_latency_cycles"] = d["index_latency_sum_cycles"] / d["index_responses"]
    d["kv_mean_latency_cycles"] = d["kv_latency_sum_cycles"] / d["kv_responses"]
    d["index_responses_per_cycle"] = d["index_responses"] / d["cycles"]
    d["kv_responses_per_cycle"] = d["kv_responses"] / d["cycles"]
    d["log_sha256"] = hashlib.sha256(s.stdout.encode()).hexdigest()
    d["build_stderr_sha256"] = hashlib.sha256(b.stderr.encode()).hexdigest()
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/v41x_hbm_arb_concurrent.json")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="v41x_hbm_arb_") as td:
        direct = run(False, Path(td))
        piped = run(True, Path(td))
    pins = SOURCES + ["tools/rtl_v41x_hbm_arb_concurrent.py"]
    rec = {
        "schema": "opentallas.rtl.v41x_hbm_arb_concurrent.v1",
        "status": "pass",
        "scope": "two-user, fixed-clock, 32-PC one-entry responder; index and KV share K ports; "
                 "not the HBM DRAM model, weight-port interference, full token or routed clock",
        "stimulus": {"index_responses": 8192, "kv_responses": 2048,
                     "index_per_user": 4096, "kv_per_user": 1024,
                     "kv_downstream_ready": "false each 13th cycle", "reads_only": True},
        "direct": direct,
        "pipeline": piped,
        "observation": "The request/response pipeline preserves exact replies and fixed-clock completion; "
                       "it increases KV latency under output stalls. It is a timing-closure option, "
                       "not an evidence-backed token-rate uplift.",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in pins},
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({"status": rec["status"], "direct_cycles": direct["cycles"],
                      "pipeline_cycles": piped["cycles"], "kv_mean_latency_direct": direct["kv_mean_latency_cycles"],
                      "kv_mean_latency_pipeline": piped["kv_mean_latency_cycles"]}))


if __name__ == "__main__":
    main()
