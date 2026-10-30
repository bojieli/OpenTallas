from pathlib import Path
import collections,json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(sys.argv[1]);D=R/'row_first_geometry';r=json.loads((D/'plan_geometry.json').read_text())[0];s=json.loads((D/'slice_geometry_native.json').read_text());check=json.loads((D/'geometry_checks.json').read_text())
masters={f[1]:[float(x)for x in f[2:4]]for l in (R/'baseline/sites.txt').read_text().splitlines()if(f:=l.split())and f[0]=='MASTER'}
fig,ax=plt.subplots(figsize=(8,12));mac={}
for l in (R/'baseline/geo.txt').read_text().splitlines():
 f=l.split()
 if f and f[0]=='MACRO':mac[f[1]]=list(map(float,f[3:7]))
for a,b,c,d in mac.values():
 ax.add_patch(Rectangle((a,b),c-a,d-b,color='.83'));ax.add_patch(Rectangle((a-4.32,b-4.32),c-a+8.64,d-b+8.64,fill=False,edgecolor='.7',lw=.3,ls='--'))
for w in r['wire_paths']:
 for pts in w['paths']:ax.plot([p[0]for p in pts],[p[1]for p in pts],c='.75'if w['level']>2 else('tab:red'if w['level']==1 else'tab:blue'),lw=.3 if w['level']>2 else 1.5,alpha=.7)
upper={q['new']for q in r['row_first22']['old_new_map']}
for u,p in s['cell_placements'].items():
 a,b=p['origin_um'];w,h=masters[p['master']];name=u.removeprefix('mp_ck_');ax.add_patch(Rectangle((a,b),w,h,color='orange'if name in upper else'navy',alpha=.8))
for q in s['core_tree']['nodes']:
 name=q['name'].removeprefix('mp_ck_')
 if name in upper:ax.scatter(*q['xy_um'],s=18,c='orange',edgecolors='black',lw=.4,zorder=5)
ax.scatter(*zip(*r['islands_requested_xy']),s=160,facecolors='none',edgecolors='magenta',lw=1.5,zorder=6)
xy=r['native_input']['xy_um'];ax.scatter(*xy,marker='*',s=150,c='lime',edgecolors='black',zorder=7);ax.annotate('native ck[0]',xy,xytext=(12,0),textcoords='offset points',fontsize=8)
for name,y in [('bottom',70.2),('middle',227.34),('top',386.1)]:ax.annotate(name+' row group',(147.96,y),xytext=(4,8),textcoords='offset points',fontsize=7)
ax.set(xlim=(0,295.92),ylim=(0,444.96),aspect='equal',title='H2 row-first3×2: actual converted upper22 footprints\nRed3 row trunks; blue6 bay legs; magenta fixed anchors\n1811 cells /19747 native sinks /12 stages; timing NOT RUN')
fig.text(.06,.02,'Native source/input, all sinks+caps, lower stage7..12 and22-master multiset preserved.\nRow/site/full-width occupancy+PG1811/0blocked PASS; maxdisp %.3fum. No P&R.'%check['converter']['displacement_um']['max'],fontsize=8)
fig.savefig(D/'geometry.png',dpi=150,bbox_inches='tight');plt.close(fig)
