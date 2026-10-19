import json
from pathlib import Path
area=1651.185;rows=[]
for nr in [84,86,88,90,104]:
 first=(504-nr)//2;capacity=nr*136.08*.270
 rows.append(dict(rows=nr,first_row=first,ylo_um=2.16+first*.270,yhi_um=2.16+(first+nr)*.270,target55_area_um2=capacity*.55,base_lef_area_um2=area,headroom_with_95BUF8_16_6212_um2=capacity*.55-area-16.6212,headroom_with_actual_INT8_reference_75_86_um2=capacity*.55-area-75.86,INT8_reference_local_fill=(area+75.86)/capacity,actual_new_clock_area_um2=None,actual_tie_cells=0,actual_new_hold_area_um2=None,upper_PG_straps_vias_capacity=None,filler_tap_cost=None,selected_by_ROOT=nr==104))
Path('out/capacity_sensitivity.json').write_text(json.dumps(dict(scope='ONE connected fullwidth band alternatives, MODEL ONLY; ROOT selected104; shorter bands historical only, not placement',current_allocation_rows=104,actual_INT8_clock_reference=dict(area_um2=75.86,cells=253,source='ROOT HBM lead measured2782sink reference; transfer to2904sink coupon NOT qualified'),clock_95BUF8='analytical fragile estimate, NOT robust clock headroom',rows=rows),indent=2)+'\n')
