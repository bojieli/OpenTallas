from pathlib import Path
import sys,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/home/ubuntu/coord/tmp/codex-s81-wavefail-2035/t51_current/geom.tsv');R=json.load(open(P/'whole_graph_translation_refined.json'))[1];mv={r['name']:r for r in R['moved']};cols={'ft2_ring_band_FFs':'#c33758','ft2_stage0':'#d58200','ft6_stage2':'#287bb5'};fig,axs=plt.subplots(1,2,figsize=(15,8))
ax=axs[0];others=[g.ctr(c)for c in D.cells.values()if c[0]=='S'and c[6]not in mv];ax.scatter([p[0]for p in others],[p[1]for p in others],s=.25,c='.7',alpha=.45,rasterized=True)
for fam,col in cols.items():
 z=[r for r in R['moved']if r['family']==fam];ax.scatter([r['new'][0]for r in z],[r['new'][1]for r in z],s=.6,c=col,label=f'{fam}: {len(z)} existing FFs')
 for key,ls in [('old','--'),('new','-')]:
  xs=[r[key][0]for r in z];ys=[r[key][1]for r in z];ax.add_patch(Rectangle((min(xs)-2,min(ys)-2),max(xs)-min(xs)+4,max(ys)-min(ys)+4,fill=False,edgecolor=col,linestyle=ls,lw=1))
 ax.annotate('',xy=z[0]['new'],xytext=z[0]['old'],arrowprops=dict(arrowstyle='->',color=col,lw=1.3))
ax.set(xlim=(0,1442.88),ylim=(0,1226.88),aspect='equal',xlabel='um',ylabel='um',title='Current actual graph, translated FF families only\nSolid=new, dashed=original bounds; all public pins unchanged');ax.legend(fontsize=8,loc='lower right')
by={c[6].replace(chr(92),''):c for c in D.cells.values()};names=['u_bound.u_cland_ft2_i/u_ring.dch[7].u_dsel/y[50]$_DFF_P_','u_bound.u_ft_ft2_o_0/q[498]$_DFF_P_','u_bound.u_ft_ft2_o_1/q[498]$_DFF_P_'];ax=axs[1]
old=[g.ctr(by[n])for n in names];new=[mv[by[n][6]]['new']if by[n][6]in mv else g.ctr(by[n])for n in names]
for pts,col,lab in [(old,'.5','Original chain centres'),(new,'#c33758','Coupled translated centres')]:
 ax.plot([p[0]for p in pts],[p[1]for p in pts],'o-',color=col,label=lab)
 for i,(x,y)in enumerate(pts):ax.text(x+3,y+3,str(i),fontsize=8,color=col)
ax.axhline(1226.784,color='black',ls=':',label='Unchanged north pin face');ax.set(xlim=(0,160),ylim=(400,1240),aspect=.2,xlabel='um',ylabel='um',title='Why ring relocation needs stage0 coupling\nRing-only: max466.88; joint full graph:402.33/0>405');ax.legend(fontsize=8)
fig.suptitle('T51 STATIC zero-cycle whole-graph translation witness\n3707 existing FFs; all-slot ft2pin86.485/global pin149.81; no rows/TAP/occupancy/PG/clock/parent-pin adoption',fontsize=12);fig.tight_layout(rect=(0,0,1,.92));fig.savefig(P/'translation_model.png',dpi=150)
