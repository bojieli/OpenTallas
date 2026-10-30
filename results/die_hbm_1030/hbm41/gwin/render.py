#!/usr/bin/env python3
"""Render windowed GRT congestion (report entries, may be capped at 20k) + station cells + blockages, side by side."""
import sys,re,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np
sys.path.insert(0,__file__.rsplit('/',1)[0]); from cong_map import parse
out=sys.argv[1]; ds=sys.argv[2:]
fig,axs=plt.subplots(1,len(ds),figsize=(7*len(ds),7))
for ax,d in zip(np.atleast_1d(axs),ds):
    T=open(d+'/probe.tcl').read(); H=float(re.search(r'-die_area \{0 0 \S+ (\S+)\}',T).group(1))
    for m in re.finditer(r'create_blockage -region \{(\S+) (\S+) (\S+) (\S+)\}',T):
        a,b,c,e=map(float,m.groups()); ax.add_patch(plt.Rectangle((a,b),c-a,e-b,color='0.85'))
    xy=np.array([(float(m.group(1)),float(m.group(2))) for m in re.finditer(r'place_inst -name \S+ -location \{(\S+) (\S+)\}',T)])
    ax.scatter(xy[:,0],xy[:,1],s=0.05,c='tab:blue',alpha=0.4)
    v=parse(d+'/grt_congestion.rpt'); g=np.zeros((int(H//10)+1,84))
    for c in v:
        x=(c['bb'][0]+c['bb'][2])/2; y=(c['bb'][1]+c['bb'][3])/2; g[int(y//10),min(83,int(x//10))]+=c['ov']
    im=ax.imshow(np.ma.masked_where(g==0,g),origin='lower',extent=(0,840,0,(g.shape[0])*10),cmap='hot_r',alpha=0.8,vmax=np.percentile(g[g>0],99) if (g>0).any() else 1)
    ax.set_xlim(0,829.44); ax.set_ylim(0,H); ax.set_aspect('equal'); ax.set_title(f"{d.rstrip('/').split('/')[-1]} rpt entries {len(v)} sum {sum(c['ov'] for c in v)}",fontsize=9)
    plt.colorbar(im,ax=ax,fraction=0.03)
plt.tight_layout(); plt.savefig(out,dpi=110)
