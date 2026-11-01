"""HBM-HUBMESH-3 task 3 estimate: deliver each plan early core tap from the pre-mesh tree instead of the mesh.
For every early core tap (plan early_ps TT>0): target TT arrival = mesh arrival(tap) - early_TT.  Candidate source =
every pre-mesh cell output (routed GRT-RC TT arrival from tree_grt_TT.txt).  Branch delay = stage model (pilot v2
stage_model, BUFx24 chain, repeaters every rep_max_um) over the Manhattan distance source->tap.  Pick the source
minimizing |residual|; report residual, distance, stages.  Diagnostic estimate (UNCHECKED: no tree load perturbation)."""
import json,sys,math,itertools
W=sys.argv[1]; proof,pilot,tree,plan,part,cfg=sys.argv[2:8]
sys.path.insert(0,W+'/tools/die_plan'); import die_sta_related as DSR, yaml
TT={t['port']:t for t in json.load(open(proof+'/tap_arrivals_TT.json'))['taps']}
FF={t['port']:t for t in json.load(open(proof+'/tap_arrivals_FF.json'))['taps']}
P=json.load(open(plan)); ecm=DSR.early_core_map(P,TT,plan_path=plan)
eTT={p:m[0]['early_ps']['TT'] for p,m in ecm.items()}; eFF={p:m[0]['early_ps']['FF'] for p,m in ecm.items()}
pj=json.load(open(pilot)); g=pj['geom']; cells=pj['cells']
arr={}
for l in open(tree):
    f=l.split()
    if f[0]=='Y': arr[f[1]]=float(f[3])
C=yaml.safe_load(open(cfg)); G=C['region']['mesh']['grid']; sm=G['stage_model']; rep=float(G['rep_max_um'])
d=sm['delay']
def stage(Lk,Lt,fo2=1,sin=60.0): return d[0]+d[1]*Lt+d[2]*Lk*Lk+d[3]*Lk+d[4]*fo2+d[5]*Lt*Lt+d[6]*sin
def chain(L):
    k=max(1,math.ceil(L/rep)); s=L/k
    return sum(stage(s,s) for _ in range(k)),k
src=[(n,arr[n],(cells[n]['x']+0.81,cells[n]['y']+0.135)) for n in arr if n in cells and not n.startswith('M') and not n.startswith('L_')]
rows=[]
TOL=float(__import__('os').environ.get('TOL','5'))
for p,e in sorted(eTT.items(),key=lambda kv:-kv[1]):
    if e<=0: continue
    t=TT[p]; tx,ty=t['xy_um'][0]-g['origin'][0],t['xy_um'][1]-g['origin'][1]
    target=t['late_ps']-e
    best=None
    for n,a,(x,y) in src:
        L=abs(x-tx)+abs(y-ty); dl,k=chain(L); r=a+dl-target
        c=L+10.0*max(0.0,-r)
        if r<=TOL and (best is None or c<best[4]): best=(r,n,L,k,c)
    # pad = -r ps of snake/detour (ledgered residual tool); pad length at ~0.06 ps/um marginal (stage model d1) is UNCHECKED
    rows.append((p,round(e,1),round(eFF[p],1),round(t['late_ps'],1))+(round(best[0],1),best[1],round(best[2]),best[3],round(-min(best[0],0),1)))
for r in rows: print(*r)
res={r[0]:r[4] for r in rows}
print('early taps',len(rows),'pad needed max %.1f ps total %.0f'%(max(-v for v in res.values()),sum(max(0,-v) for v in res.values())),'branch um total %d max %d'%(sum(r[6] for r in rows),max(r[6] for r in rows)),'extra stages',sum(r[7] for r in rows))
for p in res: res[p]=0.0   # after pad: residual = model error only (routed leg error sd 5 ps, HUBMESH-2 a3r fit)
# needed-W what-if (FF ~ TT x 0.8666): delivered taps arrive at mesh - early + residual
f=0.8666
A={p:FF[p]['late_ps'] for p in FF}
for p,v in res.items(): A[p]=A[p]-eFF[p]+v*f
dm=[A[b]-A[a]+eFF.get(b,0)-eFF.get(a,0) for a,b in itertools.permutations(A,2)]
print('needed W with early branches (FF what-if) %.1f ps'%max(dm), {w:sum(x>w for x in dm) for w in (40,60,80,120,160)})
