#!/usr/bin/env python3
"""DIE-HBM-29 (COORD 21:4x item 2, HBM-054 form): static macro sites for ot_hbm_idx_query_static (170.64 x 164.16,
5 x ot_sram_1r1w_32x128_m1 51.408 x 20.790).  The old 'placed' basis (hbm-cores-r7 _k2 placed.csv) puts gcode[1]/[2]/
scmem in one stacked column with 0.072-um gaps and overlaps gcode[2] on re-kit / fails preflight on 8.64-um channels.
Pin faces of the d28c fr28 table: E 1,032, N 596, W 3, S 2 -> the macros go SW, the E band (x > 130.9, 39.7 um) and the
N band (y > 103.4, 60.7 um) stay free for the face logic.  Plan clock entry island (82.08..90.72, 77.76..86.4) clear.
Grid: W column x 15.12 (gcode[0..2], 3 rows), second column x 79.488 (scmem, gcode[3], 2 rows); 12.96-um column
channel, 12.96-um row channels, >= 10.8 um beyond the 4.32-um core inset (start 15.12); x on 0.108, y on 0.012 mod 0.048 (HBM-054 snap).
usage: idxq_static.py PLANDIR(in) OUTDIR LEFDIR...    (pre-clears the KNOWN 'placed' rows, then core_macros_fix --static)
"""
import json, subprocess, sys, tempfile
from pathlib import Path

CORE = "ot_hbm_idx_query_static"
W, H = 51.408, 20.790
sy = lambda y: round(0.012 + round((y - 0.012) / 0.048) * 0.048, 3)
sx = lambda x: round(round(x / 0.108) * 0.108, 3)
x0, x1 = sx(15.12), sx(15.12 + W + 12.96)
ys = [sy(15.12 + i * (H + 12.96)) for i in range(3)]
sites = [("u_fcore.core.gcode[0].mem", x0, ys[0]), ("u_fcore.core.gcode[1].mem", x0, ys[1]),
         ("u_fcore.core.gcode[2].mem", x0, ys[2]), ("u_fcore.core.scmem", x1, ys[0]),
         ("u_fcore.core.gcode[3].mem", x1, ys[1])]
isl = (82.08, 77.76, 90.72, 86.4)
for n, x, y in sites:
    assert not (x < isl[2] and x + W > isl[0] and y < isl[3] and y + H > isl[1]), n
spec = {CORE: dict(outline_um=[170.64, 164.16], basis=__doc__.split("\n")[0] + " | grid W col x %.3f / 2nd col x %.3f, rows %s" % (x0, x1, ys),
                   macros=[dict(name=n, master="ot_sram_1r1w_32x128_m1", origin_um=[x, y], orient="R0") for n, x, y in sites])}
plan, out, lefs = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
cm = json.loads((plan / "core_macros.json").read_text())
old = cm["cores"][CORE]
assert sorted(m["name"] for m in old["macros"]) == sorted(n for n, _, _ in sites), "instance names differ from plan"
import os, shutil
tmp = Path(tempfile.mkdtemp(prefix="idxq_", dir=out.parent)) / "p"
shutil.copytree(plan, tmp, symlinks=True, copy_function=os.link)
(tmp / "core_macros.json").unlink()
old_copy = dict(old)
cm["cores"][CORE] = dict(status="UNKNOWN", outline_um=old["outline_um"], why="DIE-HBM-29: placed basis overlaps / 8.64-um channels",
                         macros=[], previous_placed=old_copy)
(tmp / "core_macros.json").write_text(json.dumps(cm, indent=1))
(out.parent / "idxq_static_spec.json").write_text(json.dumps(spec, indent=1))
tool = Path(__file__).resolve().parents[3] / "physical/die_plan/hbm/core_macros_fix.py"
cmd = ["python3", str(tool), str(tmp), "--out", str(out), "--static", str(out.parent / "idxq_static_spec.json")]
for d in lefs:
    cmd += ["--lef-dir", d]
subprocess.run(cmd, check=True)
shutil.rmtree(tmp.parent)
print(json.dumps(spec, indent=1))
