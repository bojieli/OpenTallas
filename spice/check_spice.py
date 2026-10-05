#!/usr/bin/env python3
"""Run ngspice and enforce topology-level read-path invariants."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)
LOG = BUILD / "ngspice.log"
process = subprocess.run(
    ["ngspice", "-b", "-o", str(LOG), str(ROOT / "via_rom_read.sp")],
    text=True,
    capture_output=True,
    check=False,
)
if process.returncode:
    raise SystemExit(
        f"ngspice failed ({process.returncode})\nstdout:\n{process.stdout}\nstderr:\n{process.stderr}\n"
        f"log:\n{LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else '(missing)'}"
    )

text = LOG.read_text(encoding="utf-8", errors="replace")
names = (
    "v_present",
    "v_absent",
    "v_masked",
    "sense_present_v",
    "sense_absent_v",
    "read_margin",
    "discharge_delay",
    "read_energy",
)
values = {}
for name in names:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text)
    if not match:
        raise SystemExit(f"missing ngspice measure {name}; see {LOG}")
    values[name] = float(match.group(1))

failures = []
if values["v_present"] >= 0.25:
    failures.append("programmed selected cell did not discharge below 0.25 V")
if values["v_absent"] <= 1.0:
    failures.append("absent-via cell did not retain a high bitline")
if values["v_masked"] <= 1.0:
    failures.append("masked programmed cell leaked/discharged")
if values["read_margin"] <= 0.75:
    failures.append("nominal read margin is below 0.75 V")
if values["sense_present_v"] <= 0.9 or values["sense_absent_v"] >= 0.3:
    failures.append("sense inverter did not resolve both polarities")
if not 0 < values["discharge_delay"] < 2e-9:
    failures.append("discharge delay is outside the topology-test bound")
if values["read_energy"] <= 0:
    failures.append("measured read energy is non-positive")

report = {
    "status": "pass" if not failures else "fail",
    "scope": "generic level-1 MOS topology; not PDK, extracted, or sign-off",
    "measures": values,
    "failures": failures,
    "ngspice_log": str(LOG.relative_to(ROOT)),
}
(BUILD / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if failures:
    raise SystemExit("; ".join(failures))
print(
    "PASS: via-present discharge, via-absent retention, wordline mask, and sense polarity; "
    f"margin={values['read_margin']:.3f} V delay={values['discharge_delay'] * 1e12:.1f} ps"
)
