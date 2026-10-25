#!/usr/bin/env python3
"""Generate a three-class lockstep vehicle using the actual, unchanged leaves."""
import json
from pathlib import Path
import sys
from group_su_lane import pack


def main():
    out=Path(sys.argv[1]);manifest=json.loads((out/'groups.json').read_text())
    # E/W have the same logical wrappers; their physical pin orientations differ.
    for c in range(3):
        w=json.loads((out/f'qfd_qc_su_lane_w_c{c}.reference.json').read_text())
        e=json.loads((out/f'qfd_qc_su_lane_e_c{c}.reference.json').read_text())
        assert w['signature']==e['signature'],f'E/W class{c} differs'
    tb=['`timescale 1ns/1ps','module tb;','reg clk=0; reg rst_n=0;',
        'integer cyc,bitn,errors=0; reg [31:0] rng=32\'h75319bad; integer mutant;',
        'initial begin mutant=$test$plusargs("mutant"); end']
    refs=[]
    for c in range(3):
        n=f'qfd_qc_su_lane_w_c{c}';r=json.loads((out/f'{n}.reference.json').read_text())
        ports=['input wire clk','input wire rst_n',f'input wire [{r["widths"]["c_i"]-1}:0] c_i']
        for g,bits in r['groups'].items():ports.append(f'output wire [{len(bits)-1}:0] {g}')
        ref=[f'module ref_{c} ('+', '.join(ports)+');']
        for wire,width in {**r['reference_wires'],**r['external_wires']}.items():
            ref.append(f'wire [{width-1}:0] {wire};')
        # Reference keeps the exact original port expressions and reconstructs
        # its input wires independently from the candidate's packed slices.
        for field in r['fields']:
            ref.append(f'assign {field["source_expr"]} = c_i[{field["offset"]} +: {field["width"]}];')
        ref.extend(r['reference_cells'])
        for g,bits in r['groups'].items():ref.append(f'assign {g} = {pack(bits)};')
        ref.append('endmodule');refs.append('\n'.join(ref))
        W=r['widths']['c_i'];tb.append(f'reg [{W-1}:0] ci{c};')
        for g,bits in r['groups'].items():
            tb.append(f'wire [{len(bits)-1}:0] got{c}_{g}, ref{c}_{g};')
        conn=['.clk(clk)','.rst_n(rst_n)',f'.c_i(ci{c})']
        tb.append(n+f' dut{c} ('+', '.join(conn+[f'.{g}(got{c}_{g})' for g in r['groups']])+');')
        tb.append(f'ref_{c} golden{c} ('+', '.join(conn+[f'.{g}(ref{c}_{g})' for g in r['groups']])+');')
    tb+=['initial begin','for (cyc=0;cyc<4096;cyc=cyc+1) begin','rst_n=(cyc>=16);']
    for c,W in enumerate([760,760,759]):
        tb.append(f'for(bitn=0;bitn<{W};bitn=bitn+1) begin rng=(rng>>1)^(-(rng&1)&32\'hd0000001); ci{c}[bitn]=rng[0]; end')
    tb+=['#5; clk=1; #1;','if(cyc>64) begin']
    for c in range(3):
        r=json.loads((out/f'qfd_qc_su_lane_w_c{c}.reference.json').read_text())
        for g in r['groups']:
            lhs=f'got{c}_{g}'
            if c==0 and g=='c_o':lhs=f'({lhs} ^ ((mutant && cyc==100) ? 246\'d1 : 246\'d0))'
            tb.append(f'if ({lhs} !== ref{c}_{g}) begin $display("MISMATCH class{c} {g} cycle%0d",cyc);errors=errors+1;end')
    tb+=['end','#4;clk=0;','end',
         'if(errors) $fatal(1,"SU_LANE_MITER FAIL errors=%0d",errors);',
         '$display("SU_LANE_MITER PASS classes=3 E/W_equivalent=3 cycles=4096");$finish;','end','endmodule']
    (out/'reference.sv').write_text('\n\n'.join(refs)+'\n')
    (out/'tb.sv').write_text('\n'.join(tb)+'\n')


if __name__=='__main__':main()
