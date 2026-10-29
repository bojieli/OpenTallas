import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pl=json.load(open(sys.argv[1]));g=json.load(open(sys.argv[2]));reach=json.load(open(sys.argv[3]));D=pl['dbu'];fig,ax=plt.subplots(1,3,figsize=(19,7));cells=pl['cells'];by={c['inst']:c for c in cells}
for kind,x,y,X,Y in g['hard_forbidden']:
 ax[0].add_patch(Rectangle((x/D,y/D),(X-x)/D,(Y-y)/D,facecolor='#d5dbe0',edgecolor='none',alpha=.4))
for seq,col,label in [(False,'#dc8d27','comb'),(True,'#1868b2','FF')]:
 cc=[c for c in cells if c['sequential']==seq];ax[0].scatter([(c['bbox_dbu'][0]+c['bbox_dbu'][2])/2/D for c in cc],[(c['bbox_dbu'][1]+c['bbox_dbu'][3])/2/D for c in cc],s=1,c=col,label=label)
ax[0].set(xlim=(0,g['die_dbu'][2]/D),ylim=(0,g['die_dbu'][3]/D),title=f'ALL {len(cells)} cells / {len({c["stage"] for c in cells})} stages',xlabel='um',ylabel='um');ax[0].set_aspect('equal');ax[0].legend()
stage='b0' if any(c['stage']=='b0' for c in cells) else cells[0]['stage'];root=[c for c in cells if c['stage']==stage];xr=min(c['bbox_dbu'][0] for c in root)/D;yr=min(c['bbox_dbu'][1] for c in root)/D;view=[xr-1,yr-1,xr+15,yr+3]
for n,m,x,y,X,Y in g['existing_cells']:
 r=[x/D,y/D,X/D,Y/D]
 if r[0]<view[2] and view[0]<r[2] and r[1]<view[3] and view[1]<r[3]:ax[1].add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],facecolor='#728089',alpha=.7))
for c in root:
 x,y,X,Y=[v/D for v in c['bbox_dbu']];ax[1].add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#1868b2' if c['sequential'] else '#dc8d27',edgecolor='white',linewidth=.3))
ax[1].set(xlim=(view[0],view[2]),ylim=(view[1],view[3]),title=f'{stage}: {sum(c["sequential"] for c in root)} FF + {sum(not c["sequential"] for c in root)} comb; clocks grey',xlabel='um',ylabel='um');ax[1].set_aspect('equal')
a=reach['arcs'][0];aa=by[a['src_inst']]['bbox_dbu'];bb=by[a['dst_inst']]['bbox_dbu'];xy=[((aa[0]+aa[2])/2/D,(aa[1]+aa[3])/2/D),((bb[0]+bb[2])/2/D,(bb[1]+bb[3])/2/D)]
ax[2].plot([xy[0][0],xy[1][0]],[xy[0][1],xy[1][1]],'-o',color='#1868b2');ax[2].set(title=f"Worst actual LEF registered reach {a['um']:.3f} um (limit405)",xlabel='um',ylabel='um');ax[2].grid(alpha=.2);ax[2].set_aspect('equal',adjustable='datalim');fig.suptitle('DIAGNOSTIC proposal only: fresh soft-island source + bounded reset + native boundaries still required.');fig.tight_layout();fig.savefig(sys.argv[4],dpi=150)
