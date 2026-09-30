#!/usr/bin/env python3
"""W18: run the field-current control bench (rtl/test/tb_chip_v41_xcap_droop.sv) on the RTL and on mutants,
and write a source-pinned record.

    python3 tools/w18/field_ctrl_check.py --output results/physical_abi3/asap7/chip/v41_w18/field_ctrl_bench.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
XCAP = ROOT / "rtl/chip/ot_chip_v41_xcap.sv"
DROOP = ROOT / "rtl/chip/ot_chip_v41_droop_ctrl.sv"
TB = ROOT / "rtl/test/tb_chip_v41_xcap_droop.sv"
MUTANTS = {
    "take_ignores_parity": (XCAP, "assign take = xs_v && (cap ? (xs_sub == ph) : !xs_sub);",
                            "assign take = xs_v && !xs_sub;"),
    "second_beat_dropped": (XCAP, "held <= in_cap;", "held <= 1'b0;"),
    "release_without_hold": (DROOP, "&& ok_cnt + 1'b1 >= cfg_hold", ""),
    "no_min_stretch": (DROOP, "if (min_cnt <= 8'd1 && code_q", "if (code_q"),
}


def run(srcs: dict, d: Path, tag: str) -> dict:
    files = []
    for p, text in srcs.items():
        f = d / f"{tag}_{p.name}"
        f.write_text(text)
        files.append(str(f))
    subprocess.run(["iverilog", "-g2012", "-o", str(d / tag), *files, str(TB)], check=True, capture_output=True)
    out = subprocess.run(["vvp", "-n", str(d / tag)], capture_output=True, text=True, timeout=900).stdout
    m = re.search(r"W18_FIELD_RESULT (.*)", out)
    return dict(result=dict(x.split("=") for x in m.group(1).split()) if m else {},
                verdict=out.strip().splitlines()[-1] if out.strip() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    base = {XCAP: XCAP.read_text(), DROOP: DROOP.read_text()}
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        rec = dict(schema="opentallas.v41.w18_field_ctrl_bench.v1", rtl=run(base, d, "rtl"), mutants={})
        for k, (f, old, new) in MUTANTS.items():
            assert old in base[f], k
            m = dict(base); m[f] = base[f].replace(old, new)
            rec["mutants"][k] = run(m, d, k)
    rec["sources"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (XCAP, DROOP, TB)}
    rec["tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rec["simulator"] = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    rec["pass"] = rec["rtl"]["verdict"] == "PASS" and all(m["verdict"] == "FAIL" for m in rec["mutants"].values())
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"rtl": rec["rtl"], "mutants": {k: v["verdict"] for k, v in rec["mutants"].items()},
                      "pass": rec["pass"]}, indent=1))


if __name__ == "__main__":
    main()
