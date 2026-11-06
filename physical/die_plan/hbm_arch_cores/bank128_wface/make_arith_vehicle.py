"""Real pair/unchanged arithmetic lockstep; explicit delayed write adapter."""
from pathlib import Path
import runpy
r=Path(__file__).resolve().parents[4]
q=r/'physical/die_plan/hbm_arch_cores/bank128_wface'
o=q/'arith_vehicle';o.mkdir(exist_ok=True)
s=(r/'rtl/hbm_accel/cores_split/ot_hbm_hc_native128/ot_hbm_hc_bank128_pair_core.sv').read_text()
top,leaves=s.split('endmodule',1);top+='endmodule\n'
(o/'pair.sv').write_text('`define OT_HC128_WFACE\n'+top.replace('module ot_hbm_hc_bank128_pair_core(','module bank_new(',1)+'`undef OT_HC128_WFACE\n'+top.replace('module ot_hbm_hc_bank128_pair_core(','module bank_old(',1)+leaves)
# Reuse only the exact SRAM behavioral model and stimulus from the mechanism
# vehicle; actual arithmetic is retained in pair.sv above.
tb=(q/'proof/tb.sv').read_text()
tb=tb.replace('integer i,j,checks=0;', 'reg go=0; reg[15:0]lv=0; reg sq=0; reg[511:0]si=0; wire[511:0]yn,yg;wire[1:0]fn,fg;integer known=0;integer i,j,checks=0;')
tb=tb.replace(".go(1'b0),.lane_valid(16'b0),.square(1'b0),.sum_in(512'b0)",'.go(go),.lane_valid(lv),.square(sq),.sum_in(si)')
tb=tb.replace('bank_new n(', 'bank_new n(').replace('.sum_out(),.fault()', '.sum_out(yn),.fault(fn)',1)
tb=tb.replace('.sum_out(),.fault()', '.sum_out(yg),.fault(fg)',1)
tb=tb.replace('we0=rst_n&$random(seed);','go=(i>50)&rst_n&$random(seed);lv=$random(seed);sq=$random(seed);for(j=0;j<16;j=j+1)si[j*32+:32]=$random(seed);\nwe0=rst_n&$random(seed);')
tb=tb.replace('checks=checks+9;', 'if(yn !== yg || fn !== fg)$fatal(1,"arithmetic mismatch cycle%0d",i); if(i>50 && !$isunknown(yn))known=known+1;checks=checks+11;')
tb=tb.replace('$display("PASS bank128 write-face cut checks=%0d cycles=3000",checks);', 'if(known<100)$fatal(1,"insufficient known arithmetic results: %0d",known);$display("PASS actual pair arithmetic checks=%0d cycles=3000 known_outputs=%0d",checks,known);')
# Initialize both memories identically; this avoids counting X equality as proof.
init='initial begin integer a; for(a=0;a<1024;a=a+1)begin\n'
for inst in ['g_w[0]','g_w[1]']:
 for n in ['n','g']:init+=f'{n}.\\u_c.u_b.{inst}.u_m .mem[a]=0;\n'
init+='end for(a=0;a<128;a=a+1)begin\n'
for n in ['n','g']:init+=f'{n}.\\u_c.u_b.g_x[0].u_m .mem[a]=0;\n'
init+='end end\n'
tb=tb.replace('initial begin wd=0;',init+'initial begin wd=0;')
tb=tb.replace('checks=checks+11;', 'checks=checks+11;if(i%500==0)$display("progress cycle=%0d known=%0d",i,known);')
(o/'tb.sv').write_text(tb)
(o/'mem.sv').write_text((q/'proof/mem.sv').read_text())
(o/'run.sh').write_text('set -eu\ncd "$(dirname "$0")"\niverilog -g2012 -s tb -o vehicle.vvp pair.sv mem.sv tb.sv > compile.log 2>&1\nvvp vehicle.vvp > result.log 2>&1\ncat result.log\n')
print(o)
