#!/usr/bin/env python3
"""DIE-QC-38 GEOM REQ render: ot_clk leaf-driver placements on the QC provider (die-qc37/leaf_fixed_rf)."""
import json, sys, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D='/srv/opentallas-scratch2/claude/die-qc37/leaf_fixed_rf/'; OUT=sys.argv[1]
cl=json.load(open(D+'leaf_clusters.json'))['clusters']
inv=json.load(open(D+'provider_cells_leaf.json'))
pl=json.load(open(D+'placements_leaf.json')); dbu=pl['dbu']
place={c['inst']:c for c in pl['cells']}
pg=json.load(open('/srv/opentallas-scratch2/claude/die-qc37/prebuild_e3_R7/pg_rects.json'))
cells=inv['cells'] if isinstance(inv,dict) else inv
byclk=collections.defaultdict(list)
for c in cells:
    if c.get('sequential'):byclk[c['connections']['CLK'][0]].append(c['inst'])
leafout={}
for c in cells:
    if c['inst'] in place and c['master'].startswith('CKINVDCx16'):
        leafout[tuple(place[c['inst']]['bbox_dbu'])]=[b for p,b in c['connections'].items() if c['directions'][p]=='output'][0][0]
bybit={k['cluster']:byclk.get(leafout.get(tuple(k['leaf_cell'])),[]) for k in cl}
print('mapped clusters',sum(1 for v in bybit.values() if v),'ffs',sum(len(v) for v in bybit.values()))
s=lambda r:[v/dbu for v in r]
def panel(ax,box,title):
    x0,y0,x1,y1=box
    for r in pg:
        if r[1]=='M8' and r[3]<y1 and r[5]>y0:
            ax.add_patch(Rectangle((x0,r[3]),x1-x0,r[5]-r[3],color='orange' if r[0]=='VDD' else 'khaki',alpha=.35,lw=0))
    for k in cl:
        t=s(k['trunk_cell']);l=s(k['leaf_cell'])
        if not (x0<=l[0]<=x1 and y0<=l[1]<=y1):continue
        ffs=[s(place[i]['bbox_dbu']) for i in bybit.get(k['cluster'],[]) if i in place]
        for f in ffs:
            ax.add_patch(Rectangle((f[0],f[1]),f[2]-f[0],f[3]-f[1],fc='0.75',ec='0.4',lw=.3))
            ax.plot([(l[0]+l[2])/2,(f[0]+f[2])/2],[(l[1]+l[3])/2,(f[1]+f[3])/2],color='tab:blue',lw=.4)
        ax.add_patch(Rectangle((l[0],l[1]),l[2]-l[0],l[3]-l[1],fc='tab:blue',ec='k',lw=.4))
        ax.add_patch(Rectangle((t[0],t[1]),t[2]-t[0],t[3]-t[1],fc='tab:red',ec='k',lw=.4))
        ax.plot([(t[0]+t[2])/2,(l[0]+l[2])/2],[(t[1]+t[3])/2,(l[1]+l[3])/2],color='tab:red',lw=.6)
    ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.set_title(title,fontsize=8)
fig,axs=plt.subplots(2,2,figsize=(14,14))
ax=axs[0][0]
xs=[(k['leaf_cell'][0])/dbu for k in cl];ys=[(k['leaf_cell'][1])/dbu for k in cl];hp=[k['leaf_hpwl_um'] for k in cl]
sc=ax.scatter(xs,ys,c=hp,s=3,cmap='viridis',vmax=30);fig.colorbar(sc,ax=ax,label='leaf HPWL um');ax.set_aspect('equal')
ax.set_title(f'all {len(cl)} clusters (leaf cell position), colour = leaf HPWL',fontsize=8)
w=max(cl,key=lambda k:k['leaf_hpwl_um']);c0=cl[0]
def around(k,r):
    x,y=k['centroid'][0]/dbu,k['centroid'][1]/dbu;return (x-r,y-r,x+r,y+r)
panel(axs[0][1],around(c0,15),f'cluster 0 ({c0["net"]}) +-15 um: red=trunk-side x5p33, blue=leaf x16, grey=FF, M8 PG bands')
panel(axs[1][0],around(w,50),f'worst leaf HPWL cluster {w["cluster"]} ({w["net"]}, {w["leaf_hpwl_um"]} um) +-50 um')
med=sorted(cl,key=lambda k:-k['ffs'])[0]
dense=max(collections.Counter((int(k['centroid'][0]/dbu/40),int(k['centroid'][1]/dbu/40)) for k in cl).items(),key=lambda t:t[1])[0]
panel(axs[1][1],(dense[0]*40,dense[1]*40,dense[0]*40+40,dense[1]*40+40),f'densest 40x40 um bin {dense}')
fig.tight_layout();fig.savefig(OUT,dpi=130)
print('LEAF_RENDER',OUT,'worst',w['cluster'],w['net'],w['leaf_hpwl_um'],'dense',dense)
