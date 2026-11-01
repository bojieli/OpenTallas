"""DIE-QC-58A: set a legacy gen_core_kit_qc kit's IO vclk frame (TT/FF) to the recipe insertion_ps/insertion_ff_ps,
in exactly the files gen_core_kit_qc.py derives from them (config.mk OT_VCLK_*, constraint.sdc + vclk_ff.sdc
set_clock_latency -source, sdc_lint.json, clock_binding.json, freeze.json). Values only; nothing else changes.
  python3 set_frame.py KIT TT FF BASIS"""
import json, re, sys
from pathlib import Path
k, tt, ff, basis = Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
def sub(p, pat, rep, n=1):
    s = p.read_text(); s2, c = re.subn(pat, rep, s, flags=re.M)
    if c != n: raise SystemExit(f"{p.name}: {c} matches for {pat!r}, want {n}")
    p.write_text(s2)
sub(k / "config.mk", r"^export OT_VCLK_TT = .*$", f"export OT_VCLK_TT = {tt:.4f}")
sub(k / "config.mk", r"^export OT_VCLK_FF = .*$", f"export OT_VCLK_FF = {ff:.4f}")
sub(k / "constraint.sdc", r"^set_clock_latency -source \S+ \[get_clocks vclk\]$", f"set_clock_latency -source {tt:.4f} [get_clocks vclk]")
sub(k / "vclk_ff.sdc", r"^set_clock_latency -source \S+ \[get_clocks vclk\]$", f"set_clock_latency -source {ff} [get_clocks vclk]")
j = json.loads((k / "sdc_lint.json").read_text()); j["insertion_ps"], j["insertion_ff_ps"] = tt, ff
(k / "sdc_lint.json").write_text(json.dumps(j, indent=1))
cb = json.loads((k / "clock_binding.json").read_text())
def setcb(d):
    for key in d:
        if isinstance(d[key], dict) and set(d[key]) >= {"tt", "ff"}:
            if isinstance(d[key]["tt"], (int, float)): d[key]["tt"], d[key]["ff"] = tt, ff
            elif isinstance(d[key]["tt"], str): d[key]["tt"] = d[key]["ff"] = basis
    if isinstance(d.get("tt"), (int, float)): d["tt"], d["ff"] = tt, ff
setcb(cb); (k / "clock_binding.json").write_text(json.dumps(cb, indent=2))
fz = json.loads((k / "freeze.json").read_text())
def walk(o):
    if isinstance(o, dict):
        if isinstance(o.get("insertion_ps"), (int, float)): o["insertion_ps"] = tt
        if isinstance(o.get("insertion_ff_ps"), (int, float)): o["insertion_ff_ps"] = ff
        setcb(o)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(fz); (k / "freeze.json").write_text(json.dumps(fz, indent=1))
print(f"frame {k.name}: TT {tt} FF {ff}")
