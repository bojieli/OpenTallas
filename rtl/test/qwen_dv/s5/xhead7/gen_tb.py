"""Leaf lockstep bench: original qfd_dv_s5_xhead (f4746778a) vs the bounded successor qfd_dv_s5_xhead2 (or the bounded real
mutant qfd_dv_s5_xhead_bounded_mut with +mutate) at the PRICED offset: the reference sees a_f / a_ib one edge late
(IN_PIPE 1 = +1 edge on the head-row input) and rst_n one edge late (RST_RELAY: reset assertion and release +1),
q / fault_i / cid unchanged.  The go bit is held 0 in reset and 4 edges
after it (the successor's go pin stage is reset, the bench's reference delay register is not).  10,000 edges, two mid-run resets; per edge a stimulus mode (fully random /
sparse control: go, descriptor-valid and data-valid (f_q[DESC=73]) at 1/8) so both the faulting and the clean fill/read paths are exercised."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[5]; sys.path.insert(0, str(root / 'tools'))
import die_port_bind as P
s = (root / 'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv').read_text()
m = next(m for m in P.parse_modules(P.strip_comments(s), 'x') if m.name == 'qfd_dv_s5_xhead'); env = m.env()
ports = [(n, m.ports[n][0], m.width(n, env)) for n in m.ports]
L = ['`timescale 1ns/1ps', 'module tb_xhead7;', 'reg ck=0; always #5 ck=~ck;', 'integer cycle,failures=0,compares=0,mutate,sparse;']
for n, d, w in ports:
    if n == 'ck': continue
    L.append(f'{"reg" if d=="input" else "wire"} [{w-1}:0] ' + (n if d == 'input' else f'{n}_ref, {n}_dut, {n}_mut') + ';')
L += ['reg [1186:0] a_f_d1; reg [379:0] a_ib_d1; reg rst_ref;', 'always @(posedge ck) begin a_f_d1 <= a_f; a_ib_d1 <= a_ib; rst_ref <= rst_n; end']
for typ, lab, suf in [('qfd_dv_s5_xhead', 'u_ref', 'ref'), ('qfd_dv_s5_xhead2', 'u_dut', 'dut'), ('qfd_dv_s5_xhead_bounded_mut', 'u_mut', 'mut')]:
    L.append(f'{typ} {lab}(' + ','.join(f'.{n}({(n+"_d1") if (lab=="u_ref" and n in ("a_f","a_ib")) else "rst_ref" if (lab=="u_ref" and n=="rst_n") else n if d=="input" else n+"_"+suf})' for n, d, w in ports) + ');')
L += ['initial begin', 'mutate=$test$plusargs("mutate");', 'rst_n=0; cid=6\'d0;', 'for(cycle=0;cycle<10000;cycle=cycle+1) begin', '@(negedge ck);',
      'if(cycle%1000==0) cid=$urandom;', 'sparse=((cycle/500)%2==1);']
for n, d, w in ports:
    if d != 'input' or n in ('ck', 'rst_n', 'cid'): continue
    for lo in range(0, w, 32): L.append(f'{n}[{lo} +: {min(32,w-lo)}]=$urandom;')
L += ['if(sparse) begin a_ib[0]=($urandom%8)==0; a_f[0]=($urandom%8)==0; a_f[73]=($urandom%8)==0; fault_i=0; end',
      'if(cycle<12 || (cycle>=3100&&cycle<3112) || (cycle>=6700&&cycle<6712)) a_ib[0]=0;',
      'rst_n=(cycle>=8)&&!(cycle>=3100&&cycle<3108)&&!(cycle>=6700&&cycle<6708);', '@(posedge ck); #1;', 'if(cycle>16) begin']
for n, d, w in ports:
    if d != 'output': continue
    L.append(f'compares=compares+1; if({n}_ref !== (mutate ? {n}_mut : {n}_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH {n} cycle=%0d",cycle); end')
L += ['end', 'end', 'if(failures) $display("XH7_EQ FAIL mismatches=%0d compares=%0d",failures,compares);',
      'else $display("XH7_EQ PASS compares=%0d cycles=%0d",compares,cycle);', '$finish;', 'end', 'endmodule']
(Path(__file__).parent / 'tb_xhead7.sv').write_text('\n'.join(L) + '\n')
