#!/usr/bin/env python3
"""Actual full-word face leaf specs, never a generic characterization top."""
import json,math
from pathlib import Path
r=Path(__file__).resolve().parents[2]
for w in [514,508]:
 name=f'qwen_glue_v{w}';kit=r/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
 allowed=[round(.012+.048*k,6) for k in range(math.ceil((5.4-.012)/.048),math.floor((70.2-.012)/.048)+1)]
 xy=[]
 for b in range(w):
  target=5.4+64.8*b/(w-1);valid=[v for v in allowed if not xy or v>=xy[-1]+.096-1e-8];xy.append(min(valid,key=lambda v:abs(v-target)))
 assert len(set(xy))==w and xy[-1]<=70.2
 positions={};tcl=[]
 for port,x in [('d',.096),('q',21.504)]:
  points=[[x,y] for y in xy];positions[port]=dict(layer='M4',xy_um=points)
  for b,(x,y) in enumerate(points):tcl.append(f'place_pin -pin_name {{{port}[{b}]}} -layer M4 -location {{{x:.6f} {y:.6f}}}')
 for port,x,y,layer in [('clk',.096,1.308,'M4'),('rst_n',9.708,.096,'M5')]:
  positions[port]=dict(layer=layer,xy_um=[[x,y]]);tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.6f} {y:.6f}}}')
 (kit/'assigned_pins.tcl').write_text('\n'.join(tcl)+'\n')
 (kit/'assigned_pins.json').write_text(json.dumps(dict(schema='opentallas.qwen.full-face-pins.v1',name=name,outline_um=[21.6,75.6],width_bits=w,positions=positions,pg_rule='M5 PG2.7um pitch, clockW/M4(.096,1.308) belowdata5.436 avoids dense M5PG access; data M4 belowPG'),indent=2)+'\n')
 s=json.load(open(r/'physical/qwen_head_bank_pins_1015/packet_template.json'))
 s.update(name=name,top=name,params={},sources=['rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv','rtl/lib/ot_rst_relay.sv','rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_face_masters.sv'],outline=dict(w=21.6,h=75.6),pins={'W':['d','clk'],'E':['q'],'S':['rst_n']},io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',pin_ranges={'d':[xy[0],xy[-1]],'q':[xy[0],xy[-1]]})
 s['route']['m5_pg_pitch']=2.7
 s['job'].update(owner='Codex:q_compute_elem_native_tile',tag='f1',purpose='Actual full-word native compute face capture with safe pin margin',branch='codex/q-compute-native-parents-1014',extra_paths=['physical/qwen_tile_glue_banks_1015','rtl/test/qwen_head_staging'],views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}')
 for b in s['job']['benches']:
  b['cmd']=b['cmd'].replace('physical/qwen_head_staging_1015/bench.sh','physical/qwen_tile_glue_banks_1015/bench_leaf.sh').replace(' 256 ',' '+str(w)+' ')
  for k in ['pass_regex','fail_regex']:
   if k in b:b[k]=b[k].replace('W=256 ','W='+str(w)+' ')
 s['structural_change']='Actual NK/NL classified longglue/faceclock failure: full514/508-bit registered word in21.6x75.6um, separateclockperword. Nativeface needs actuallaunch<=220/capture<=190: old263/256 splitpositions canbeunder500umyetfailface margin. Wider localcore1231um2 avoids original519 posthold755um2>653um2 area failure. ExactM4bitpins5.4..70.2/WclkM4(.096,1.308)/M5PG2.7 frozen. Oneoperationalcapture/noedgesadded; localresetrelease3edges/firstcapture4. Parentresetstagecost separatelyexplicit; fullnativeparentOPEN.'
 p=r/'tools/ref_tile/specs_q_compute_native'/(name+'.json');p.write_text(json.dumps(s,indent=2)+'\n');print(p)
