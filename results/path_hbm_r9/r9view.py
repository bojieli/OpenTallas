import sys,json,collections
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/path-hbm-r9-1026/tools/die_plan')
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import hbm_r9_delta as D, plan_cut as PC
P=json.load(open('/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json'))
out={}
for tn in ('q_hub_nw','q_hub_ne'):
  t=P['partition_types'][tn]; W,H=t['outline_um']
  a0=sum(h['outline_um'][0]*h['outline_um'][1] for h in t['hard_cores'])
  out[tn]=dict(core_mm2=round(a0/1e6,3),hub_mm2=round(W*H/1e6,3))
  for S in (2,3,4,8):
    Q=D.plan_quadrants(t,S); a=sum(h['outline_um'][0]*h['outline_um'][1] for h in Q['cores'])
    out[tn][f'S{S}']=dict(cores=len(Q['cores']),core_mm2=round(a/1e6,3),added_mm2=round((a-a0)/1e6,3),
       seg_core_mm2=round(a/S/1e6,3),seg_w_um=round(W/S,2),boundary_bits=D.boundary_bits(Q),
       hub_h_at_41pct_um=round(a/0.41/W,1))
print(json.dumps(out,indent=1))
json.dump(out,open('/srv/opentallas-scratch2/claude/path-hbm-r9-1026/area_table.json','w'),indent=1)
t=P['partition_types']['q_hub_nw']; W,H=t['outline_um']
Q=D.plan_quadrants(t,2); cores,st,infos,stats=D.realise(t,Q,3196.8,kx=8,route=False)
fig,ax=plt.subplots(3,1,figsize=(16,13),gridspec_kw=dict(height_ratios=[3,1,1]))
col=['tab:blue','tab:orange']
for h in cores:
  x,y=h['origin_um']; w,hh=h['outline_um']; k=Q['segof'][h['inst']]
  ax[0].add_patch(plt.Rectangle((x,y),w,hh,fc=col[k],alpha=0.35 if '__q' not in h['inst'] else 0.7,ec='k',lw=0.5))
  ax[0].text(x+w/2,y+hh/2,h['module'].replace('ot_','')[:14],fontsize=4,ha='center')
ax[0].axvline(W/2,color='r',ls='--'); ax[0].set_xlim(0,W); ax[0].set_ylim(0,3196.8); ax[0].set_aspect('equal')
ax[0].set_title('PATH-HBM-R9 q_hub_nw S=2 service quadrants (dark = replicated copy, light = distributed), H 3196.8 um, fill 0.55')
for i,(tt,lab) in enumerate(((t,'b1e2+banks (orig hub, H 2920)'),(dict(outline_um=[W,3196.8],hard_cores=cores,internal_stations=st),'R9 S=2 kx=8'))):
  for ax_i,axis in ((1,'x'),(2,'y')):
    WW,HH=tt['outline_um']; nets=PC._nets(tt); cr=PC._cores(tt)
    # profile
    import numpy as np
    X=np.arange(4.32,(WW if axis=='x' else HH)-1e-6,4.32)
    c=PC._cut_profile(WW,HH,nets,cr,per_sink=True)
    ax[ax_i].axhline(0.6,color='r'); ax[ax_i].set_ylabel(f'{axis}-cut max use')
    ax[ax_i].bar(i,c[axis]['max_use'],label=lab+f" {c[axis]['max_use']} at {c[axis]['at_um']}")
    ax[ax_i].legend(fontsize=7)
plt.tight_layout(); plt.savefig('/srv/opentallas-scratch2/claude/path-hbm-r9-1026/r9_quadrant_s2.png',dpi=110)
