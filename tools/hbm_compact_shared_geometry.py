#!/usr/bin/env python3
"""Whole-die compact shared arithmetic alternative, same source inventories.
Move complete SMframes and actual ATT macro groups; missing hardware explicit.
"""
import argparse,json
from pathlib import Path
from hbm_forward_geometry_views import candidate,draw
from hbm_head_cohort_geometry import source_spans
from hbm_system_geometry import lef

def build(g):
 c=candidate(g);b=c['boxes'];tw=2*514.89+21.6+43.2+2*(51.408+5.4);th=2*562.95+21.6+43.2+70.488+21.6+20.79+43.2
 for t in range(32):
  sl=t%16;lane=t//16;x=11000+(sl%6)*tw;y=9300+(3*lane+sl//6)*th
  old=b[f'ATT_q{t}_0'];dx=x-old['x'];dy=y-old['y']
  names=[f'ATT_q{t}_{a}'for a in range(4)]+[f'ATT_code{t}']+[f'ATT_PVbank{64*t+i}'for i in range(64)]
  for n in names:b[n]['x']+=dx;b[n]['y']+=dy
 for s in range(64):
  q=b[f'ATT_q{s//4}_0'];b[f'Q{128+s}'].update(x=q['x']+310+(s%4)*(51.408+5.4),y=q['y']+1190.7)
 for field in range(4):
  x=11000+(4+field%2)*tw;y=9300+(2+3*(field//2))*th
  for s in range(128):b[f'Pfield{field}_{s}'].update(x=x+50+(s%16)*(51.408+5.4),y=y+60+(s//16)*(20.79+5.4))
  b[f'gather_plan{field}'].update(x=x+100,y=y+400)
 for q in ['SW','NW','SE','NE']:
  for bank in range(8):
   v=b[f'VM_{q}_{bank}'];v.update(x=20000 if q=='NE'else(7500 if q.endswith('W')else 25500),y=(11000 if q=='NE'else(9200 if q.startswith('S')else 13300))+bank*(v['h']+43.2))
   for s in range(3):b[f'LG_{q}_{bank}_{s}'].update(x=v['x']-43.2-(s+1)*150.336-s*43.2,y=v['y'])
 for sm in range(16,32):b[f'SM{sm}']['y']+=800
 for lane in range(2):b[f'KV_metadata{lane}'].update(x=19000,y=16000+lane*100)
 b['ATT_programme'].update(x=19200,y=16300)
 conflicts=[];items=list(b.items())
 for i,(n,a)in enumerate(items):
  for m,d in items[i+1:]:
   if min(a['x']+a['w'],d['x']+d['w'])>max(a['x'],d['x'])+1e-6 and min(a['y']+a['h'],d['y']+d['h'])>max(a['y'],d['y'])+1e-6:conflicts.append([n,m])
 c.update(name='compact_SHARED_actual_inventory',rectangle_conflicts=conflicts,geometry_change='Pack32sharedquadgroups6columns×6rows, distinctNLlanehalves; move16northSMframes800um; samePHY/SerDesreservations;8logicalNEbanksonecentralcolumn')
 c['new_architecture_obligations']={'new_arithmetic_or_SRAM_count':0,'source_inventory_same_as':'forwardDmode34/Q64/P4/registeredgather','north_SM_frame_shift_um':800,'original_SM_frame_orientations_preserved':True,'query_problem':'BothNLclients ofSL now3tile-rowpitchesapart (~4040um). Q64stillneedsreal512bloadstations; optionalrealQcopy+64SRAM=.06840142848mm2notincluded.','P_problem':'FourexistingP4copiesinstantiated butfieldclientsnowinterleavedacrosscompactarray; actual1024blocalbuspathsneedstations/pins.','D_drain_problem':'Old4clock/gathergroups t%4 nowspancompactarray; smallergeo diameterdoesnotqualifyroots orwirehops.','FP32_QK_tree_order':'unchanged; no reassociation to pretendearlylocalreduction','new_native_PC_conflict':'North SM +800um translation overlaps source-bound native PC frame y24025.728..24738.528; this alternative is REJECTED as a whole-known fit until repacked. Controller macros not included in this rectangle scan.','all_missing_views_remain':True,'whole_native_qualified':False}
 return c

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=build(json.loads(Path(a.graph).read_text()));quad=lef('physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef');c['QK_source_spans']=source_spans(c,quad);Path(a.out).write_text(json.dumps(c,indent=2)+'\n');draw(c,Path(a.out).with_suffix('.svg'),quad,lef('physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef'),lef('physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef'));print(json.dumps({'conflicts':conflicts if False else c['rectangle_conflicts'],'QKspan':c['QK_source_spans'][0]}))
if __name__=='__main__':main()
