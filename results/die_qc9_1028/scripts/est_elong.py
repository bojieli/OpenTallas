# DIE-QC-9 ESTIMATE: su_c wire elongation (plan-computed DME snake) needed per region, from trial6 routed arrivals.
# deficit(tap) = target - (arrival + core insertion); allot hierarchically: each node takes min deficit of its subtree
# (minus what ancestors took) -> snake wire on the leg INTO that node = allot / (ps per um of elongated buffered leg).
import json,collections,statistics as st,sys,math
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc8-1028");R=Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028")
sys.path.insert(0,str(R/"source_tree/tools/die_plan"));import schema as S
P=S.Plan(json.load(open(R/"build_inputs/event/qc_k2b_phase12.json")))
T=json.load(open(Q/"trial6/clock/tree.json"));reg=json.load(open(R/"build_inputs/part_region.json"))["part_region"]
contracts={(p,n):tp for p,pp in P.parts.items() for n,_,_,tp in S.core_taps(P,pp["type"])}
N=T["nodes"]
MODEL_PS_UM=(20.8281+0.013984*250+0.00033554*250*250)/250   # leg_ps(250)/250, die_trial STAGE_1X_TT
RATIO={"TT":1.548,"FF":1.293}
WIN=float(sys.argv[1]) if len(sys.argv)>1 else 0.0
GRID=len(sys.argv)>2
out={}
for c in ["TT","FF"]:
  tl={}
  for l in open(Q/f"c6_{c}/arr_{c}.txt"):
    f=l.split()
    if f[0]=="T": tl[f[1]]=float(f[2])
  com=S.common_latency_ps(P,c)
  byreg=collections.defaultdict(list)
  for t in T["taps"]:
    g=reg[t["part"]]
    if not g.endswith("su_c"): continue
    tp=contracts.get((t["part"],t["tap"]));lat=S.core_tap_insertion_ps(tp,c) if tp else com
    if lat==com or not GRID: byreg[g].append((t["port"],t["node"],tl[t["port"]]+lat))
  ps_um=MODEL_PS_UM*RATIO[c]
  rows={}
  for g,L in sorted(byreg.items()):
    tgt=max(b for _,_,b in L)-WIN
    defi=collections.defaultdict(list)   # node -> deficits of taps below
    for port,nd,b in L:
      d=max(0.0,tgt-b);i=str(nd)
      while i is not None and N[i].get("dme")==g:
        defi[i].append(d);p=N[i]["parent"];i=str(p) if p is not None else None
    allot={}
    def take(i,above):
      m=min(defi[i]) if defi[i] else 0.0
      allot[i]=m-above
      for k in N[i]["kids"]:
        if str(k) in defi: take(str(k),m)
    roots=[i for i in defi if str(N[i]["parent"]) not in defi]
    for r in roots: take(r,0.0)
    legs=[v for v in allot.values() if v>1.0]
    wire=sum(legs)/ps_um
    x0,y0,x1,y1=N[roots[0]]["region"]
    rows[g]=dict(taps=len(L),spread=round(max(b for *_,b in L)-min(b for *_,b in L),1),snake_legs=len(legs),
                 snake_ps_sum=round(sum(legs),1),snake_um=round(wire,1),max_leg_snake_um=round(max(legs,default=0)/ps_um,1),
                 region_mm2=round((x1-x0)*(y1-y0)/1e6,3))
  out[c]=rows
for c in out:
  r=out[c];print(c,"window",WIN,"| snake um med/max/sum",st.median(v["snake_um"] for v in r.values()),max(v["snake_um"] for v in r.values()),round(sum(v["snake_um"] for v in r.values())),"| legs",sum(v["snake_legs"] for v in r.values()),"| max one leg",max(v["max_leg_snake_um"] for v in r.values()))
json.dump(out,open(f"/srv/opentallas-scratch2/claude/die-qc9-1028/est_elong_w{int(WIN)}{"_grid" if GRID else ""}.json","w"),indent=1)
print(json.dumps(out["TT"]["sl_E0_su_c"]))
