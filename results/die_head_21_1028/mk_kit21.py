# DIE-HEAD-20: estimate-before-build -- can MAIN gen_phys regenerate the DH9 one-entry hd_tile kit?
from pathlib import Path
import json, sys
W=Path("/srv/opentallas-scratch2/claude/wt/die-head-21")
O=Path("/srv/opentallas-scratch2/claude/codex-head-die-1028-0405")
R=Path("/srv/opentallas-scratch2/claude/die-head-21")
OUT=Path(sys.argv[1])
sys.path.insert(0,str(W/"tools/die_plan"))
import gen_phys as G, rtl_lint as L, schema as S
p=Path("/srv/opentallas-scratch2/claude/die-head-20/plan/plan_hd_tile_525.json"); raw=json.loads(p.read_text())
err=S.validate(raw); print("VALIDATE", len(err), err[:5])
P=S.Plan(raw,path=p)
old=O/"tile_corner/hd_tile"; src=[]
for f in L.config(old)["VERILOG_FILES"]:
    n=Path(f).name; f=old/"rtl"/n
    if n=="ot_dp_clk_landing_ca.sv": f=W/"rtl/common"/n
    if (R/"rtl"/n).is_file(): f=R/"rtl"/n
    assert f.is_file(),f; src.append(str(f))
print(G.write_type_kit(P,"hd_tile",OUT,src,root=W,trial=True),flush=True)
