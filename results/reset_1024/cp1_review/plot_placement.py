import json,sys,pathlib,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
root=pathlib.Path('/srv/opentallas-scratch/claude/wt/codex-cp1-push-1025')
sys.path.insert(0,str(root/'tools/die_plan'))
import schema,reset_tree
p=root/'results/reset_1024/cp1_wavefront_1025';d=json.load(open(p/'r1_placed.json'));budget=json.load(open('/srv/opentallas-scratch/claude/codex-cp1-wavefront-kits/col_h10_r1__t1/budget.json'))
P=schema.Plan(json.load(open(p/'pair_plan.json')));T=reset_tree.for_type(P,'col_h10_r1__t1')
x0,y0,w,h=d['die'];fig,axes=plt.subplots(1,2,figsize=(15,7),dpi=150)
colors={'face':'#e24a33','leaf':'#348abd','station':'#2ca02c','reset':'#e5ae38','buffer':'#999999'}
def kind(n):
 if n.startswith(('u_bin_','u_bout_')):return 'face'
 if n.startswith('u_leaf'):return 'leaf'
 if n.startswith('u_ft'):return 'station'
 if n.startswith(('u_rrl','u_rst')):return 'reset'
 return 'buffer'
for k,col in colors.items():
 pts=[c for c in d['cells'] if kind(c[0])==k]
 if pts:axes[0].scatter([c[2] for c in pts],[c[3] for c in pts],s=1.5 if k!='reset' else 10,c=col,label=f'{k}: {len(pts)}',alpha=.75)
ck=np.array([t['xy'] for t in budget['clock']['taps_snapped']]);axes[0].scatter(ck[:,0],ck[:,1],marker='*',s=55,c='purple',label='clock taps')
for r in T['relays']:
 axes[0].plot(*r['xy'],'.',c='gold',ms=4)
axes[0].plot(*T['root'],'s',c='black',ms=6,label='reset entry')
axes[0].set_title('CP1 W r1: actual 3_place cells + clock/reset')
axes[0].legend(loc='upper right',fontsize=8)
area=np.array([c[4]*c[5] for c in d['cells']]);xx=np.array([c[2] for c in d['cells']]);yy=np.array([c[3] for c in d['cells']]);bins=(25,22)
H,xe,ye=np.histogram2d(xx,yy,bins=bins,range=[[0,w],[0,h]],weights=area);H=H/((w/bins[0])*(h/bins[1]));im=axes[1].imshow(H.T,origin='lower',extent=[0,w,0,h],cmap='Blues',vmin=0,vmax=max(.03,float(H.max())),aspect='equal');fig.colorbar(im,ax=axes[1],label='active cell area / bin area',shrink=.75)
edges=d['edges'][:80];segs=[[e[3],e[4]] for e in edges];axes[1].add_collection(LineCollection(segs,linewidths=.5,colors=['red' if e[0]>405 else 'gray' for e in edges],alpha=.3))
axes[1].set_title(f'Active density + 80 longest signal segments\nmax bin {H.max():.1%}; red >405um (buffers included)')
for a in axes:a.set(xlim=(0,w),ylim=(0,h),xlabel='x (um)',ylabel='y (um)',aspect='equal');a.grid(alpha=.15)
fig.suptitle(f"CP1 wavefront proof r1: {len(d['cells']):,} active, {d['physical_cells_skipped']:,} physical cells omitted; placement only",fontsize=12)
fig.tight_layout();out=p/'r1_placed.png';fig.savefig(out,bbox_inches='tight');print(out)
print('maxbin',H.max(),'top segments',[(round(e[0],1),e[1],e[2]) for e in edges[:6]])
