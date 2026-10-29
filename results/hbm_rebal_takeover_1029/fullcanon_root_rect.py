"""Correct only the root driver micro-rectangle inside its existing 8.64um island."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import core_infra as C
P=Path(sys.argv[1]);sl=json.load(open(P/'master_slice.json'));old=C.compile_slice(sl)
isl=sl['pushdown']['islands'][0];assert isl['name']=='isl0' and isl['driver']['parallel']==2
r=isl['driver_rect_um'];assert round(r[2]-r[0],6)==2.16
cx=(r[0]+r[2])/2;newr=[round(cx-2.16,6),r[1],round(cx+2.16,6),r[3]]
assert all(a<=b for a,b in zip(isl['rect_um'][:2],newr[:2])) and all(a<=b for a,b in zip(newr[2:],isl['rect_um'][2:]))
isl['driver_rect_um']=newr;new=C.compile_slice(sl)
assert len(old['cells'])==len(new['cells'])
for a,b in zip(old['cells'],new['cells']):
 assert {k:v for k,v in a.items()if k!='rect_um'}=={k:v for k,v in b.items()if k!='rect_um'}
 if a['rect_um']!=b['rect_um']:assert a['name'].startswith('mp_isl0_')
for k in old:
 if k!='cells':assert old[k]==new[k],k
(P/'master_slice_root4.json').write_text(json.dumps(sl,indent=2)+'\n')
(P/'core_infra_plan_root4.json').write_text(json.dumps(new,indent=2)+'\n')
(P/'master_core_infra_root4.tcl').write_text(C.emit_tcl(sl))
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(8,7));a=isl['rect_um'];ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fill=False,edgecolor='black',label='Existing reserved 8.64um island'))
ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='red',linestyle='--',label='Failed 2.16um micro-rectangle'))
ax.add_patch(Rectangle((newr[0],newr[1]),newr[2]-newr[0],newr[3]-newr[1],fill=False,edgecolor='green',linewidth=2,label='Corrected 4.32um micro-rectangle'))
for c in new['cells']:
 if not c['name'].startswith('mp_isl0_'):continue
 w=C.BUF_WIDTH_UM[c['master'].split('_ASAP7')[0]];x,y=c['xy_um'];ax.add_patch(Rectangle((x-w/2,y-.135),w,.27,color='steelblue'));ax.annotate(c['name'],(x,y),xytext=(x,y+.5),ha='center',fontsize=8)
for p in isl['ft_ports']:
 x,y=p['xy_um'];ax.plot(x,y,'o',color='purple');ax.annotate(p['name'],(x,y),xytext=(x,y+.35),ha='center',fontsize=8)
ax.plot(*sl['islands'][0]['centre_um'],'k+');ax.set(xlim=(a[0]-1,a[2]+1),ylim=(a[1]-1,a[3]+1),aspect='equal',xlabel='um',ylabel='um',title='Fullcanon root: same cell centres/FT pins, legal driver rectangle');ax.legend(fontsize=8,loc='lower left');fig.tight_layout();fig.savefig(P/'root_rect_review.png',dpi=140)
print('SOURCE delta driver_rect only; cells/ports/arcs/clock/source/cycles identical')
