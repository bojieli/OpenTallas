from pathlib import Path
import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=Path(sys.argv[1]);G=Path(sys.argv[2]);r=json.loads((D/'plan_geometry.json').read_text())[0];sl=json.loads((D/'slice_geometry.json').read_text());review=json.loads((D/'geometry.json').read_text())
fig,ax=plt.subplots(figsize=(9,12));rects=set()
for ln in G.read_text().splitlines():
 f=ln.split()
 if f[0]=='MACRO':rects.add(tuple(map(float,f[3:7])))
for x0,y0,x1,y1 in rects:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='.93',edgecolor='.8',lw=.3))
colors={1:'tab:red',2:'tab:blue',3:'tab:green',4:'tab:orange'}
for w in r['wire_paths']:
 for ps in w['paths']:ax.plot([p[0]for p in ps],[p[1]for p in ps],c=colors.get(w['level'],'.5'),lw=.55,alpha=.65)
changed=set()
for x in r['candidate_changes']:
 for p in x['new_repeaters_um']:changed.add(tuple(p))
for x in r['candidate_leaf_reparents']:
 if x.get('fixed'):changed.add(tuple(x['branch_xy']))
if changed:ax.scatter([p[0]for p in changed],[p[1]for p in changed],s=9,c='cyan',edgecolors='black',linewidth=.25,zorder=5,label='Redistributed existing repeaters / repaired branches')
for i,p in enumerate(r['islands_requested_xy']):
 ax.scatter(*p,s=130,facecolors='none',edgecolors='magenta',zorder=6)
 ax.text(p[0]+4,p[1]+3,str(i),color='magenta',fontsize=9)
native=r['native_input']['xy_um'];root=next(n['xy_um']for n in sl['core_tree']['nodes']if n['name']=='mp_ck_root')
ax.scatter(*native,marker='*',s=180,c='black',zorder=10,label='Actual native ck[0] M5 entry')
ax.scatter(*root,marker='s',s=22,c='blue',zorder=9,label='Native converted root buffer')
ax.scatter(147.96,222.48,marker='x',s=50,c='.4',zorder=8,label='Old diagnostic model centre (not a native pin)')
ax.set(xlim=(0,295.92),ylim=(0,444.96),aspect='equal',xlabel='µm',ylabel='µm',title='H2 single native-input geometry candidate — timing NOT RUN\n6 fixed anchors; 1811 frozen-master cells / 12 stages / 19747 sinks\nall segments≤70µm; detour≤1.016; native converter max1.539µm / PG PASS')
ax.legend(loc='lower center',bbox_to_anchor=(.5,-.19),fontsize=8,ncol=1);fig.tight_layout();fig.savefig(D/'geometry.png',dpi=140);plt.close(fig)
