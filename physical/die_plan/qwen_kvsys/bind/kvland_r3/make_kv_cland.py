"""KV-LAND-R3: compose KV clock landings (c3t crossing table) -> landed plan + sidecar + recipe copy.

Run from the repo root: python3 physical/die_plan/qwen_kvsys/bind/kvland_r3/make_kv_cland.py <landed_crossings.json>
Outputs (repo-relative): physical/die_plan/qwen_kvsys/die_plan_cland_r3.json,
physical/die_plan/qwen_kvsys/bind/kvland_r3/{landing_placement_table.json,landed_crossings_c3t.json},
physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv_2350_cland_r3.json.
Observer = hub_C sequencer core u_seq_u_core: hf (fault, sticky f_pend) / lp_run (loop admission).
"""
import json,sys
from pathlib import Path
sys.path.insert(0,"tools/die_plan")
import clock_landing_plan as C
D=Path("physical/die_plan/qwen_kvsys");O=D/"bind/kvland_r3"
pp=D/"die_plan.json";p=json.loads(pp.read_text());t=json.loads(Path(sys.argv[1]).read_text())
O.mkdir(parents=True,exist_ok=True);(O/"landed_crossings_c3t.json").write_text(json.dumps(t,indent=1)+"\n")
obs=dict(module="qkd_seq_core_static_s",instance_suffix="u_seq_u_core",fault_port="hf",ready_port="lp_run")
a,b=C.compose(p,t,str(pp),observer_part="hub_C",observer=obs)
# Price the landings in the plan's own latency table (schema.lane_latency semantics: +clock_landing into cycles).
import clock_landings as CL
add=CL.network_lane_cycles(a);lanes=a.setdefault("latency",{}).setdefault("lanes",{})
for lid,n in add.items():
    L=lanes.get(lid)
    if L is None:raise SystemExit(f"lane {lid} has no latency row")
    if L.get("clock_landing"):raise SystemExit(f"lane {lid} already priced")
    L["clock_landing"]=n;L["cycles"]=int(L["cycles"])+n;L["natural"]=int(L.get("natural",L["cycles"]-n))+n
print("priced lanes",len(add),"cycles",sum(add.values()))
(D/"die_plan_cland_r3.json").write_text(json.dumps(a,indent=1)+"\n")
(O/"landing_placement_table.json").write_text(json.dumps(b,indent=1)+"\n")
rp=D/"dcal_rom/bind/position2144b19/recipe_kv_2350.json";r=json.loads(rp.read_text())
lineage=b["collector"]["types"]
def expand(names):
    out=[]
    for n in names:
        hits=sorted(tn for tn,i in lineage.items() if tn==n or i["base_type"]==n)
        if not hits:raise SystemExit(f"recipe type {n} has no cohort")
        out+=hits
    return out
r["inner_uniform"]=expand(r["inner_uniform"])
r["clock_landing_table"]=str(O/"landing_placement_table.json")
r["clock_landing_note"]="KV-LAND-R3: 662 c3t crossings landed (+3 data cycles each); hard PHY rings in the soft wrapper; observer hub_C u_seq_u_core hf/lp_run"
(rp.parent/"recipe_kv_2350_cland_r3.json").write_text(json.dumps(r,indent=1)+"\n")
print("types",len(p["partition_types"]),"->",len(a["partition_types"]),"crossings",len(b["ports"]),"bands_failed",len(b["collector"]["placement_failures"]),
      "monitor_max_hop",round(b["collector"]["max_die_hop_um"],1),"inner_uniform",r["inner_uniform"])
