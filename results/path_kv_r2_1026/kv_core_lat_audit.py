"""PATH-KV-R2 audit (owner 06:3x): (A) KV core taps needing an early-tap offset (core insertion != die common
latency) and every hard-core type with its insertion vs 250 TT target; (B) die clock tree / repeater / pad / stub
cells of the c3e mesh that have no legal channel site (sit inside a partition outline)."""
import sys,json,collections
D,PLAN,TOOLS,OUT=sys.argv[1:5]; sys.path.insert(0,TOOLS)
import schema as S
P=S.Plan(S.load(PLAN))
res={"plan":PLAN,"common_latency_ps":{c:S.common_latency_ps(P,c) for c in ("TT","FF")}}
A=[];hc=[]
cnt=collections.Counter(p["type"] for p in P.parts.values())
for tn,t in sorted(P.types.items()):
  if tn not in cnt: continue
  if t.get("hard_cores"):
    hc.append(dict(type=tn,replicas=cnt[tn],hard_cores=[h.get("inst",h.get("name")) if isinstance(h,dict) else h for h in t["hard_cores"]][:8],core_taps=(t.get("clock",{}) or {}).get("core_taps"),contract=(t.get("clock_contract") or {}).get("kind") if isinstance(t.get("clock_contract"),dict) else t.get("clock_contract")))
  for port,x,y,tp in S.core_taps(P,tn):
    e={c:S.core_tap_early_ps(P,tp,c) for c in ("TT","FF")}; ins={c:S.core_tap_insertion_ps(tp,c) for c in ("TT","FF")}
    A.append(dict(type=tn,replicas=cnt[tn],port=port,tap=tp.get("core") or tp.get("name"),insertion_ps=ins,early_ps=e,needs_offset=any(v>0.01 for v in e.values())))
res["hard_core_types"]=hc; res["core_taps"]=A
res["early_offset_types"]=sorted({a["type"] for a in A if a["needs_offset"]})
cells=json.load(open(f"{D}/place.json"))
rects=[(n,P.rect(n)) for n in P.parts]
import numpy as np
inside=collections.Counter(); ex=collections.defaultdict(list)
for nm,c in cells.items():
  x,y=c["x"],c["y"]
  for n,r in rects:
    if r[0]<x<r[2] and r[1]<y<r[3]:
      inside[(P.parts[n]["type"],c["kind"])]+=1
      if len(ex[P.parts[n]["type"]])<3: ex[P.parts[n]["type"]].append([nm,c["kind"],n,round(x,1),round(y,1)])
      break
bytype=collections.defaultdict(dict)
for (tn,k),v in inside.items(): bytype[tn][k]=v
res["no_channel_site"]={"total_cells":sum(inside.values()),"of_cells":len(cells),"by_type":{tn:dict(kinds=v,replicas=cnt[tn],examples=ex[tn]) for tn,v in sorted(bytype.items())}}
json.dump(res,open(OUT,"w"),indent=1)
print(json.dumps({k:(v if k!="core_taps" else len(v)) for k,v in res.items()},indent=1)[:6000])
