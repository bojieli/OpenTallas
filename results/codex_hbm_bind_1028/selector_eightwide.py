"""Prepare exact quarter-preserving 8-record source input into existing 16-record selector.
The full selector still owns its 4x16-record output and12 SRAMs. No arithmetic or cycle changes.
usage selector_eightwide.py INPUT_TOP OUTPUT_TOP (candidate only until source/plan adoption)
"""
import re,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
module='ot_hbm_idx_selector_static_sel'
src=root/'physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/index'/f'{module}.sv'
s=src.read_text();a=s.index('module '+module+' #(');end=re.search(r'^\s*\);\s*$',s[a:],re.M).end()+a
head=s[a:end].replace('module '+module+' #(','module '+module+'_eightwide #(',1).replace('input wire [2367:0] in_line','input wire [1183:0] in_line')
# All8 physical records of quarter q remain in that quarter; the absent upper8 records have valid0.
body='\n wire [2367:0] full_line;\n'
for q in range(4):body+=f" assign full_line[{q*592}+:592]={{296'd0,in_line[{q*296}+:296]}};\n"
body+=f' {module} #(.MUT(MUT)) u_selector (\n'+',\n'.join('  .'+x+'('+('full_line' if x=='in_line' else x)+')' for x in ['clk_ctl','clk_q','clk_mem','rst_n','op','pass','addr','k','in_line','selected_v','selected_line','fault'])+'\n );\nendmodule\n'
(root/'rtl/hbm_next/bind/ot_hnx_selector_eightwide.sv').write_text('`default_nettype none\n'+head+body+'`default_nettype wire\n')
top=Path(sys.argv[1]).read_text();match=re.search(r'(  ot_hbm_idx_selector_static_sel hb_idx__selector \(.*?\.in_line\()([^\n]*)(\),)',top,re.S)
assert match, 'expected current selector source instance'
# Anchor the exact known four296-bit payload slices; do not infer or discard a payload.
expected=['hb_idx__xqr__y[1186:891]','hb_idx__xqr__y[889:594]','hb_idx__xqr__y[592:297]','hb_idx__xqr__y[295:0]']
old=match[2];assert old.startswith("{1184'b") and old.endswith(', '.join(expected)+'}'), 'not the known malformed whole-top expression'
expr='{'+', '.join("296'd0, "+x for x in expected)+'}'
top=top[:match.start(2)]+expr+top[match.end(2):];Path(sys.argv[2]).write_text(top)
keep=[q*592+i for q in range(4) for i in range(296)];removed={str(q*592+i):'0' for q in range(4) for i in range(296,592)}
rule=dict(inst=re.escape('hb_idx__selector'),module=module+'_eightwide',reason='Preserve quarter positions of the8 actual records; missing upper8 records invalid0 inside source wrapper, not leaf tie',port_bits={'in_line':keep},port_bit_constants={'in_line':removed})
Path(__file__).with_name('selector_substitute_inst.json').write_text(json.dumps([rule],indent=1)+'\n')
print('prepared quarter-preserving selector:1184 packed input ->4x592;0 added cycles; candidate needs plan/interface adoption')
