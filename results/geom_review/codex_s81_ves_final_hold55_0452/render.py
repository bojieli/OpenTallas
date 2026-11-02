from pathlib import Path
import json,importlib.util
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
p=Path('/home/ubuntu/coord/tmp/codex-ves-final-look-0452');b=json.loads((p/'baseline.json').read_text());pg=json.loads((p/'actual_PG.json').read_text());assert pg['unknown_count']==0
s=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G);d=G.Design(p/'geom.tsv');by={c[6].replace('\\',''):c for c in d.cells.values()};order=['chunk_kk.term[6].operand_line.g_ring.u.q[24]$_DFF_P_','_104726_','chunk_kk.term[6].add.u.x_bexp[1]$_DFF_P_'];leafs=['mp_ck_T101200','mp_ck_T100131'];fig,axs=plt.subplots(1,2,figsize=(13,12),gridspec_kw={'width_ratios':[.9,1.1]})
a=axs[0];cs=list(d.cells.values());a.scatter([G.ctr(c)[0] for c in cs],[G.ctr(c)[1] for c in cs],s=.12,c='slategray',alpha=.25,rasterized=True)
for z in pg['global_m5_stripes']:
 r=z['rect_um'];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='goldenrod',alpha=.25,lw=0))
a.add_patch(Rectangle((35,195),23,14,fill=False,ec='red',lw=1.2));a.scatter([82.092],[172.8],marker='*',color='darkorange',s=45);a.set(xlim=(0,172.8),ylim=(0,345.6),title='Actual routed final baseline /385.51um reach\n30810FF rooted; all858648PG0; DRC/ANT/DRV0')
a=axs[1];cs=[c for c in cs if c[2]<57 and c[4]>35 and c[3]<211 and c[5]>195];a.add_collection(PatchCollection([Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3]) for c in cs],facecolor='lightgray',edgecolor='none',alpha=.65))
colors={'M3':'#2171b5','M4':'#756bb1','M5':'#d9a52b'}
for z in pg['region_pg_shapes']:
 r=z['rect_um'];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color=colors[z['layer']],alpha=.15,lw=0))
for i,n in enumerate(order):
 c=by[n];x,y=G.ctr(c);a.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc=['#31a354','#fdae6b','#de2d26'][i],ec='black',lw=.5));a.annotate(['Launch q[24]\nCLK188.69 + CQ54.97','INVx1\n10.45ps','Capture x_bexp[1]\nCLK221.50'][i],(x,y),xytext=[(52,207.8),(50,197.2),(40,199)][i],fontsize=9,ha='center',arrowprops={'arrowstyle':'->','lw':.7})
 if i:
  xx,yy=G.ctr(by[order[i-1]]);a.plot([xx,x],[yy,y],c='red',lw=1.4)
for n,col in zip(leafs,['#238b45','#cb181d']):
 c=by[n];x,y=G.ctr(c);a.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc=col,alpha=.8));a.annotate(n,(x,y),fontsize=7,color=col)
a.set(xlim=(35,57),ylim=(195,211),title='Actual short data path across two frozen clock leaves\narrival254.18 vs required263.47 → FF−9.29ps')
for a in axs:a.set_aspect('equal');a.set_xlabel('um');a.set_ylabel('um');a.grid(alpha=.08)
fig.suptitle('VEs source-final LOOK for bounded DATA-only FFhold12 PREP\nTT+41.71 / FF−9.29,55ep; preserve RTL/reset/clock wires and sink masters; no physical ECO launched',fontsize=12);fig.tight_layout();fig.savefig(p/'actual_final_hold55_look.png',dpi=160);print(p/'actual_final_hold55_look.png')
