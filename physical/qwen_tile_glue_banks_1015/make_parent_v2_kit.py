#!/usr/bin/env python3
"""NK banked v2 kit (PM-H-S interleaved W tree faces, Q-COMPUTE-ELEM r13 2026-10-15) derived from the v1 kit:
face_n_a/n_b/n_y/t_out (4 x qwen_glue_v514) -> face_ya / face_tb (2 x qwen_glue_x1028, x 5.4, y 587.52 / 699.84),
W pins bit-interleaved: TB y = 705.132 + 0.096 s (t_out[k] s=2k, n_b[k] s=2k+1); YA y = 592.812 + 0.096 s
(n_y[k] s=2k, n_a[k] s=2k+1); M4 at x 0.096.  ck_bank[37..40] pads move onto the x1028 clock pins (from its LEF).
Run after the qwen_glue_x1028 view exists (its bytes are hash-bound in the hard-face audit)."""
from pathlib import Path
import json,hashlib,re,sys,subprocess
r=Path(__file__).resolve().parents[2]; G=r/'physical/qwen_tile_glue_banks_1015'
v1=r/'physical/ref_tile/qfd_tile_nk_banked_v1'; name='qfd_tile_nk_banked_v2'; kit=r/'physical/ref_tile'/name
XV='physical/ref_tile/qwen_glue_x1028/views/qwen_glue_x1028'
TB=(5.4,699.84); YA=(5.4,587.52); LOCAL0=5.292; P=0.096
sha=lambda p:hashlib.sha256((r/p).read_bytes()).hexdigest()
lef=(r/XV/'qwen_glue_x1028.lef').read_text()
def pin_xy(pin):
    m=re.search(r'PIN '+re.escape(pin)+r'\b(.*?)END '+re.escape(pin),lef,re.S); assert m,pin
    x0,y0,x1,y1=map(float,re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m.group(1)).groups())
    return (x0+x1)/2,(y0+y1)/2
for k in (0,1,513):   # the master's frozen W slots must be the plan's
    for pin,s in ((f'oq[{k}]',2*k),(f'id[{k}]',2*k+1)):
        x,y=pin_xy(pin); assert abs(y-(LOCAL0+P*s))<1e-3 and x<0.3,(pin,x,y)
s=json.loads((v1/'spec.json').read_text())
s['name']=s['top']=name
s['sources']=[x.replace('qfd_tile_nk_banked_v1.sv','qfd_tile_nk_banked_v2.sv').replace('parent_banks_bb.v','parent_banks_bb_v2.v') for x in s['sources']]
drop={'face_n_a','face_n_b','face_n_y','face_t_out'}
s['children']=[c for c in s['children'] if c['inst'] not in drop]
s['children']+=[{'view':XV,'count':1,'inst':'face_ya','at':list(YA),'at_exact':True,'orient':'R0'},
                {'view':XV,'count':1,'inst':'face_tb','at':list(TB),'at_exact':True,'orient':'R0'}]
assert len(s['children'])==81
hr=s['required_hybrid_roots']['hard_child_entry']
cmap={'ck_bank[37]':('face_ya','clk_i',YA),'ck_bank[38]':('face_tb','clk_i',TB),'ck_bank[39]':('face_ya','clk_o',YA),'ck_bank[40]':('face_tb','clk_o',TB)}
for port,(inst,pin,o) in cmap.items(): hr[port]=f'{inst}/{pin}'
s['io_tcl']=f'physical/ref_tile/{name}/assigned_pins.tcl'
s['orfs_vars']['OT_OFLOP_HARD_FACE_AUDIT']='/src/physical/qwen_tile_glue_banks_1015/hard_face_binding_v2.tcl'
s['job'].update(tag='pm1',owner='Claude:q15_compute_elem',purpose='PM-H-S interleaved W tree faces (coordinator 2026-10-15): paired x1028 face masters, 81 hard children, same 84 roots; bp58c hooks')
s['job']['benches']=[b for b in s['job'].get('benches',[]) if b['name']!='lint']
s['structural_change']=('PM-H-S paired-column mirror (coordinator 2026-10-15, main 48fab3baf): W tree words bit-interleaved '
  '(t_out[k]/n_b[k], n_y[k]/n_a[k] one 0.096 track apart) so the 16.44 um inner channel needs no jogs (cut 0.975 -> 0.136); '
  'the four W face v514 banks become two paired qwen_glue_x1028 masters holding the same registers/clocks/resets (zero added edges). '
  'Keeps the bp58c flow fix (channel blocking + post-resize relocation).')
kit.mkdir(exist_ok=True)
(r/f'tools/ref_tile/specs_q_compute_native/{name}.json').write_text(json.dumps(s,indent=1)+'\n')
pins=json.loads((v1/'assigned_pins.json').read_text())
pp=pins['pins']
for k in range(514):
    pp[f't_out[{k}]']={'layer':'M4','xy_um':[0.096,round(TB[1]+LOCAL0+P*2*k,6)],'basis':'PM-H-S interleave TB even'}
    pp[f'n_b[{k}]']={'layer':'M4','xy_um':[0.096,round(TB[1]+LOCAL0+P*(2*k+1),6)],'basis':'PM-H-S interleave TB odd'}
    pp[f'n_y[{k}]']={'layer':'M4','xy_um':[0.096,round(YA[1]+LOCAL0+P*2*k,6)],'basis':'PM-H-S interleave YA even'}
    pp[f'n_a[{k}]']={'layer':'M4','xy_um':[0.096,round(YA[1]+LOCAL0+P*(2*k+1),6)],'basis':'PM-H-S interleave YA odd'}
for port,(inst,pin,o) in cmap.items():
    x,y=pin_xy(pin); pp[port]={'layer':'M5','xy_um':[round(o[0]+x,6),round(o[1]+y,6)],'basis':f'x1028 {inst}/{pin} LEF pad; M5 parent entry'}
pins['schema']='qwen.compute.parent.actual_pins.v2_interleaved'
(kit/'assigned_pins.json').write_text(json.dumps(pins,indent=1)+'\n')
(kit/'assigned_pins.tcl').write_text('\n'.join(f'place_pin -pin_name {{{n}}} -layer {v["layer"]} -location {{{v["xy_um"][0]:.6f} {v["xy_um"][1]:.6f}}}' for n,v in pp.items())+'\n')
bb=(G/'parent_banks_bb.v').read_text()+'(* blackbox *) module qwen_glue_x1028(input clk_o,clk_i,rst_o_n,rst_i_n,input[513:0]od,output[513:0]oq,input[513:0]id,output[513:0]iq);endmodule\n'
(G/'parent_banks_bb_v2.v').write_text(bb)
b=(G/'hard_face_binding.tcl').read_text()
add=''.join(f' {{{p}}} {sha(p)}\n' for p in ['rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_x1028.sv',f'{XV}/qwen_glue_x1028.lef',f'{XV}/qwen_glue_x1028_tt.lib',f'{XV}/insertion.json'])
b=b.replace('set qce_face_hashes {\n','set qce_face_hashes {\n'+add,1)
for port,(inst,pin,o) in cmap.items():
    b=re.sub(r' \{'+re.escape(port)+r'\} \{\{face_[a-z_]+\} \{qwen_glue_v514\} \{clk\}\}',f' {{{port}}} {{{{{inst}}} {{qwen_glue_x1028}} {{{pin}}}}}',b)
assert b.count('qwen_glue_x1028} {clk_')==4
b=b.replace('hard_face_audit.tcl','hard_face_audit_v2.tcl')
(G/'hard_face_binding_v2.tcl').write_text(b)
a=(G/'hard_face_audit.tcl').read_text()
for o,n in [(' n_a 514 face_n_a qwen_glue_v514 d INPUT',' n_a 514 face_ya qwen_glue_x1028 id INPUT'),(' n_b 514 face_n_b qwen_glue_v514 d INPUT',' n_b 514 face_tb qwen_glue_x1028 id INPUT'),
            (' n_y 514 face_n_y qwen_glue_v514 q OUTPUT',' n_y 514 face_ya qwen_glue_x1028 oq OUTPUT'),(' t_out 514 face_t_out qwen_glue_v514 q OUTPUT',' t_out 514 face_tb qwen_glue_x1028 oq OUTPUT')]:
    assert a.count(o)==1,o; a=a.replace(o,n)
(G/'hard_face_audit_v2.tcl').write_text(a)
print(subprocess.run([sys.executable,str(r/'tools/ref_tile/ref_tile.py'),'gen',str(r/f'tools/ref_tile/specs_q_compute_native/{name}.json')],cwd=r,capture_output=True,text=True).stdout[-600:])
