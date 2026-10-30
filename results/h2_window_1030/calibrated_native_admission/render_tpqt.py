from pathlib import Path
import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(sys.argv[1]);D=R/'tpqt_slew_geometry';r=json.loads((D/'plan_geometry.json').read_text())[0];a=json.loads((R/'final_model/plan_model.json').read_text())[0];s=json.loads((D/'slice_geometry_native.json').read_text());old={q[0]:q for q in a['nodes_xy']};new={q[0]:q for q in r['nodes_xy']};masters={f[1]:[float(v)for v in f[2:4]]for l in(R/'baseline/sites.txt').read_text().splitlines()if(f:=l.split())and f[0]=='MASTER'}
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,9));mac={}
for l in(R/'baseline/geo.txt').read_text().splitlines():
 f=l.split()
 if f and f[0]=='MACRO':mac[f[1]]=list(map(float,f[3:7]))
for view in [ax,bx]:
 for x,y,z,t in mac.values():view.add_patch(Rectangle((x,y),z-x,t-y,color='.82'));view.add_patch(Rectangle((x-4.32,y-4.32),z-x+8.64,t-y+8.64,fill=False,edgecolor='.6',ls='--',lw=.5))
 for w in r['wire_paths']:
  for ps in w['paths']:view.plot([p[0]for p in ps],[p[1]for p in ps],c='red'if w['edge']=='Tpqt'else'.7',lw=1.8 if w['edge']=='Tpqt'else .35)
 for name,p in s['cell_placements'].items():
  x,y=p['origin_um'];w,h=masters[p['master']];view.add_patch(Rectangle((x,y),w,h,color='navy'))
 for u in ['Tpqt_r0','Tpqt_r1']:
  view.scatter(*old[u][2],marker='x',c='orange',s=70,zorder=7);p=s['cell_placements']['mp_ck_'+u]['centre_um'];view.scatter(*p,c='lime',edgecolors='black',s=60,zorder=8)
  if view is bx:view.annotate(u+' '+new[u][3].split('_')[0],p,xytext=(4,10 if u.endswith('r0')else-15),textcoords='offset points',fontsize=8)
 view.set_aspect('equal')
ax.set(xlim=(0,295.92),ylim=(0,444.96),title='H2 nativebest frame; same source/clocktree/1811 cells\nOnly2 existing Tpqt repeater homes change')
bx.set(xlim=(48,104),ylim=(225,271),title='Same67.5um shortest Tpqt path (red)\nOrange old homes; green actual converted homes')
fig.text(.06,.02,'Calibration repair only: segments22.68/3.24/41.58 →25.92/41.04/.54um. No added wire/stages/masters/cycles.\nAll-buffer transition precheck PASS: TTinput52.58/output47.65; FF40.19/35.81ps. No new arrival model or P&R yet.\nNative row/fullwidth/PG1811edges0blocked PASS; max displacement1.539um; window remains historical design-targetFAIL, not recalculated.',fontsize=9)
fig.tight_layout(rect=(0,.09,1,1));fig.savefig(D/'geometry.png',dpi=130,bbox_inches='tight');plt.close(fig)
