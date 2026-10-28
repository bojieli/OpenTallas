# DIE-QC-9: trial11 routed clock-only GRT arrivals -> in-region spread of (tap arrival + declared core insertion), per class
import json,collections,statistics as st,sys
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc13-1028");R=Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028")
sys.path.insert(0,str(R/"source_tree/tools/die_plan"));import schema as S
P=S.Plan(json.load(open(R/"build_inputs/event/qc_k2b_phase12.json")))
T=json.load(open(Q/"trial11/clock/tree.json"));reg=json.load(open(R/"build_inputs/part_region.json"))["part_region"]
contracts={(p,n):tp for p,pp in P.parts.items() for n,_,_,tp in S.core_taps(P,pp["type"])}
ent={}
for i,n in T["nodes"].items():
  if n.get("region_root") is not None: ent.setdefault(n["region_root"],"b"+i)
out={}
for c in ["TT","FF"]:
  nl={};tl={}
  for l in open(Q/f"c11_{c}/arr_{c}.txt"):
    f=l.split()
    if f[0]=="N": nl[f[1]]=float(f[2])
    elif f[0]=="T": tl[f[1]]=float(f[2])
  com=S.common_latency_ps(P,c);G=collections.defaultdict(list)
  for t in T["taps"]:
    tp=contracts.get((t["part"],t["tap"]));lat=S.core_tap_insertion_ps(tp,c) if tp else com
    g=reg[t["part"]];G[g].append(dict(port=t["port"],tree=tl[t["port"]],lat=lat,e2t=tl[t["port"]]-nl.get(ent.get(g),tl[t["port"]])))
  rows={}
  for g,L in G.items():
    b=[x["tree"]+x["lat"] for x in L];tr=[x["tree"] for x in L if x["lat"]==com] or [0]
    e2t=max(x["e2t"] for x in L);ocv=0.062*e2t
    rows[g]=dict(n=len(L),spread=round(max(b)-min(b),1),grid_spread=round(max(tr)-min(tr),1),e2t_max=round(e2t,1),ocv_est=round(ocv,1),with_ocv=round(max(b)-min(b)+ocv,1))
  out[c]=rows
def kls(g): return "c" if g.startswith("c_") else ("su_c" if g.endswith("su_c") else g.split("_")[0])
summ={}
for c,rows in out.items():
  K=collections.defaultdict(list)
  for g,r in rows.items(): K[kls(g)].append(r)
  summ[c]={k:dict(regions=len(L),spread_med=round(st.median(x["spread"] for x in L),1),spread_max=max(x["spread"] for x in L),
     with_ocv_max=max(x["with_ocv"] for x in L),over150=sum(x["with_ocv"]>150 for x in L),e2t_max=max(x["e2t_max"] for x in L)) for k,L in sorted(K.items())}
  print(c);[print(" ",k,v) for k,v in summ[c].items()]
json.dump(dict(scope="DIE-QC-9 trial11 clock-only GRT (2W2S, 50 it) arrivals; spread = max-min of (tap late arrival + declared core insertion) per region; ocv_est = 0.062 x max entry->tap (UNCHECKED ratio from DIE-QC-6 c_* split), not the shared die STA model",summary=summ,regions=out),open(Q/"trial11_spread.json","w"),indent=1)
