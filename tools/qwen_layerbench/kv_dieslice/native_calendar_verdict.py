#!/usr/bin/env python3
"""Keep native calendar health separate from the historical boot-load verdict."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path


def inspect(log: str, simulator_exit: int | None) -> dict:
    samples = []
    for line in log.splitlines():
        m = re.search(r"\bdcal_fault\s+([01])\b", line)
        if m:
            cycle = re.search(r"\bcyc\s+(\d+)\b", line)
            samples.append({"cycle": int(cycle[1]) if cycle else None,
                            "fault": int(m[1])})
    lines = log.splitlines()
    boot_lines = [(i, line) for i, line in enumerate(lines) if re.search(r"KVSLICE_BOOT (PASS|FAIL)\b", line)]
    boot = re.findall(r"KVSLICE_BOOT (PASS|FAIL)\b", log)
    finals = [(i, line) for i, line in enumerate(lines) if re.search(r"\bKVSLICE_FINALCAL\b", line)]
    terminal = re.search(r"\bdcal_fault\s+([01])\b", finals[-1][1]) if finals else None
    terminal_order = bool(finals and boot_lines and finals[-1][0] > boot_lines[-1][0]
                          and not any("KVSLICE_POST" in line for line in lines[finals[-1][0] + 1:]))
    asserted = [s for s in samples if s["fault"]]
    if asserted:
        verdict = "FAIL"
    elif terminal and terminal_order and terminal[1] == "0" and simulator_exit == 0 and boot[-1] == "PASS":
        verdict = "PASS"
    else:
        verdict = "NOT_QUALIFIED"
    return {"scope": "native_calendar_component", "verdict": verdict,
            "boot_load_verdict": boot[-1] if boot else "NOT_OBSERVED",
            "simulator_exit": simulator_exit, "observations": len(samples),
            "first_fault_cycle": asserted[0]["cycle"] if asserted else None,
            "terminal_calendar_marker": bool(terminal and terminal_order),
            "last_observed_fault": samples[-1]["fault"] if samples else None}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("log", type=Path)
    p.add_argument("--exit-file", type=Path, required=True)
    a = p.parse_args()
    try:
        status = int(a.exit_file.read_text().strip())
    except (OSError, ValueError):
        status = None
    result = inspect(a.log.read_text() if a.log.exists() else "", status)
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
