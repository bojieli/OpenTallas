# DIE-QC-8 estimate: decompose trial4 routed (pad-removed) region spread into core-insertion vs local-tree parts.
import json,statistics,sys,collections
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028")
T=json.load(open(R/"clockbuild/trial4_pad/clock/tree.json"));reg=json.load(open(R/"build_inputs/part_region.json"))["part_region"]
sys.path.insert(0,str(R/"source_tree/tools/die_plan"));import schema as S
P=S.Plan(json.load(open(R/"build_inputs/event/qc_k2b_phase12.json")))
contracts={(p,n):tp for p,pp in P.parts.items() for n,_,_,tp in S.core_taps(P,pp["type"])}
out={}
for c in ["TT","FF"]:
  nl={};tl={}
  for l in open(R/f"c1_{c}/arr_{c}.txt"):
    f=l.split()
    if f[0]=="N": nl[f[1]]=float(f[2])
    elif f[0]=="T": tl[f[1]]=float(f[2])
  com=S.common_latency_ps(P,c)
  rows={}
  for t in T["taps"]:
    path=t["path"];ps=[i for i,x in enumerate(path) if x.startswith("p")]
    delta=sum(nl[path[i]]-nl[path[i-1]] for i in ps)
    tp=contracts.get((t["part"],t["tap"]))
    lat=S.core_tap_insertion_ps(tp,c) if tp else com
    # region entry = first node on path whose region_root == this region
    g=reg[t["part"]]
    ent=None
    for x in path:
      if x.startswith("b"):
        nd=T["nodes"][x[1:]]
        if nd.get("region_root")==g: ent=x;break
    tree=tl[t["port"]]-delta
    rows[t["port"]]=dict(part=t["part"],tap=t["tap"],type=P.parts[t["part"]]["type"],lat=lat,tree=tree,ent=ent,ent_arr=nl.get(ent) if ent else None,core=bool(tp),base=tree+lat)
  out[c]=dict(com=com,rows=rows)
json.dump(out,open("/tmp/qc8_est_rows.json","w"))
print("ok")
