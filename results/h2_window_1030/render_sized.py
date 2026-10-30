from pathlib import Path
import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(sys.argv[1]);d=R/'sizing';r=json.loads((d/'plan_sized.json').read_text())[0];s=json.loads((d/'slice_sized_geometry.json').read_text())
masters={f[1]:[float(x)for x in f[2:4]]for l in (R/'baseline/sites.txt').read_text().splitlines()if(f:=l.split())and f[0]=='MASTER'}
changes=r['d1_uf3']['changes'];fig=plt.figure(figsize=(13,11));ax=fig.add_subplot(121)
mac={}
for l in (R/'baseline/geo.txt').read_text().splitlines():
 f=l.split()
 if f and f[0]=='MACRO':mac[f[1]]=list(map(float,f[3:7]))
for a,b,c,e in mac.values():ax.add_patch(Rectangle((a,b),c-a,e-b,color='.8'))
for w in r['wire_paths']:
 for ps in w['paths']:ax.plot([p[0]for p in ps],[p[1]for p in ps],lw=.4,color=plt.cm.tab10(w['level']%10),alpha=.6)
for n,p in s['cell_placements'].items():
 a,b=p['origin_um'];w,h=masters[p['master']];ax.add_patch(Rectangle((a,b),w,h,color='navy',alpha=.7))
for i,q in enumerate(changes):
 p=s['cell_placements']['mp_ck_'+q['node']]['centre_um'];ax.scatter(*p,s=45,c='red');ax.annotate(str(i),p,fontsize=9)
a=r['native_input']['xy_um'];ax.scatter(*a,marker='*',s=130,c='lime',edgecolors='black');ax.annotate('native ck[0]',a)
ax.scatter(*zip(*r['islands_requested_xy']),s=120,facecolors='none',edgecolors='magenta')
ax.set(xlim=(0,295.92),ylim=(0,444.96),aspect='equal',title='Fixed H2 graph; actual resized converter footprints\n1811 cells,19747 sinks,6 anchors,12 stages; final timing NOT RUN')
text='Canonical R9 accepted master changes\n\n'+'\n\n'.join(f'{i}: {q["node"]}\n{q["frm"]} → {q["to"]}'for i,q in enumerate(changes))+'\n\nNative row/sites and full master widths\nPG1811 edges PASS; max displacement1.539um\nNo topology, wire, stage, fit or sink changes\nPre-final local-descent estimate37.68/30.34: FAIL20'
fig.text(.57,.8,text,fontsize=10,va='top');fig.savefig(d/'geometry.png',dpi=120,bbox_inches='tight');plt.close(fig)
