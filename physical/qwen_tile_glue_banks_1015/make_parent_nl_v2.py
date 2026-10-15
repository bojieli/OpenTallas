#!/usr/bin/env python3
"""qfd_tile_nl_banked_v2 (r13 NL helper 2026-10-15): NL v1 with the PM-H-S W-face plan (coordinator decision, main
48fab3baf / c75914db1).  ONLY change vs v1: face_t_out is the CLOSED-to-be qwen_glue_w514 (v514 RTL, W=q pins at
local y 5.292 + 0.192 k) at R0 origin (5.4, 699.84), and t_out[k] sits on the tile TB window y = 705.132 + 0.192 k
(= TB slot s = 2k; odd slots empty: NL has no n_b).  Same logic/matvec, same 53 banks / clocks / resets / edges."""
from pathlib import Path
import json,re,subprocess,sys
r=Path(__file__).resolve().parents[2]
D=r/'rtl/qwen_sys/tile_parent_nl_banked_20261015'
def one(s,a,b):
 assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
t=(D/'qfd_tile_nl_banked_v1.sv').read_text()
t=one(t,'module qfd_tile_nl_banked_v1 #(','module qfd_tile_nl_banked_v2 #(')
t=one(t,'qwen_glue_v514 face_t_out(','qwen_glue_w514 face_t_out(')
t=t.replace('// Versioned NODE-LESS native-parent successor','// PM-H-S v2 (face_t_out = qwen_glue_w514, interleaved TB t_out pins) of the versioned NODE-LESS native-parent successor',1)
(D/'qfd_tile_nl_banked_v2.sv').write_text(t)
m=json.loads((D/'bank_manifest.json').read_text())
for z in m['banks']:
 if z['inst']=='face_t_out':z['master']='qwen_glue_w514'
m['schema']='qwen.compute.parent_nl_banked_v2';m['pm_h_s']='face_t_out=qwen_glue_w514 at (5.4,699.84) R0; t_out[k] W M4 (0.096, 705.132+0.192k)'
(D/'bank_manifest_v2.json').write_text(json.dumps(m,indent=2)+'\n')
# physical: v1 spec -> v2
s=json.loads((r/'tools/ref_tile/specs_q_compute_native/qfd_tile_nl_banked_v1.json').read_text())
name='qfd_tile_nl_banked_v2';s['name']=s['top']=name;s['io_tcl']=f'physical/ref_tile/{name}/assigned_pins.tcl'
s['sources']=[x.replace('qfd_tile_nl_banked_v1.sv','qfd_tile_nl_banked_v2.sv') for x in s['sources']]
c=next(c for c in s['children'] if c['inst']=='face_t_out')
c.update(view='physical/ref_tile/qwen_glue_w514/views/qwen_glue_w514',at=[5.4,699.84],orient='R0')
for c2 in s['children']:
 if c2 is c:continue
 bx,by=c2['at']
 assert not (bx<27.0 and by<805.68 and bx>-1 and by+1>0 and False)
kit=r/'physical/ref_tile'/name;kit.mkdir(exist_ok=True)
pins=json.loads((r/'physical/ref_tile/qfd_tile_nl_banked_v1/assigned_pins.json').read_text())
P=pins['pins']
for k in range(514):P[f't_out[{k}]']={'layer':'M4','xy_um':[0.096,round(705.132+0.192*k,6)],'basis':'PM-H-S TB window slot s=2k (coordinator frozen plan)'}
# clock pad of face_t_out moves with the master: w514 R0 clk W M4 local (0.096,1.308) -> parent M5 entry above it
P['ck_bank[38]']={'layer':'M5','xy_um':[round(5.4+0.096,6),round(699.84+1.308,6)],'basis':'qwen_glue_w514 R0 clk pad (local 0.096,1.308) at origin (5.4,699.84)'}
pins['qualification']='PENDING: qwen_glue_w514 view not yet CLOSED; actual CTS/native gates'
(kit/'assigned_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(kit/'assigned_pins.tcl').write_text('\n'.join(f'place_pin -pin_name {{{n}}} -layer {v["layer"]} -location {{{v["xy_um"][0]:.6f} {v["xy_um"][1]:.6f}}}'for n,v in P.items())+'\n')
s['orfs_vars']['OT_OFLOP_HARD_FACE_AUDIT']='/src/physical/qwen_tile_glue_banks_1015/hard_face_binding_nl_v2.tcl'
s['job'].update(tag='nl53pm',purpose='NL PM-H-S v2: qwen_glue_w514 t_out face on the interleaved TB slots; otherwise NL banked v1',views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}')
for b in s['job']['benches']:b['cmd']=b['cmd'].replace('qfd_tile_nl_banked_v1','qfd_tile_nl_banked_v2')
s['job']['benches'][0]['cmd']=s['job']['benches'][0]['cmd'].replace('rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv','rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv')
s['structural_change']=s['structural_change']+' v2: PM-H-S face_t_out=qwen_glue_w514 at (5.4,699.84), t_out on TB slots 705.132+0.192k.'
s['reroute_reason']['source']='rtl/qwen_sys/tile_parent_nl_banked_20261015/qfd_tile_nl_banked_v2.sv'
(r/f'tools/ref_tile/specs_q_compute_native/{name}.json').write_text(json.dumps(s,indent=2)+'\n')
# hard-face binding v2: face_t_out master qwen_glue_w514 (its view hashes are added when the w514 view is CLOSED)
b=(r/'physical/qwen_tile_glue_banks_1015/hard_face_binding_nl.tcl').read_text()
b=one(b,'{ck_bank[38]} {{face_t_out} {qwen_glue_v514} {clk}}','{ck_bank[38]} {{face_t_out} {qwen_glue_w514} {clk}}')
b=one(b,'hard_face_audit_nl.tcl','hard_face_audit_nl_v2.tcl')
(r/'physical/qwen_tile_glue_banks_1015/hard_face_binding_nl_v2.tcl').write_text(b)
a=(r/'physical/qwen_tile_glue_banks_1015/hard_face_audit_nl.tcl').read_text()
a=one(a,' t_out 514 face_t_out qwen_glue_v514 q OUTPUT',' t_out 514 face_t_out qwen_glue_w514 q OUTPUT')
(r/'physical/qwen_tile_glue_banks_1015/hard_face_audit_nl_v2.tcl').write_text(a)
print('NL v2 generated')
