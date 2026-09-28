#!/usr/bin/env python3
"""Source-pinned finite mixed-owner gate for the four-stack Qwen HBM service.

This synthetic controller and single-PC contention case checks arbitration,
completion and ownership. Its cycles are not a token or throughput estimate.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv",
    "rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv",
    "rtl/hdc/hbm/ot_hdc_qwen_hbm_regions.sv",
    "rtl/test/tb_hdc_qwen_hbm_mixed_service.sv",
)
PATTERN = re.compile(
    r"RESULT cycles=(\d+) requests=(\d+) responses=(\d+) "
    r"phy_stalls=(\d+) rsp_blocked=(\d+) credit_blocked=(\d+) "
    r"max_wait=(\d+) pc=(\d+) clients=(\d+)"
)


def run() -> dict:
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}
    with tempfile.TemporaryDirectory(prefix="qwen-hbm-mixed-") as tmp:
        binary = Path(tmp) / "gate.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_hbm_mixed_service",
                        "-o", str(binary), *SOURCES], cwd=ROOT, check=True,
                       capture_output=True, text=True)
        result = subprocess.run(["vvp", str(binary)], cwd=ROOT, check=True,
                                capture_output=True, text=True, timeout=30)
    found = PATTERN.search(result.stdout)
    if not found:
        raise RuntimeError(f"missing complete mixed-service verdict: {result.stdout}")
    names = ("cycles", "requests", "responses", "phy_stalls", "rsp_blocked",
             "credit_blocked", "max_wait", "pc", "clients")
    metrics = dict(zip(names, map(int, found.groups())))
    if (metrics["requests"] != 24 or metrics["responses"] != 24 or
            metrics["clients"] != 6 or metrics["pc"] != 0 or
            min(metrics[k] for k in ("phy_stalls", "rsp_blocked", "credit_blocked")) <= 0):
        raise RuntimeError(f"mixed-service checks incomplete: {metrics}")
    if pins != {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}:
        raise RuntimeError("mixed-service source changed while running")
    return {"status": "pass", "scope": "synthetic one-PC mixed-owner functional gate",
            "throughput_claim": False, "configuration": {
                "stacks": 4, "pcs_per_stack": 32, "active_pc": 0, "clients": 6,
                "max_outstanding_per_client_pc": 2,
                "controller_accept_period_cycles": 3,
                "controller_response_delay_cycles": "24+sequence_mod_3",
                "sector_bytes": 32},
            "metrics": metrics, "source_sha256": pins}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()
