from pathlib import Path
import json,sys,re
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
R=Path(__file__).parent;D=G.Design(R/'geom.tsv');shift=11.934;orig={};moved=[]
for i,c in list(D.cells.items()):
 if c[0]=='S' and 'u_ft_ft6_o_2/' in c[6]:
  orig[i]=c;moved.append(c[6]);a=list(c);a[2]-=shift;a[4]-=shift;D.cells[i]=tuple(a)
pairs=[];m=G.r2r_metrics(D,pairs);out=dict(scope='DISABLED geometric stage2-family translation arithmetic only, no cells moved in nativeDB or plan; native row/TAP/clock/occupancy/source review pending',shift_x_um=-shift,moved_count=len(moved),expected_stage2_count515=True if len(moved)==515 else False,projected_full_graph=m,remaining_over405=pairs)
# Pure graph geometry footprints omit TAP and native row inventory: do not claim legal anchor allocation.
(R/'ft6_stage2_translation_MODEL.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
