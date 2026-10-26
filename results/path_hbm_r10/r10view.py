import sys,json
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/path-hbm-r10-1026/tools/die_plan')
import plan_cut as PC
base=json.load(open('/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json'))['partition_types']['q_hub_nw']
v1=json.load(open(sys.argv[1]+'/die_plan.json'))['partition_types']['q_hub_nw']; lab1=sys.argv[2]
rep=json.load(open(sys.argv[1]+'/r10_delta_report.json'))['hubs']['q_hub_nw']
def prof(t):
  W,H=t['outline_um']; nets=PC._nets(t); cores=PC._cores(t)
  X=np.arange(4.32,W-1e-6,4.32); dx=np.zeros(len(X)); dc=np.zeros(len(X))
  for n in nets:
    a=n['pts'][0]; mx=np.zeros(len(X))
    for p,b in zip(n['pts'][1:],n['sink_bits']): mx=np.maximum(mx,np.where((X>min(a[0],p[0]))&(X<max(a[0],p[0])),b,0))
    dx+=mx
    if not n['face']: dc+=mx
  bx=np.zeros(len(X))
  for (x0,y0,x1,y1) in cores.values(): bx[(X>x0)&(X<x1)]+=min(y1,H)-max(y0,0)
  bx=np.minimum(bx,H); cx=(H-bx)*.75/.048+H*.75/.064
  return X,dx/cx,dc/cx
fig,ax=plt.subplots(3,1,figsize=(16,15),gridspec_kw=dict(height_ratios=[1.3,1.6,1]))
for a,t,ttl in ((ax[0],base,'BASE q_hub_nw (b1e2+banks k4/4), census cross-product face stations (sample 1/6)'),(ax[1],v1,lab1)):
  W,H=t['outline_um']
  for h in t['hard_cores']:
    x,y=h['origin_um']; w,hh=h['outline_um']
    a.add_patch(plt.Rectangle((x,y),w,hh,fc='tab:orange' if '__q' in h['inst'] else 'tab:blue',alpha=.45,ec='k',lw=.4))
    a.text(x+w/2,y+hh/2,h['module'].replace('ot_','').replace('hbm_','')[:13],fontsize=4,ha='center')
  for i,s in enumerate(t['internal_stations']):
    f=[p for p in (s['from_um'],s['to_um']) if p[1]<=.5 or p[1]>=H-.5]
    if not f or (t is base and i%6): continue
    a.plot([s['from_um'][0],s['to_um'][0]],[s['from_um'][1],s['to_um'][1]],color='g',lw=.15+min(1.5,s['bits']/1500),alpha=.5)
  for b in rep.get('bounds_um',[]): 
    if t is v1: a.axvline(b,color='r',ls='--')
  a.set_xlim(0,W); a.set_ylim(0,H); a.set_aspect('equal'); a.set_title(ttl,fontsize=9)
for t,c,l in ((base,'tab:gray','base'),(v1,'tab:blue','R10')):
  X,u,uc=prof(t); ax[2].plot(X,u,color=c,label=f'{l} total per-sink x-cut (max {u.max():.2f})'); ax[2].plot(X,uc,color=c,ls=':',label=f'{l} core-core only (max {uc.max():.2f})')
ax[2].axhline(.6,color='r'); ax[2].legend(fontsize=8); ax[2].set_xlabel('x um'); ax[2].set_ylabel('x-cut use (M4-M7, blocked, PG .25)')
plt.tight_layout(); plt.savefig(sys.argv[3],dpi=110)
