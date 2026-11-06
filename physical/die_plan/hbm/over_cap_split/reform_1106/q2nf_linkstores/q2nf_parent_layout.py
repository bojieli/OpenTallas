import json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base=Path(__file__).resolve().parent
sizes={'ot_sram_1r1w_64x512_m1_r2c2':[171.288,77.784],'ot_sram_1r1w_256x256_m2_r2c2':[172.824,41.064],'ot_sram_1rw_256x64_m4_r2c2':[66.312,17.832]}
children={'link0':{'origin_um':[34.56,172.8],'outline_um':[224.64,414.72]},'rest_control':{'origin_um':[280.8,8.64],'outline_um':[224.64,606.96]},'link1':{'origin_um':[527.04,172.8],'outline_um':[224.64,414.72]}}
macros=[]
for l in (base/'q2nf_macro_placement.tcl').read_text().splitlines():
 m=re.match(r'\s*\{([^}]+)\}\s+(ot_sram_\S+)\s+(\S+)\s+(\S+)\s+(\S+)',l)
 if not m:continue
 n,mod,x,y,orient=m.groups();x=float(x);y=float(y);w,h=sizes[mod]
 owner='link0' if 'g_link\\[0\\]' in n else 'link1' if 'g_link\\[1\\]' in n else 'rest_control'
 q=children[owner];ox,oy=q['origin_um'];W,H=q['outline_um'];assert ox<=x and oy<=y and x+w<=ox+W and y+h<=oy+H,(n,owner)
 macros.append({'name':n,'module':mod,'owner':owner,'rect_um':[x,y,x+w,y+h],'orientation':orient})
assert len(macros)==19
for name,q in children.items():
 w,h=q['outline_um'];area=w*h;ma=sum((r['rect_um'][2]-r['rect_um'][0])*(r['rect_um'][3]-r['rect_um'][1]) for r in macros if r['owner']==name)
 q['macro_count']=sum(r['owner']==name for r in macros);q['macro_area_um2']=ma;q['nominal_free_area_um2']=area-ma;q['nominal_cell_area_capacity_45']=.45*(area-ma)
report={'schema':'q2nf.parent_candidate.v1','parent_outline_um':[786.24,622.08],'children':children,'macros':macros,'inter_child_channel_um':21.6,'parent_unoccupied_area_um2':786.24*622.08-sum(q['outline_um'][0]*q['outline_um'][1] for q in children.values()),'extra_cycles':0,'macro_positions':'preserve all19 measured A SRAM placements; repartition their physical ownership','status':'planning candidate, no native hard-child parent binding or routed abstract yet','required_before_route':['all three actual mapped counts/area','native R2 parent glue binding exact child ABIs','child signal pin grouping/aligned face assignments','actual PG pin/OBS and parent layer reservation','fixed anchors/clock placement review from fresh actual GEN']}
(base/'q2nf_parent_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(13,10));colors={'link0':'#d3e6fa','rest_control':'#e2edce','link1':'#f6e0c8'}
for name,q in children.items():
 x,y=q['origin_um'];w,h=q['outline_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor=colors[name],edgecolor='black',lw=1.5));ax.text(x+w/2,y+h-12,name,ha='center',va='top',fontsize=13)
for j,q in enumerate(macros):
 x,y,X,Y=q['rect_um'];ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#8d98a7',edgecolor='white',lw=.5));ax.text((x+X)/2,(y+Y)/2,q['module'].split('_')[3],ha='center',va='center',fontsize=8)
ax.text(130,80,'Native R2 parent shell /\nclock + PG + pin reserve',ha='center',fontsize=11)
ax.text(650,80,'Same external interface\nand zero extra cycles',ha='center',fontsize=11)
ax.annotate('',(527.04,380),(505.44,380),arrowprops={'arrowstyle':'<->','color':'#b42c2c'});ax.text(516,350,'21.6',rotation=90,ha='center',color='#b42c2c')
ax.set(xlim=(0,786.24),ylim=(0,622.08),xlabel='x (um)',ylabel='y (um)',title='Q2NF: candidate three-child composition in existing parent footprint\nSRAM positions retained; mapped counts and native parent binding required before route');ax.set_aspect('equal');ax.grid(alpha=.15);fig.tight_layout();fig.savefig(base/'q2nf_parent_review.png',dpi=150)
print({k:{a:b for a,b in v.items() if 'area' in a or 'capacity' in a} for k,v in children.items()})
