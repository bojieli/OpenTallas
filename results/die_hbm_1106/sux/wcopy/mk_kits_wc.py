#!/usr/bin/env python3
"""mk_kits_wc.py SRC_KIT DST_KIT N FORM_TEXT [GUIDE_UM]: HBM-FORM-SPLIT-14-SUX kit = SRC inputs + WCOPY N RTL.
GUIDE_UM > 0 adds the REBAL-10 macro register guides (g_read[k].g_wcopy. beside macro k, GPL only, released before DPL)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
src, dst, n, form = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
grow = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
EX = ("run signoff lec lec_async.lock lec_async.on lec_async.owner lec_async.pid lec_async.runs lec_async.source_identity "
      "lec_async.identity lec_async.ready lec_async.done lec_async.rc *.log rtl_lint.json rtl_lint.ys selrange.json selrange.rc "
      "face_guard.json port_bind.json postcts_gate_*.json hold_census.txt pin_audit.json placed.csv physical_completion views "
      "__pycache__ FAIL_* *.previous.* eco_* FORM_v*.txt").split()
if dst.exists():
    raise SystemExit(f"{dst} exists")
dst.mkdir(parents=True)
subprocess.check_call(["rsync", "-a", *[f"--exclude={e}" for e in EX], f"{src}/", f"{dst}/"])
subprocess.check_call([sys.executable, "-I", str(HERE / "patch_wcopy.py"), str(dst), str(n)])
(dst / f"FORM_{dst.name.rsplit('_', 1)[1]}.txt").write_text(form + "\n")
if grow > 0:
    W, H = 94.824, 41.064
    die = re.search(r"CORE_AREA = (\S+) (\S+) (\S+) (\S+)", (dst / "config.mk").read_text())
    cx0, cy0, cx1, cy1 = (float(v) for v in die.groups())
    spec = []
    for m in re.finditer(r"g_read\\\[(\d)\\\]\.u_m\} \S+ (\S+) (\S+) R0", (dst / "macro_placement.tcl").read_text()):
        k, x, y = int(m.group(1)), float(m.group(2)), float(m.group(3))
        pf = f"u_fcore.u_core.u_bank.u_data.g_read[{k}].g_wcopy."
        spec.append(f"{{m{k} {{{{{pf}}}}} {max(cx0, x - grow):.3f} {max(cy0, y - grow):.3f} {min(cx1, x + W + grow):.3f} {min(cy1, y + H + grow):.3f}}}")
    assert len(spec) == 6, spec
    head = "# HBM-FORM-SPLIT-14-SUX: spec for the REBAL-10 guide (6 macros, g_wcopy registers).\nset ::ot_mrg_spec [concat " + " ".join(spec) + "]\n"
    (dst / "macro_reg_guide.tcl").write_text(head + (HERE / "macro_reg_guide.tcl").read_text())
    shutil.copyfile(HERE / "macro_reg_guide_release.tcl", dst / "macro_reg_guide_release.tcl")
    for f, s in (("face_flops.tcl", "macro_reg_guide.tcl"), ("face_flops_release.tcl", "macro_reg_guide_release.tcl")):
        with open(dst / f, "a") as fh:
            fh.write(f"# HBM-FORM-SPLIT-14-SUX macro register guide\nsource /work/{s}\n")
print(dst, "WCOPY", n, "guide", grow)
