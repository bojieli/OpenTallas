import json,sys,math,collections,copy,shutil,array
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-s81-die-1351/tools/die_plan')
import die_clock_mesh as D,die_clock as DC,schema as S
B=Path('/srv/opentallas-scratch2/claude/codex-s81-graded-1351/p128_bankrepair');O=B.parent/'p128_stage18';O.mkdir(exist_ok=True)
P=S.Plan(S.load('/srv/opentallas-scratch2/claude/codex-s81-pd14-0818/die_plan_phy_contents.json'));C=json.load(open(B/'place.json'));N=json.load(open(B/'nets.json'));M=json.load(open(B/'mesh.json'));ko=list(DC.keepouts(P))+D.ft_halo_keepouts(P);repairs=[]
def solve(points,reps,src,dst):
 lens=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:])];L=sum(lens);nseg=len(reps)+1;mx=405-1.566;mn=8.64
 if L>nseg*mx+1e-6:return None,dict(reason='path_longer_than_existing_stage_budget',length=L,budget=nseg*mx)
 K=DC.KeepIndex(ko,die=(P.W,P.H))
 for n,c in C.items():
  if n not in reps:D.reserve_cell(K,n,c)
 candidates=[];progress=0.
 for a,b,l in zip(points,points[1:],lens):
  if not l:continue
  steps=math.ceil(l/.27)
  for j in range(1,steps+1):
   d=min(l,j*.27);x=D.snap(a[0]+(b[0]-a[0])*d/l,D.SITE_X);y=D.snap(a[1]+(b[1]-a[1])*d/l,D.ROW_Y);s=progress+d
   if s>=L-mn or s<mn:continue
   if not D.hitf(K,(x+.81,y+.135)):candidates.append((s,x,y))
  progress+=l
 A=sorted(set(candidates));s=[p[0] for p in A];count=len(A);inf=float('inf');dp=[inf]*count;backs=[]
 for i,v in enumerate(s):
  if v<=mx+1e-6 and L-v<=(nseg-1)*mx+1e-6:dp[i]=(v-L/nseg)**2
 backs.append(array.array('i',[-1])*count)
 for stage in range(2,nseg):
  cur=[inf]*count;back=array.array('i',[-1])*count;q=collections.deque();j=0
  for i,v in enumerate(s):
   while j<count and s[j]<=v-mn+1e-6:
    if dp[j]!=inf:
     while q and dp[q[-1]]>=dp[j]:q.pop()
     q.append(j)
    j+=1
   while q and s[q[0]]<v-mx-1e-6:q.popleft()
   if q and L-v<=(nseg-stage)*mx+1e-6:cur[i]=dp[q[0]]+(v-stage*L/nseg)**2;back[i]=q[0]
  dp=cur;backs.append(back)
 options=[(dp[i]+((L-v)-L/nseg)**2,i) for i,v in enumerate(s) if mn-1e-6<=L-v<=mx+1e-6 and dp[i]!=inf]
 if not options:return None,dict(reason='no_free_fixed_stage_chain',length=L,candidates=count,stages=nseg)
 cost,i=min(options);chosen=[]
 for stage in range(nseg-2,-1,-1):chosen.append(A[i]);i=backs[stage][i]
 chosen.reverse();new={r:dict(C[r],x=a[1],y=a[2]) for r,a in zip(reps,chosen)};cc=dict(C,**new);fail=D.actual_clock_hop_violations(cc,[dict(name='x',drv=a,loads=[b]) for a,b in zip([src]+reps,reps+[dst])],405)
 if fail:return None,dict(reason='post_pin_hop_fail',fail=fail)
 return new,dict(cost=cost,length=L,candidates=count,stages=nseg,path=points)

for e in [e for e in M["htree"] if e["tag"] in ["h00","h01","h10","h11"]]:
 tag=e["tag"];reps=[r["cell"] for r in e["reps"]]
 incoming={ld:n["drv"] for n in N["nets"] for ld in n["loads"]};outgoing={n["drv"]:n["loads"] for n in N["nets"]}
 src=incoming[reps[0]];dst=outgoing[reps[-1]][0];a=(C[src]["x"],C[src]["y"]);b=(C[dst]["x"],C[dst]["y"])
 extra="ckm_r2_"+tag+"_17";C[extra]=dict(C[reps[-1]]);reps.append(extra)
 routes=[("straight",[a,(a[0],b[1]),b])]
 for q in D.hard_keepout_violations(P,C):
  if q["cell"] not in reps:continue
  r=q["keepout_um"]
  for x in [D.snap(r[0]-5.94,D.SITE_X),D.snap(r[2]+4.32,D.SITE_X)]:routes.append(("side_channel",[a,(x,a[1]),(x,b[1]),b]))
 result=None;tried=[]
 for label,points in routes:
  new,rec=solve(points,reps,src,dst);tried.append(dict(label=label,**rec));print(tag,label,rec,flush=True)
  if new is not None:result=new;break
 if result is None:del C[extra];repairs.append(dict(tag=tag,failed=True,tried=tried));continue
 C.update(result);oldlast=reps[-2]
 for n in N["nets"]:
  if n["drv"]==oldlast:n["loads"]=[extra if v==dst else v for v in n["loads"]]
 N["nets"].append(dict(name="ck_"+extra,drv=extra,loads=[dst]));e["reps"].append(dict(cell=extra));e["n_seg"]=18;repairs.append(dict(tag=tag,added_cell=extra,tried=tried))
hard=D.hard_keepout_violations(P,C);hops=D.actual_clock_hop_violations(C,N["nets"],405);over=D.placement_overlaps(C);ft=D._body_keepout_violations(DC.KeepIndex(D.ft_halo_keepouts(P)),P.W,P.H,C);uniform=all(not r.get("failed") for r in repairs)
report=dict(status="BLOCKED" if hard or hops or over or ft or not uniform else "PLACEMENT_READY_PENDING_METAL",hardbody=len(hard),actual_pin_hops=len(hops),overlaps=len(over),ft_halos=len(ft),balanced_all_four_level2=uniform,repairs=repairs,qualified_timing=False)
M["meta"]["stage18_repair"]=report;M["clock_hard_keepout_violations"]=hard;M["clock_actual_hop_violations"]=hops
for fn in ["graded_metal.json","banks.json"]:shutil.copyfile(B/fn,O/fn)
for fn,obj in [("mesh.json",M),("place.json",C),("nets.json",N),("REPAIR.json",report),("body_failures.json",hard),("hop_failures.json",hops)]: (O/fn).write_text(json.dumps(obj,separators=(",",":"))+"\n")
D.write_verilog(C,N["nets"],N["ports"],O/"ctree.v");print({k:v for k,v in report.items() if k!="repairs"},flush=True)
