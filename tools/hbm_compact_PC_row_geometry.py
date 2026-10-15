#!/usr/bin/env python3
"""Structural whole-known alternative: compact shared ATT and one-row PC shores.
No source inventory removed; new PC outline is unqualified and all outside gaps remain.
"""
import argparse,json
from pathlib import Path
from hbm_compact_shared_geometry import build as compact
from hbm_forward_geometry_views import draw
from hbm_system_geometry import lef
from hbm_head_cohort_geometry import source_spans

def build(graph):
 c=compact(graph);b=c['boxes'];ys=sorted({b[f'SM{i}']['y']-800 for i in range(16,32)});shifts=[621.6,600,575.424,550.8]
 for i in range(16,32):
  y=b[f'SM{i}']['y']-800;b[f'SM{i}']['y']=y+shifts[ys.index(y)]
 width=244.512;height=345.6;frame_width=32*width+31*21.6
 for q,x,y,north in [('SW',1455.84,21.6,False),('SE',22165.712,21.6,False),('NW',1455.84,24781.728,True),('NE',22165.712,24781.728,True)]:
  x0=x+(8500.056-frame_width)/2;y0=y-43.2-height if north else y+1177.2+43.2
  for i in range(32):
   b[f'PC_prototype_{q}_{i}']={'x':x0+i*(width+21.6),'y':y0,'w':width,'h':height,'role':'PC_prototype','source':'340cfd747 SAME source/FF/macro inventory; NEW source-identical physical outline must pass pin/PG/FFband/nativeCTS','orientation':'R0','qualified':False}
 conflicts=[];items=list(b.items())
 for i,(n,a)in enumerate(items):
  for m,d in items[i+1:]:
   if min(a['x']+a['w'],d['x']+d['w'])>max(a['x'],d['x'])+1e-6 and min(a['y']+a['h'],d['y']+d['h'])>max(a['y'],d['y'])+1e-6:conflicts.append([n,m])
 c['name']='compact_SHARED_one_row_PC_UNQUALIFIED';c['rectangle_conflicts']=conflicts;c['known_and_planning_rectangles']=len(b);c['all_rectangle_area_mm2']=sum(a['w']*a['h']for a in b.values())/1e6;c['macro_and_prototype_box_area_mm2']=sum(a['w']*a['h']for a in b.values()if a['role']!='gather_reservation')/1e6
 c['new_architecture_obligations'].update(north_SM_frame_shift_um=shifts,new_native_PC_conflict='Old uniform800um translation replaced by explicit row-specific shifts; see actual combined rectangle audit. NO actual channel/pinclock/PHY or fullmissinghardwarefit qualification.',PC_single_row={'source_inventory_change':0,'prototype_outline_um':[width,height],'frame_width_um':frame_width,'shoreline_reservation_width_um':8500.056,'gap_um':21.6,'nominal_perpendicular_extreme_to_PHY_um':388.8,'actual_fixedPHY_command_pins_unbound':True,'PC_first_physical_gate259_2_width_preserved':True,'new_outline_requires':'actual pin/PG/FFband area+CTS and commandPHY pinETM audit; not low-utilization shrink'})
 c['missing_physical_areas'].append('128 PC bodies shown ONLY as source-identical new-outline prototypes; current command-only PHY and caller control/arbiter hardware unbound')
 return c

def main():
 p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=build(json.loads(Path(a.graph).read_text()));q=lef('physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view/ot_attn_tile_m6h1q.lef');c['QK_source_spans']=source_spans(c,q);Path(a.out).write_text(json.dumps(c,indent=2)+'\n');draw(c,Path(a.out).with_suffix('.svg'),q,lef('physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef'),lef('physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef'));svg=Path(a.out).with_suffix('.svg');text=svg.read_text().replace('HBM H16 component forward-flow study: shared compute, local stores, unfinished boundaries','Compact shared attention + one-row native PC candidate (unqualified)').replace('589824 transposeFF / PCcontrollers / sink-DEN-norm','589824 transposeFF / command-only PHY / sink-DEN-norm');svg.write_text(text);print(json.dumps({'rectangles':len(c['boxes']),'conflicts':c['rectangle_conflicts'],'known_prototype_area_mm2':c['macro_and_prototype_box_area_mm2'],'QKspan':c['QK_source_spans'][0]}))
if __name__=='__main__':main()
