#!/usr/bin/env python3
# HEAD-R18 11-24 copy of epyc10 head-start-r18/start_reset.py (HEAD-START-R16); M = a composed tool tree (M/tools).
"""HEAD-START-R16: site each emitted START stage reset on the nearest EXISTING declared type raw export
(plan reset_start_raw_exports rows: no new type port, no type RTL change), in head_start_reset_exports.plan_exports form,
then head_start_local_reset.patch (settle = max(prev 88, span + 4)).  usage: start_reset.py M PLAN STAGES_DIR OUT"""
import json,sys,copy
from pathlib import Path
M,PLAN,SD,OUT=sys.argv[1:5]
sys.path[:0]=[M+"/tools/die_plan",M+"/tools/s81_head"]
import schema as S, reset_tree as R, head_start_local_reset as LR
P=S.Plan(S.load(PLAN),Path(PLAN)); wf=R.wf_plan(P)
stages=json.load(open(SD+"/start_stages.json"))
cands=[]
for pn,p in sorted(P.parts.items()):
    tn=p["type"]; rows=P.types[tn].get("reset_start_raw_exports",[])
    if not rows: continue
    t=R.for_type(P,tn); rel={r["name"]:r for r in (R.start_relays(t) if t.get("start") else t["relays"])}
    for row in rows:
        r=rel.get(row["instance"])
        if r is None or r["q"]!=row["net"]: raise SystemExit(f"{tn}.{row[port]}: declared export {row[instance]}/{row[net]} not a relay q of the tree")
        release=wf["parts"][pn]["release"]-R.release_clocks(t)+R.entry_stages(t)+r["depth"]
        c=dict(part=pn,type=tn,instance=row["instance"],net=row["net"],xy_um=list(P.to_die(pn,r["xy"])),local_xy_um=list(r["xy"]),raw_release=release,port=row["port"])
        if row.get("existing_port"): c["existing_port"]=row["existing_port"]
        cands.append(c)
sel=[];over=[]
for st in stages["stages"]:
    xy=st["clock_pin_xy_um"]; dist=lambda c:sum(abs(a-b) for a,b in zip(xy,c["xy_um"]))
    c=min(cands,key=lambda q:(dist(q),q["part"],q["port"])); d=dist(c)
    sel.append(dict(stage=st["id"],stage_region=st["region"],clock_node=st["node_cell"],stage_xy_um=xy,source={k:v for k,v in c.items() if k!="existing_port"},hop_um=round(d,4),qualified=False))
    if d>405: over.append((st["id"],round(d,1)))
rootid=next(s["id"] for s in stages["stages"] if s["root"]); root=next(r for r in sel if r["stage"]==rootid)
relative=max(r["source"]["raw_release"]-root["source"]["raw_release"] for r in sel)
ex=dict(schema="ot_head_start_reset_exports/1",reset_form="local_wavefront_PROPOSED",stages=sel,
        summary=dict(stages=len(sel),max_hop_um=max(r["hop_um"] for r in sel),over_hop=over,root_raw_release=root["source"]["raw_release"],max_relative_raw_release=relative))
Path(OUT).mkdir(parents=True,exist_ok=False); json.dump(ex,open(OUT+"/exports.json","w"),indent=1)
print(json.dumps(dict(ex["summary"],over_hop=over[:10],candidates=len(cands),used_exports=len({(r["source"]["part"],r["source"]["port"]) for r in sel}))))
if over and "--bench-allow-over" not in sys.argv: sys.exit(2)
if over: ex["summary"]["over_hop_open"]=over; ex["summary"]["over_hop"]=[]; json.dump(ex,open(OUT+"/exports.json","w"),indent=1)  # OPEN physical item: bench-only allowance
settle=max(88,relative+4)
doc,sv=LR.patch(stages,Path(SD+"/start_stages.sv").read_text(),ex,settle)
json.dump(doc,open(OUT+"/start_stages.json","w"),indent=1); open(OUT+"/start_stages.sv","w").write(sv)
for n in ("ctree.v","ctree.tcl"):
    if Path(SD+"/"+n).exists(): Path(OUT+"/"+n).write_bytes(Path(SD+"/"+n).read_bytes())
print(json.dumps(dict(settle=settle,reset_ports=len(doc["reset_ports"]),guard=doc["root_settle_guard"])))
