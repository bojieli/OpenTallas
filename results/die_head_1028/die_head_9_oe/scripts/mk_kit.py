from pathlib import Path
import json, sys
W=Path("/srv/opentallas-scratch2/claude/wt/die-head-9-oe")
O=Path("/srv/opentallas-scratch2/claude/codex-head-die-1028-0405")
R=Path("/srv/opentallas-scratch2/claude/die-head-9/one_entry")
sys.path.insert(0,str(W/"tools/die_plan"))
import gen_phys as G, rtl_lint as L, schema as S
p=R/"plan_one_entry_450.json"; P=S.Plan(json.loads(p.read_text()),path=p)
old=O/"tile_corner/hd_tile"; src=[]
for f in L.config(old)["VERILOG_FILES"]:
    n=Path(f).name; f=old/"rtl"/n
    if n=="ot_dp_clk_landing_ca.sv": f=W/"rtl/common"/n
    if (R/"_rtl"/n).is_file(): f=R/"_rtl"/n   # regenerated one-entry wrapper + cells
    assert f.is_file(),f; src.append(str(f))
print("\n".join(src))
print(G.write_type_kit(P,"hd_tile",R/"kits",src,root=W,trial=True),flush=True)
(R/"kits/run_kit.sh").write_text(G.RUN_KIT)
