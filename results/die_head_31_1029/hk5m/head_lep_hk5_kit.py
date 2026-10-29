#!/usr/bin/env python3
"""DIE-HEAD-31: first hd_lep0N kit on the hk5 HEAD-START source (none existed).  The generic steps of
tools/s81_head/head_ctl_hk5_kit.py (count strap pin sites + private raw START exports on a plan copy, `gen.py phys
--trial --clock-landing SIDECAR --types hd_lep0N`, wrapper reset-alias + private raw RTL patches), without the
hd_ctl-only LEC fixes.  V1 = default PLACE_DENSITY, V2 = PLACE_DENSITY .35.  usage: ROOT SOURCE_DIR OUT_DIR"""
import json, shutil, subprocess, sys
from pathlib import Path
root, source, out = (Path(a).resolve() for a in sys.argv[1:4])
sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
from head_count_strap_sites import apply as count_strap_sites
from head_start_raw_private import prepare_plan, patch_rtl as private_raw_rtl
from head_start_reset_aliases import patch_rtl
TYPE = "hd_lep0N"
out.mkdir(parents=True)
path, side = source / "source_plan.json", source / "source_sidecar.json"
plan = json.loads(path.read_text())
plan, straps = count_strap_sites(plan, path, root, types={TYPE})
plan, private = prepare_plan(plan, {TYPE})
cand = out / "source_plan_lep_hk5.json"; cand.write_text(json.dumps(plan, indent=1) + "\n")
# relative core pin tables (core_pins/...) resolve against the plan directory: link the source's own tables
for f in source.iterdir():
    if f.is_dir():
        (out / f.name).symlink_to(f.resolve())
gen = out / "gen"
cmd = [sys.executable, str(root / "tools/die_plan/gen.py"), "phys", str(cand), "--clock-landing", str(side),
       "--types", TYPE, "--out", str(gen), "--rtl-root", str(root), "--trial"]
r = subprocess.run(cmd, capture_output=True, text=True); (out / "gen.log").write_text(r.stdout + r.stderr)
if r.returncode: raise SystemExit(f"gen.py phys exit {r.returncode}: {(r.stdout + r.stderr)[-1500:]}")
t = plan["partition_types"][TYPE]; kit = gen / TYPE; wr = gen / "_rtl" / f"{t['module']}.sv"
rows = t.get("reset_start_raw_exports", [])
text = patch_rtl(wr.read_text(), rows); text, prr = private_raw_rtl(text, t)
wr.write_text(text); (kit / "rtl" / wr.name).write_text(text)
for v in ("v1", "v2"):
    shutil.copytree(gen, out / v, symlinks=True)
    if v == "v2":
        c = out / v / TYPE / "config.mk"; s = c.read_text(); assert s.count("export PLACE_DENSITY = ") == 1, "density"
        import re; c.write_text(re.sub(r"export PLACE_DENSITY = [0-9.]+\n", "export PLACE_DENSITY = 0.35\n", s))
rep = dict(type=TYPE, cells=t.get("cells"), raw_reset_exports=len(rows), count_strap_sites=straps, private_raw_rtl=prr,
           gen_cmd=cmd, added_cycles=0, route_qualified=False)
(out / "lep_hk5_receipt.json").write_text(json.dumps(rep, indent=2) + "\n"); print(json.dumps(rep)[:600])
