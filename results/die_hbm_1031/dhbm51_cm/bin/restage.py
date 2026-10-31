#!/usr/bin/env python3
"""restage.py KIT OUTKIT PLAN_CM: copy of a probe kit with macro_placement.tcl rewritten by the generator functions
(core_macros_placement + snap_macro_placement + the same table form) from PLAN_CM/core_macros.json. Check only."""
import json,re,shutil,sys
from pathlib import Path
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/die_plan/hbm_arch_cores")
import gen_core_kit_hbm as G
k,o,pl=map(Path,sys.argv[1:4])
if o.exists(): shutil.rmtree(o)
shutil.copytree(k,o)
fz=json.load(open(k/"freeze.json")); mod=fz["module"]; mac=fz["macros"]; w,h=fz["outline_um"]
rows,src=G.core_macros_placement(pl/"core_macros.json",mod,mac)
rows,moves=G.snap_macro_placement(rows,(k/"make_tracks.tcl").read_text(),lambda m:(k/"macros"/f"{m}.lef").read_text(),(w,h))
tbl=[]
for p in rows:
    inst="u_fcore."+p["inst"]; inst=re.sub(r"(?<!\\)([\[\]])",r"\\\1",inst)
    tbl.append("  {%s} %s %s %s %s"%(inst,p["macro"],G._um(p["xy_um"][0]),G._um(p["xy_um"][1]),p.get("orient","R0")))
(o/"macro_placement.tcl").write_text("\n".join(["foreach {inst master x y orient} {"]+tbl+["} {","  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact","}"])+"\n")
c=(o/"config.mk").read_text()
if "MACRO_PLACEMENT_TCL" not in c: (o/"config.mk").write_text(c.rstrip("\n")+"\nexport MACRO_PLACEMENT_TCL = /work/macro_placement.tcl\n")
print(o.name,"rows",len(rows),"snap moves",len(moves))
