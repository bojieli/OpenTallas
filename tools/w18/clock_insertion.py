#!/usr/bin/env python3
"""Measured clock insertion of an ORFS stage result (CTS calibration for the IO SDC, owner rule 2026-10-06).

Loads <stage>.odb/.sdc (default 4_cts), estimates placement parasitics, propagates the clock and reports the clock
arrival (rise) at every register / macro clock pin at SS and FF: min / max / mid in ps.

    python3 tools/w18/clock_insertion.py --orfs-dir <keep-workdir>/orfs --stage 4_cts [--macro DIR] --output R.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from corner_sta import LIBS, PLAT, ROOT


def script(corner, base, stage, macros):
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{l}" for l in LIBS[corner])
    mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros)
    mlefs = "\n".join(f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros)
    rc = f"{PLAT}/setRC.tcl"
    return f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{mlefs}
{libs}
{mlibs}
read_db {base}/{stage}.odb
read_sdc {base}/{stage}.sdc
if {{[file exists {rc}]}} {{ source {rc} }}
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set lo 1e9; set hi -1e9; set n 0
foreach p [all_registers -clock_pins] {{
  set a [get_property $p arrival_max_rise]
  if {{$a eq "" || $a eq "INF" || $a eq "-INF"}} continue
  if {{$a < $lo}} {{ set lo $a }}; if {{$a > $hi}} {{ set hi $a }}; incr n
}}
puts "OT_INS $n $lo $hi"
report_clock_skew
exit
"""


def run(orfs, corner, stage, macros):
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(orfs)}"
    (orfs / f"w18_ins_{corner}.tcl").write_text(script(corner, rel, stage, macros))
    cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{ROOT}:/src:ro", "openroad/orfs:latest", "bash",
           "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/w18_ins_{corner}.tcl"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout + p.stderr
    (orfs / f"w18_ins_{corner}.log").write_text(out)
    m = re.search(r"^OT_INS (\d+) (\S+) (\S+)", out, re.M)
    if not m or int(m.group(1)) == 0:
        return dict(corner=corner, error=out[-800:])
    lo, hi = float(m.group(2)), float(m.group(3))
    sc = 1e12 if abs(hi) < 1e-3 else 1.0          # seconds or ps, depending on the STA unit
    lo, hi = lo * sc, hi * sc
    return dict(corner=corner, clock_pins=int(m.group(1)), min_ps=round(lo, 1), max_ps=round(hi, 1),
                mid_ps=round((lo + hi) / 2, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--stage", default="4_cts")
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    o = a.orfs_dir.resolve()
    rec = dict(schema="opentallas.w18.clock_insertion.v1", orfs_dir=str(o), stage=a.stage,
               ss=run(o, "ss", a.stage, a.macro), ff=run(o, "ff", a.stage, a.macro))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
