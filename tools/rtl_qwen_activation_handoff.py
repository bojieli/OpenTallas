#!/usr/bin/env python3
"""Run the logical two-reticle activation handoff under deterministic stalls."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/link/ot_qwen_activation_handoff.sv"
TB = ROOT / "rtl/test/tb_qwen_activation_handoff.sv"
INPUTS = (RTL, TB, Path(__file__).resolve())
METRICS = re.compile(
    r"HANDOFF beats=(\d+) completions=(\d+) aborts=(\d+) users=(\d+) "
    r"cycles=(\d+) max_level=(\d+) source_stalls=(\d+) sink_stalls=(\d+) "
    r"status_stalls=(\d+) terminal_wait=(\d+) fault=(\d+) seed=([0-9a-f]+)"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/qwen_two_reticle_handoff"))
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/qwen_two_reticle_handoff.json")
    args = ap.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    verilator = os.environ.get("VERILATOR")
    if verilator is None:
        preferred = Path("/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator")
        verilator = str(preferred if preferred.exists() else shutil.which("verilator"))
    rec = {
        "schema": "opentallas.qwen-two-reticle-logical-handoff.v1",
        "configuration": {"data_bits": 256, "transaction_bits": 12, "user_bits": 3,
                          "position_bits": 16, "topology_bits": 5,
                          "exchange_bits": 8, "fifo_depth": 4,
                          "users": 2, "transactions": 4, "exchanges_at_one_position": 4,
                          "payload_beats": 536, "full_vector_bytes": 16384,
                          "aborted_transactions": 1, "seed": "71ace55d"},
        "claim_boundary": "Logical opaque repeated-exchange handoff between two reduced Qwen reticles. "
                          "The test checks exact beats, tags, terminal completion/abort and "
                          "bounded backpressure. It is not a UCIe PHY, two-reticle core "
                          "integration, full 73-exchange TP-2 traffic, link timing, production "
                          "throughput, or energy result. No payload arithmetic or layer cut is assumed.",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in INPUTS},
        "workdir": str(work),
    }
    try:
        version = subprocess.run([verilator, "--version"], capture_output=True,
                                 text=True, check=True, timeout=10)
        rec["verilator_version"] = version.stdout.strip()
        obj = work / "obj"
        cmd = [verilator, "--binary", "--timing", "--top-module",
               "tb_qwen_activation_handoff", "-Mdir", str(obj), str(RTL), str(TB)]
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        rec["build_returncode"] = build.returncode
        rec["build_output_tail"] = (build.stdout + build.stderr)[-4000:]
        if build.returncode:
            raise RuntimeError("Verilator build failed")
        exe = obj / "Vtb_qwen_activation_handoff"
        rec["binary_sha256"] = sha(exe)
        run = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True,
                             timeout=60)
        rec["returncode"] = run.returncode
        rec["stdout"] = run.stdout
        rec["stderr"] = run.stderr
        match = METRICS.search(run.stdout)
        if match:
            names = ("beats", "completions", "aborts", "users", "cycles", "max_level",
                     "source_stalls", "sink_stalls", "status_stalls", "terminal_wait", "fault")
            rec["metrics"] = dict(zip(names, map(int, match.groups()[:11])))
            rec["metrics"]["seed"] = match.group(12)
        m = rec.get("metrics", {})
        rec["status"] = "pass" if (
            run.returncode == 0 and re.search(r"(?m)^PASS$", run.stdout) and
            "FAIL" not in run.stdout and "FATAL" not in run.stdout and
            m.get("beats") == 536 and m.get("completions") == 4 and
            m.get("aborts") == 1 and m.get("users") == 2 and
            m.get("max_level") == 4 and m.get("fault") == 0 and
            m.get("seed") == "71ace55d" and
            all(m.get(k, 0) > 0 for k in ("source_stalls", "sink_stalls",
                                           "status_stalls", "terminal_wait"))
        ) else "fail"
        rec["phase"] = "simulation"
    except Exception as exc:
        rec.update(status="fail", phase="exception", error=str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(args.output, rec["status"], rec["phase"], flush=True)
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
