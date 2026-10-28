# DIE-QC-8: residual pads needed on trial6 (measured) to reach spread + ocv_est <= 150 at TT and FF (pads delay early taps)
import json,collections,math,sys
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc8-1028");R=Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028")
sys.path.insert(0,str(R/"source_tree/tools/die_plan"));import schema as S
P=S.Plan(json.load(open(R/"build_inputs/event/qc_k2b_phase12.json")))
T=json.load(open(Q/"trial6/clock/tree.json"));reg=json.load(open(R/"build_inputs/part_region.json"))["part_region"]
sp=json.load(open(Q/"trial6_spread.json"))["regions"]
con={(p,n):tp for p,pp in P.parts.items() for n,_,_,tp in S.core_taps(P,pp["type"])}
step={"TT":24.019,"FF":18.572}
b={}
for c in ["TT","FF"]:
  tl={l.split()[1]:float(l.split()[2]) for l in open(Q/f"c6_{c}/arr_{c}.txt") if l.startswith("T ")}
  com=S.common_latency_ps(P,c)
  for t in T["taps"]:
    tp=con.get((t["part"],t["tap"]));b[(c,t["port"])]=tl[t["port"]]+(S.core_tap_insertion_ps(tp,c) if tp else com)
G=collections.defaultdict(list)
for t in T["taps"]: G[reg[t["part"]]].append(t["port"])
K=lambda g:"c" if g.startswith("c_") else ("su_c" if g.endswith("su_c") else "other")
need={};
for g,ps in G.items():
  for c in ["TT","FF"]:
    W=150-sp[c][g]["ocv_est"];mx=max(b[(c,p)] for p in ps)
    for p in ps:
      gap=mx-W-b[(c,p)]
      if gap>0: need[p]=max(need.get(p,0),math.ceil(gap/step[c]))
cnt=collections.Counter();pads=collections.Counter();tot=collections.Counter()
for g,ps in G.items():
  tot[K(g)]+=len(ps)
  for p in ps:
    if p in need: cnt[K(g)]+=1;pads[K(g)]+=need[p]
for k in tot: print(k,"taps",tot[k],"padded",cnt[k],"pads",pads[k])
print("TOTAL padded",sum(cnt.values()),"/",sum(tot.values()),f"{100*sum(cnt.values())/sum(tot.values()):.2f}%","pads",sum(pads.values()),"max",max(need.values()) if need else 0)
json.dump({"pad":need},open(Q/"trial6_residual_pads.json","w"),indent=1)
