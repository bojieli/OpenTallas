#!/usr/bin/env python3
"""Run an existing core flow and fail closed on its final physical gates.

The core's intended P&R recipe stays in --runner. Use an owned fresh successor
kit: existing sign-off records are refused rather than overwritten. This wrapper
supports legacy runners that accidentally return the ORFS status after sign-off
crashes or fails. It does not repair, alter constraints, or waive a gate.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run(kit: Path, runner: Path, goal: str, mem: int, threads: int) -> int:
    kit = kit.resolve()
    final = goal in {"route", "finish"}
    record = kit / "signoff/signoff.json"
    if final:
        missing = [n for n in ("signoff.py", "pair_skew.tcl", "pin_audit.py") if not (kit / n).is_file()]
        if missing:
            print("CORE_CHECKED PREFLIGHT FAIL missing " + ", ".join(missing), file=sys.stderr)
            return 4
        if record.exists():
            print("CORE_CHECKED PREFLIGHT FAIL existing signoff record; use a fresh successor kit", file=sys.stderr)
            return 4
    started_ns = time.time_ns()
    result = subprocess.run(["bash", str(runner.resolve()), str(kit), goal, str(mem), str(threads)])
    if result.returncode:
        return result.returncode
    if not final:
        print(f"CORE_CHECKED {goal} completed; physical signoff NOT RUN")
        return 0
    try:
        signoff = json.loads(record.read_text())
        pins = json.loads((kit / "pin_audit.json").read_text())
    except (OSError, ValueError) as exc:
        print(f"CORE_CHECKED FAIL missing/invalid final gate: {exc}", file=sys.stderr)
        return 5
    if (kit / "pin_audit.json").stat().st_mtime_ns < started_ns:
        print("CORE_CHECKED FAIL pin audit predates this run", file=sys.stderr)
        return 5
    if signoff.get("verdict") != "SIGNED" or pins.get("verdict") != "PASS":
        print(f"CORE_CHECKED FAIL signoff={signoff.get('verdict')} pins={pins.get('verdict')}", file=sys.stderr)
        return 6
    if signoff.get("policy", {}).get("period_ps") != 833.0:
        print("CORE_CHECKED FAIL signoff does not use the 833 ps release clock", file=sys.stderr)
        return 6
    print("CORE_CHECKED SIGNED (signoff + pin audit)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kit", type=Path)
    ap.add_argument("goal", choices=("synth", "place", "cts", "grt", "route", "finish"))
    ap.add_argument("mem", type=int)
    ap.add_argument("threads", type=int)
    ap.add_argument("--runner", type=Path, required=True)
    a = ap.parse_args()
    return run(a.kit, a.runner, a.goal, a.mem, a.threads)


if __name__ == "__main__":
    raise SystemExit(main())
