"""Render completed RT clock records without recalculating their model."""
import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(sys.argv[1]);r=json.loads((p/'plan.json').read_text())[0]
fig,ax=plt.subplots(figsize=(13,7));pts=[];mac=[]
for ln in (p/'geo.txt').read_text().splitlines():
 f=ln.split()
 if f[0]=='SINK':pts.append([float(f[1]),float(f[2])])
 if f[0]=='MACRO':mac.append((f[1],[float(x) for x in f[3:7]]))
ax.scatter([q[0] for q in pts],[q[1] for q in pts],s=.4,c='.76',label=f'{len(pts)} standard clock sinks')
for name,(x0,y0,x1,y1) in mac:
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#eeeeee',edgecolor='black',lw=1.5));ax.text((x0+x1)/2,(y0+y1)/2,name+' SRAM',ha='center',va='center')
 ax.add_patch(Rectangle((x0-4.32,y0-4.32),x1-x0+8.64,y1-y0+8.64,facecolor='none',edgecolor='#666666',lw=.8,linestyle='--'))
colors={1:'#d95f02',2:'#1b9e77',3:'#7570b3',4:'#7f7f7f'};bad=[]
for w in r['wire_paths']:
 for length,ps in zip(w['segs'],w['paths']):
  a,b=ps[0],ps[-1];man=sum(abs(x-y) for x,y in zip(a,b))
  if man>1 and length/man>1.1+1e-9:bad.append((ps,w['edge'],length/man))
  ax.plot([q[0] for q in ps],[q[1] for q in ps],color=colors.get(w['level'],'#aaaaaa'),lw=.6,alpha=.65)
for ps,name,ratio in bad:
 ax.plot([q[0] for q in ps],[q[1] for q in ps],color='crimson',lw=1.6)
root=r['nodes_xy'][0][2];entry=[129.612,129.36]
if (p/'slice_native_n.json').exists():
 sl=json.loads((p/'slice_native_n.json').read_text());root=next(n['xy_um'] for n in sl['core_tree']['nodes'] if n['name']=='mp_ck_root')
ax.plot([entry[0],root[0]],[entry[1],root[1]],color='black',lw=2)
ax.scatter(*entry,c='black',marker='*',s=130,zorder=10,label='Preserved native N clock pin')
ax.scatter(*root,c='blue',marker='s',s=20,zorder=10,label='Internal modeled root')
ax.plot([],[],color='crimson',lw=2,label=f'{len(bad)} legs exceed 1.10× direct reach')
ax.set_xlim(0,259.2);ax.set_ylim(0,136);ax.set_aspect('equal');ax.set_xlabel('µm');ax.set_ylabel('µm')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.13),ncol=2,fontsize=9)
check=json.loads((p/'checks.json').read_text());timing=r
if (p/'native_entry_priced.json').exists():
 price=json.loads((p/'native_entry_priced.json').read_text());timing=price.get('uf3_full_input',price['full_input'])
ax.set_title(f"CAP_RT preserved N clock: {r['wire']} {check['verdict']} PLAN MODEL; physical unmeasured\nTT {timing['TT']['mean']:.3f} ps / window {timing['TT']['window']:.2f}; FF {timing['FF']['mean']:.3f} / window {timing['FF']['window']:.2f}; {r['sinks']} exact sinks, {r['stages']} stages")
fig.tight_layout();fig.savefig(p/'clock_review.png',dpi=150);plt.close(fig)
