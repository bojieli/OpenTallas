import sys,os,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
# render.py probe_dir stage(rcx|cts) title out.png [hl_inst ...]
D,st,title,out=sys.argv[1:5]; hl=sys.argv[5:]
ck={}
for l in open(f'{D}/ck_rcx_tt.tsv' if os.path.exists(f'{D}/ck_rcx_tt.tsv') else f'{D}/ck_{st}_tt.tsv'):
    p=l.rstrip('\n').split('\t'); ck[p[0].rsplit('/',1)[0]]=(float(p[1]),float(p[2]),float(p[3]),p[4])
insts={}
for l in open(f'{D}/insts_{st}.tsv'):
    p=l.rstrip('\n').split('\t')
    if len(p)==6: insts[p[0]]=(p[1],*map(float,p[2:6]))
fig,ax=plt.subplots(figsize=(16,9) if True else None,dpi=110)
X=max(v[3] for v in insts.values()); Y=max(v[4] for v in insts.values())
# hold/buffer density: BUF (non-clock) cells
hb=[(v[1],v[2]) for k,v in insts.items() if v[0].startswith(('BUFx2','HB')) and 'clk' not in k]
if hb: ax.scatter([a for a,b in hb],[b for a,b in hb],s=0.3,c='#bbbbbb',label=f'data BUFx2/HB {len(hb)}',zorder=1)
for k,v in insts.items():
    if v[0].startswith('ot_sram'):
        ax.add_patch(Rectangle((v[1],v[2]),v[3]-v[1],v[4]-v[2],fc='#ffe0a0',ec='k',lw=1.2,zorder=2)); ax.text(v[1]+2,v[2]+2,k,fontsize=8)
xs=[v[0] for v in ck.values()]; ys=[v[1] for v in ck.values()]; cs=[v[2] for v in ck.values()]
sc=ax.scatter(xs,ys,c=cs,s=1.2,cmap='turbo',vmin=min(cs),vmax=max(cs),zorder=3)
cb=fig.colorbar(sc,ax=ax,fraction=0.025); cb.set_label('register CK arrival TT (ps)')
# tree: non-leaf clock nets
segs=[];lsegs=[]
for l in open(f'{D}/cknets_{st}.tsv'):
    p=l.rstrip('\n').split('\t')
    if len(p)<3 or not p[1]: continue
    _,m,xy=p[1].split('@'); x0,y0=map(float,xy.split(','))
    sk=[tuple(map(float,s.split(','))) for s in p[2].split()] if p[2] else []
    leaf='leaf' in p[0]
    for s in sk: (lsegs if leaf else segs).append([(x0,y0),s])
ax.add_collection(LineCollection(lsegs,colors='#66666655',linewidths=0.2,zorder=4))
ax.add_collection(LineCollection(segs,colors='m',linewidths=0.9,zorder=5))
for h in hl:
    for k,v in ck.items():
        if k.replace('\\','')==h or k==h:
            ax.plot(v[0],v[1],'k*',ms=12,zorder=7); ax.annotate(f'{h} {v[2]:.0f}',(v[0],v[1]),fontsize=8,zorder=8)
ax.set_xlim(0,X+2);ax.set_ylim(0,Y+2);ax.set_aspect('equal')
ax.set_title(title,fontsize=10); ax.legend(loc='upper right',fontsize=7,markerscale=8)
fig.savefig(out,bbox_inches='tight'); print('wrote',out)
