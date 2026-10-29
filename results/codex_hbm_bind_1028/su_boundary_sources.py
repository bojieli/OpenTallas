"""Enumerated constant SIDE boundary and exact D=0 wire variants; opt-in only."""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools'))
import die_port_bind as D
p=root/'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane_pinreg.sv'
s=p.read_text();start=s.index('module ot_hbm_su_static_lane_pinreg');end=s.index('\n);',start)+3
header=s[start:end];original=next(m for m in D.parse_modules(header+'\nendmodule',str(p)) if m.name=='ot_hbm_su_static_lane_pinreg')
header=header.replace('module ot_hbm_su_static_lane_pinreg','module ot_hnx_su_pinreg_noside').replace('    input wire [31:0] side_y,\n','')
assert 'input wire [31:0] side_y' not in header
body='''
 if(KIND!=0 && KIND!=1)begin:g_invalid_kind
  ERROR_su_noside_requires_KIND_zero_or_one invalid_configuration();
 end
 ot_hbm_su_static_lane_pinreg #('''+', '.join('.'+k+'('+k+')' for k in original.params)+') u_native (\n'
body+=',\n'.join('.'+k+'('+ ("32'd0" if k=='side_y' else k)+')' for k in original.ports)+');\nendmodule\n'
wire='''module ot_hnx_delay_wire #(parameter integer W=32,D=0,RESET=0)(
 input wire[W-1:0]d,output wire[W-1:0]q
);
 if(D!=0 || RESET!=0)begin:g_invalid_delay
  ERROR_delay_wire_requires_zero_D_and_RESET invalid_configuration();
 end
 assign q=d;
endmodule
'''
(root/'rtl/hbm_next/bind/ot_hnx_su_boundaries.sv').write_text('`default_nettype none\n'+header+body+wire+'`default_nettype wire\n')
rules=[dict(inst=r'su_(?:NW|NE)[0-3]\.u_slice\.g_lane\[(?:[0-9]|[12][0-9]|3[01])\]\.g_pr\.u_lane',module='ot_hnx_su_pinreg_noside',reason='Actual selected eight-SU KIND0/1 constant SIDE boundary only; no FULL capability claim; zero added cycles',port_bit_constants={'side_y':{str(i):'0' for i in range(32)}}),
dict(inst=r'hb_idx__s_(?:NW|NE|SW|SE)\.scorer\.ge\[[01]\]\.gc\[[0-3]\]\.leaf\.core\.u_qlate',module='ot_hnx_delay_wire',reason='Actual D0 RESET0 delay is exactly a combinational wire; removes unused clock/reset pins',port_bit_constants={'rst_n':{'0':'0'}})]
Path(__file__).with_name('su_boundary_substitute_inst.json').write_text(json.dumps(rules,indent=2)+'\n')
print('Emitted exact 256 SIDE boundaries and32 D0 wire substitutions; source constants remain mandatory')
