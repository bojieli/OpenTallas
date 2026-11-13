#!/usr/bin/env python3
"""HOLD-TAP-1 private proof prep: stage the R-CLOCK hold build into a COPY of an existing kit and reset it to CTS.
usage: prep_proof.py KITCOPY RUN_KIT_SH SRC_KIT WT   (config.mk keeps the source kit's mtime: no re-synthesis)"""
import ast, os, shutil, sys
from pathlib import Path
kit, rk, src, wt = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(wt / "tools/die_plan"))
import pregrt_ff_hold as PG
new = next(ast.literal_eval(n.value) for n in ast.parse((wt / "tools/die_plan/gen_phys.py").read_text()).body
           if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "RUN_KIT" for t in n.targets))
A = "  if [ \\$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = grt ]; } && grep -q '^export OT_PREGRT_FF_HOLD = 1'"
B = "  HM=; if ["
def block(t):
    assert t.count(A) == 1, t.count(A)
    i = t.index(A); return i, t.index(B, i)
t = rk.read_text()
i, j = block(t); ni, nj = block(new)
if t[i:j] != new[ni:nj]:
    shutil.copyfile(rk, str(rk) + ".pre_holdtap1")
    rk.write_text(t[:i] + new[ni:nj] + t[j:])
shutil.copyfile(wt / "tools/die_plan/pregrt_ff_hold.py", kit / "pregrt_ff_hold.py")
PG.install({"clock": {}}, kit)
cfg = kit / "config.mk"; c = cfg.read_text()
if PG.CONFIG not in c:
    c = c.rstrip("\n") + "\n" + "\n".join(PG.config_lines({"clock": {}})) + "\n"
elif "OT_PREGRT_HOLD_GUARD" not in c:
    c = c.rstrip("\n") + f"\nexport OT_PREGRT_HOLD_GUARD = {PG.GUARD_PS:g}\n"
cfg.write_text(c)
st = (src / "config.mk").stat(); os.utime(cfg, (st.st_atime, st.st_mtime))
base = next((kit / "run/results/asap7").glob("*/base")); name = base.parent.name
gone = []
for d in (base, kit / "run/logs/asap7" / name / "base", kit / "run/reports/asap7" / name / "base"):
    for f in d.iterdir() if d.is_dir() else []:
        if f.name[:2] in ("4_", "5_", "6_") or f.name.startswith(("generate_abstract", "cts_", "final_", "drt_", "grt_")):
            (shutil.rmtree if f.is_dir() else os.unlink)(f); gone.append(f.name)
for n in ("signoff", "hold_gate.log", "FAIL_POSTCTS", "pin_audit.json", "run_route.log", "physical_completion"):
    p = kit / n
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): p.unlink()
print("prepared", kit, "removed", len(gone), "stage files; run_kit pregrt block new:", t[i:j] != new[ni:nj])
