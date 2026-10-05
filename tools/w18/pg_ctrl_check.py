#!/usr/bin/env python3
"""W18: run the stage power-gating controller bench (rtl/test/tb_chip_v41_pg_ctrl.sv) on the RTL and on two
mutants (spacing ignored; isolation released before reset), and write a source-pinned record.

    python3 tools/w18/pg_ctrl_check.py --output results/physical_abi3/asap7/chip/v41_w18/pg_ctrl_bench.json
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
RTL = ROOT / "rtl/chip/ot_chip_v41_pg_ctrl.sv"
TB = ROOT / "rtl/test/tb_chip_v41_pg_ctrl.sv"
MUTANTS = {
    "enable_spacing_ignored": ("cnt >= cfg_step && (idx", "cnt >= 1 && (idx"),
    "isolation_released_before_reset": ("st <= S_RST; cnt <= CW'(cfg_rst); clk_en <= 1'b1;",
                                        "st <= S_RST; cnt <= CW'(cfg_rst); clk_en <= 1'b1; iso_n <= 1'b1;"),
}


def run(src: str, d: Path, tag: str) -> dict:
    f = d / f"{tag}.sv"
    f.write_text(src)
    subprocess.run(["iverilog", "-g2012", "-o", str(d / tag), str(f), str(TB)], check=True, capture_output=True)
    out = subprocess.run(["vvp", "-n", str(d / tag)], capture_output=True, text=True, timeout=900).stdout
    m = re.search(r"W18_PG_RESULT (.*)", out)
    kv = dict(x.split("=") for x in m.group(1).split()) if m else {}
    return dict(result=kv, verdict=out.strip().splitlines()[-1] if out.strip() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    src = RTL.read_text()
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        rec = dict(schema="opentallas.v41.w18_pg_ctrl_bench.v1", rtl=run(src, d, "rtl"), mutants={})
        for k, (old, new) in MUTANTS.items():
            assert old in src, k
            rec["mutants"][k] = run(src.replace(old, new), d, k)
    ver = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    rec.update(sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (RTL, TB)},
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), simulator=ver,
               pass_=rec["rtl"]["verdict"] == "PASS" and all(m["verdict"] == "FAIL" for m in rec["mutants"].values()),
               clock_ghz=1.087, wake_budget_ns=1000.0,
               basis="W14 model: ~100 staggered 10-cycle sub-domains in a 1 us wake (ReGate); switch rings per "
                     "tools/w18/die_pdn.py")
    rec["pass"] = rec.pop("pass_")
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
