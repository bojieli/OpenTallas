#!/usr/bin/env python3
"""Top-down requested pins, not actual PG-admitted geometry, for split D gather."""
import hashlib,json,csv
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'results/arch/hbm_system_geometry_1015';source=Path('/home/ubuntu/wt/hbm-static-attn-quant-1014/rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_registered.sv')
rows=[];faces={f:[]for f in ['W','E','N']}
for bundle in range(8):
 face='W' if bundle in [0,1,4,5]else 'E'
 faces[face]+=[f'tile_data[{256*bundle+i}]'for i in range(256)]+[f'tile_flags[{8*bundle+i}]'for i in range(8)]
faces['E'] += [f'bank_data[{i}]'for i in range(256)]+[f'bank_flags[{i}]'for i in range(8)]+['output_v']
faces['N']=['block_select[0]','block_select[1]','block_select[2]','capture_v','rst_n','clk']
assert {f:len(v)for f,v in faces.items()}=={'W':1056,'E':1321,'N':6}
for bank in range(8):
 for face,names in faces.items():
  for i,name in enumerate(names):
   # Requested locations spread across the face, snapped to .048 lattice.
   edge=225.18 if face!='N'else 250.02
   along=round((4+(edge-8)*(i+.5)/len(names))/.048)*.048
   rows.append({'bank_leaf':bank,'region':bank//2,'half':bank%2,'port_bit':name,'face':face,'layer':'M4'if face!='N'else 'M5','requested_along_um':round(along,6),'actual_coordinate':None})
with (out/'D_bank_gather_pin_contract.tsv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
d={'status':'SOURCE_BOUND_REQUESTED_PROTOTYPE_NOT_QUALIFIED','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'outline_requested_um':[250.02,225.18],'permitted_platform_snap':'must report actual dimensions','orientation':'R0','leaves':8,'ff_per_leaf':2386,'literal_pin_bits_per_leaf':2383,'faces':{f:len(v)for f,v in faces.items()},'face_port_order':faces,'clock_period_ps':833.333333,'additional_read_edges':2,'same_cycles_as':'previous four registered full-group gathers','source_binding':'bank B uses region g=B//2, half=B%2; bundle k takes logical tile4*k+g data[256*half+:256],flags[8*half+:8]','PG_offset_requested_um':1.5,'minimum_pitch_requested_um':.096,'cut_limit':.60,'capacity_lower_bounds_um_before_PG':{'W':1056*.096/.6,'E':1321*.096/.6},'pin_policy':'TSV is requested along-edge positions only. Physical owner must legalize to actual tech tracks, above-pin keepouts and PG projections, then export all actual rectangles. No actual PG capacity or insertion claimed.','replaces':'full group gather measured TT spread207ps and setup-24ps; split source requires actual proof and CTS','actual_global_homes':None,'known_clocks':'two half leaves per region on same logical phase; source/physical owner must count total bank root endpoints before accepting shared root'}
(out/'D_bank_gather_pin_contract.json').write_text(json.dumps(d,indent=2)+'\n');print({'rows':len(rows),'source_sha256':d['source_sha256']})
