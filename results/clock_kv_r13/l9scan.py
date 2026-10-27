import json,sys,collections
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/clock-kv-r13/tools/die_plan")
import schema as S
raw=json.load(open("plan_r12.json")); raw.pop("plan_deltas",None); P=S.Plan(raw)
rects=[]
for pn,p in P.parts.items():
  for c in P.types[p["type"]].get("hard_cores",[]):
    import die_clock_mesh as D
    w,h=c["outline_um"]
    a=D.core_frame(P,pn,c,(0,0),inverse=True); b=D.core_frame(P,pn,c,(w,h),inverse=True)
    rects.append((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]),c["module"]))
m=json.load(open(sys.argv[1]))
lv=int(sys.argv[2])
rows=[(tuple(h["a"]),tuple(h.get("branch") or h["b"])) for h in m["htree"] if h["level"]==lv and not h.get("leaf")]
print(len(rows))
for d in [x*2.16 for x in range(0,148,4)]:
  c=collections.Counter()
  for a,k in rows:
    ax=0 if abs(a[0]-k[0])>abs(a[1]-k[1]) else 1
    sg=1 if a[ax]>=k[ax] else -1
    q=list(k); q[ax]+=sg*d
    hit=[r[4] for r in rects if r[0]<=q[0]<=r[2] and r[1]<=q[1]<=r[3]]
    c[hit[0] if hit else "-"]+=1
  print(round(d,2), dict(c))
