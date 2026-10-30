import sys,json,copy
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent;D=G.Design(p/'tile_geom.tsv');by={c[6]:c for c in D.cells.values()};d=json.load(open(p/'tile4_groups.json'));groups=d['groups'];rects=d['rects']
# Same macro/core outline. Occupy capture cells before spreading the overlapping merge group.
rects['merge_pipeline']=[330,334,430,374]
for k,suffix,r in [('fault_a1_capture','flt_q',[342,180,360,190]),('fault_a1_mid','flt_h',[350,485,360,495])]:
 names=[n for n in by if n.replace('\\','')==f'u_core.u_b.{suffix}[1]$_DFF_P_'];assert len(names)==1,names
 groups[k]=names;rects[k]=r
order=list(groups);order.remove('a_capture');order.insert(order.index('merge_pipeline'),'a_capture')
for k in ['a_early_skew','b_skew']:
 order.remove(k);order.append(k)
spread={}
for k in ['a_early_skew','b_skew','merge_pipeline']:
 area=sum((by[n][4]-by[n][2])*(by[n][5]-by[n][3]) for n in groups[k]);r=rects[k];target=.8 if k!='merge_pipeline' else .65
 spread[k]=.4*(r[2]-r[0])*(r[3]-r[1])*target/area
lines=['# Tile bounded-area packing trial: same RTL/cycles/outline/pins/macros.', 'set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]']
for k in order:
 lines.append('set cland_cursor {}');r=' '.join(map(str,rects[k]));sp=spread.get(k,.6)
 for n in sorted(groups[k]):lines.extend([f'set ti [$ff_blk findInst {{{n}}}]','if {$ti eq "NULL"} {error "TILE5 missing exact mapped core register"}',f'cland_put $ti {{{r}}} tile5:{k} {sp:.8f} 1'])
 lines.append(f'puts "TILE5 {k} count={len(groups[k])} spread={sp:.5f}"')
lines.append('close $cland_fh');(p/'tile5_hop.tcl').write_text('\n'.join(lines)+'\n');d['spread']=spread;(p/'tile5_groups.json').write_text(json.dumps(d,indent=1)+'\n');print(spread)
# Review structural bounds of same-stage free regions and the single escaped two-stage fault link.
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
f,a=plt.subplots(figsize=(8,11))
for c in D.cells.values():
 if c[0]=='M':a.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc='lightgray',ec='black',hatch='//'))
colors={'a_early_skew':'blue','b_skew':'green','merge_pipeline':'orange','fault_a1_capture':'red','fault_a1_mid':'red'}
for k,col in colors.items():
 x,y,X,Y=rects[k];a.add_patch(Rectangle((x,y),X-x,Y-y,fill=False,ec=col,lw=2));a.text(x,y+Y-y+3,k,color=col,fontsize=8)
a.plot([351,355,355,275],[185,490,714,714],'r-o',label='existing fault stages; bounds333/393um')
a.set(xlim=(0,708.48),ylim=(0,1036.8),aspect='equal',title='Tile5 bounded packing proposal: no new RTL or cycles');a.legend(loc='upper left',fontsize=8);f.savefig(p/'tile5_candidate.png',dpi=160,bbox_inches='tight')
