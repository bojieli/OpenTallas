#!/usr/bin/env python3
"""Export a CLOSED routed view as a die abstract: <name>.lef (write_abstract_lef) + <name>_ss.lib / <name>_ff.lib
(write_timing_model, SS / FF libraries, routed SPEF, the sign-off SDC read after the routed one).

    python3 tools/w18/export_view.py --orfs-dir <keep-workdir>/orfs --name NAME --post-sdc REL.sdc [--macro DIR] --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from corner_sta import LIBS, PLAT, ROOT


def script(corner, base, name, macros, post):
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{l}" for l in LIBS[corner])
    mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros)
    mlefs = "\n".join(f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros)
    lef = f"write_abstract_lef /out/{name}.lef" if corner == "ss" else ""
    return f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{mlefs}
{libs}
{mlibs}
read_db {base}/6_final.odb
read_sdc {base}/6_final.sdc
read_spef {base}/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/{post}
puts "OT_WS_MAX [sta::worst_slack_cmd max] OT_WS_MIN [sta::worst_slack_cmd min]"
report_clock_latency -include_internal_latency
write_timing_model -library_name {name}_{corner} /out/{name}_{corner}.lib
{lef}
puts OT_EXPORT_DONE
exit
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--post-sdc", required=True)
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    o = a.orfs_dir.resolve(); a.out.mkdir(parents=True, exist_ok=True); out = a.out.resolve()
    base = next((o / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(o)}"
    rec = dict(schema="opentallas.w18.export_view.v1", name=a.name, orfs_dir=str(o), post_sdc=a.post_sdc)
    for corner in ("ss", "ff"):
        (o / f"w18_export_{corner}.tcl").write_text(script(corner, rel, a.name, a.macro, a.post_sdc))
        cmd = ["docker", "run", "--rm", "-v", f"{o}:/work", "-v", f"{ROOT}:/src:ro", "-v", f"{out}:/out",
               "openroad/orfs:latest", "bash", "-lc",
               f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/w18_export_{corner}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"export_{corner}.log").write_text(log)
        m = re.search(r"OT_WS_MAX (\S+) OT_WS_MIN (\S+)", log)
        rec[corner] = dict(done="OT_EXPORT_DONE" in log, ws_max=m and m.group(1), ws_min=m and m.group(2))
    rec["files"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir())
                    if f.suffix in (".lef", ".lib")}
    (out / "export.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
