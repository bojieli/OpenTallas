# DIE-S81-26: Codex codex-bf-enable-0255/pack.py unchanged in logic, paths as args: SLICE SITES OUTJSON OUTTSV
import json,hashlib,sys
from pathlib import Path
import core_plan_to_infra as C
import core_infra as I
sl_p,si_p,oj,ot=map(Path,sys.argv[1:5])
sites=C.read_sites(si_p);layout=C.SiteMap(sites)
sl=json.loads(sl_p.read_text());plan=I.compile_slice(sl)
gates=plan["core_tree"]["gates"];orig_pins={}
for g in gates:
 if "clone_of" in g:orig_pins.setdefault(g["clone_of"],set()).update(g["enable_pins"])
items=[]
for g in gates:
 orig=g.get("clone_of",g["inst"]);pins=sorted(orig_pins.get(orig,()))
 assert pins and all(p not in (g["clk_pin"],g["out_pin"]) for p in pins)
 for pin in pins:
  name=f"bf_g2_ctl_{len(items):04d}"
  q=layout.place(name,"BUFx2_ASAP7_75t_R",*g["xy_um"],max_um=20)
  items.append(dict(name=name,master="BUFx2_ASAP7_75t_R",target=g["inst"],target_master=g["master"],source=orig,pin=pin,clk_pin=g["clk_pin"],out_pin=g["out_pin"],**q))
report=dict(schema="opentallas.bf_g2_control_isolation.v1",source_slice_sha256=hashlib.sha256(sl_p.read_bytes()).hexdigest(),native_sites_sha256=hashlib.sha256(si_p.read_bytes()).hexdigest(),clock_cells=len(plan.get("cells",[])),changed_clock_cells=0,added_control_buffers=len(items),added_cycles=0,max_target_distance_um=max(q["displacement_um"] for q in items),outline_um=sl["outline_um"],buffers=items)
oj.write_text(json.dumps(report,indent=1)+"\n")
with open(ot,"w") as f:
  f.write("# from %s source_slice %s\n"%(report["schema"],report["source_slice_sha256"]))
  for b in items: f.write("\t".join([b["name"],b["target"],b["pin"],"%.4f"%b["origin_um"][0],"%.4f"%b["origin_um"][1],b["orient"]])+"\n")
print({k:v for k,v in report.items() if k!="buffers"},flush=True)
