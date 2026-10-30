#!/usr/bin/env python3
"""Per-bit planned keybuf SRAM read and bypass reach, not routed timing."""
import argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('repo',type=Path);a=ap.parse_args()
D=json.loads((a.plan/'die_plan.json').read_text());C=next(c for t in D['partition_types'].values() for c in t.get('hard_cores',[]) if c['module']=='ot_hnx_idxn_keybuf_slice');pins={p['name']:p for p in json.loads((a.plan/C['pins_file']).read_text())}
source=a.repo/'rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_slice.sv';sv=source.read_text();assert '.rd_out(rd[m*256+:256])' in sv and "{rd[1087:0],tag,1'b1}:key_in" in sv
master='ot_sram_1r1w_256x256_m2_r2c2';lef=a.repo/'physical/asap7_memory_macros_v2'/master/(master+'.lef');text=lef.read_text();W,H=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups());rd={}
for m in re.finditer(r'(?ms)^\s*PIN\s+(rd_out\[\d+\])(.*?)^\s*END\s+\1\s*$',text):
 box=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',m[2]);x0,y0,x1,y1=map(float,box.groups());rd[int(re.search(r'\[(\d+)\]',m[1])[1])]=((x0+x1)/2,(y0+y1)/2)
assert len(rd)==256
M=json.loads((a.plan/'core_macros.json').read_text())['cores']['ot_hnx_idxn_keybuf_slice']['macros'];assert len(M)==5
width,height=C['outline_um'];rows=[]
for bit in range(1099):
 out=pins[f'key_out[{bit}]'];inp=pins[f'key_in[{bit}]'];ff=(min(width-4.32,max(4.32,out['x'])),4.32)
 row=dict(bit=bit,input_pin_xy=[inp['x'],inp['y']],output_pin_xy=[out['x'],out['y']],planned_output_ff_xy=ff,bypass_pin_to_pin_um=round(abs(inp['x']-out['x'])+abs(inp['y']-out['y']),3),bypass_pin_to_ff_um=round(abs(inp['x']-ff[0])+abs(inp['y']-ff[1]),3))
 if bit>=11:
  m,b=divmod(bit-11,256);mac=M[m];assert mac['orient']=='MY';dx,dy=rd[b];x=mac['rect_um'][0]+W-dx;y=mac['rect_um'][1]+dy
  row.update(macro=mac['name'],rd_bit=b,read_pin_xy=[round(x,3),round(y,3)],macro_read_to_output_pin_um=round(abs(x-out['x'])+abs(y-out['y']),3),macro_read_to_output_ff_um=round(abs(x-ff[0])+abs(y-ff[1]),3))
 rows.append(row)
keys=['macro_read_to_output_pin_um','macro_read_to_output_ff_um','bypass_pin_to_pin_um','bypass_pin_to_ff_um'];worst={k:max((r for r in rows if k in r),key=lambda r:r[k]) for k in keys};bad={k:sum(r.get(k,0)>405 for r in rows) for k in keys}
report=dict(status='ANALYTIC_PLANNED_POINTS_NOT_PLACED',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),real_macro_size_um=[W,H],per_bit_mapping='key_out[11+m*256+b] from gm[m].mem.rd_out[b], m0..3 all256 and m4 b0..63; metadata0..10 fromtag/control; all1099 have direct key_in bypass',output_ff_guide='S-band planned row y4.32; x clamp4.32..W-4.32 at its own pin',worst=worst,captures_gt405=bad,rows=rows)
(a.plan/'keybuf_read_reach.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(dict(worst={k:v[k] for k,v in worst.items()},captures_gt405=bad,real_macro_size_um=[W,H])))
