"""Generate a cycle miter of old pre-sampler select and emitted per-input samplers."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
from test_origin_per_start import origin_body

body, _, _, _ = origin_body(('a', 'b', 'c'), root=True)
ports = '''input clk, input raw_0, input raw_1, input raw_2, input root_raw,
 input cland_fstart_in_a, input cland_fstart_in_b, input cland_fstart_in_c,
 input [1:0] strap_ca_tsel, input [1:0] strap_ca_pad, input strap_ca_efall,
 input strap_ca_root, output cland_start'''
new = 'module candidate(' + ports + ');\n' + body + '\nendmodule\n'
old = '''module reference(''' + ports + ''');
 wire raw_sel = strap_ca_tsel == 0 ? raw_0 : strap_ca_tsel == 1 ? raw_1 : raw_2;
 wire ps = strap_ca_tsel == 0 ? cland_fstart_in_a : strap_ca_tsel == 1 ? cland_fstart_in_b : cland_fstart_in_c;
 wire cs, rs;
 ot_dp_landing_origin_s #(.PADW(2)) orig (.clk(clk),.rst_raw_n(raw_sel),.p_start(ps),
   .strap_efall(strap_ca_efall),.strap_pad(strap_ca_pad),.start(cs));
 ot_dp_landing_root #(.SETTLE(40)) root (.clk(clk),.rst_raw_n(root_raw),.start(rs));
 assign cland_start = strap_ca_root ? rs : cs;
 endmodule
'''
tb = '''module tb;
 reg clk=0; always #5 clk=~clk;
 reg raw_0=0,raw_1=0,raw_2=0,root_raw=0;
 reg a=0,b=0,c=0;
 wire [63:0] eq;
 genvar t,p,e,r;
 generate for(t=0;t<4;t=t+1) begin:T
 for(p=0;p<4;p=p+1) begin:P
 for(e=0;e<2;e=e+1) begin:E
 for(r=0;r<2;r=r+1) begin:R
 wire cn,rf;
 candidate dut(clk,raw_0,raw_1,raw_2,root_raw,a,b,c,2'(t),2'(p),1'(e),1'(r),cn);
 reference ref0(clk,raw_0,raw_1,raw_2,root_raw,a,b,c,2'(t),2'(p),1'(e),1'(r),rf);
 assign eq[16*t+4*p+2*e+r] = (cn===rf);
 end end end end endgenerate
 integer i, comparisons=0;
 initial begin
 for(i=0;i<160;i=i+1) begin
 @(negedge clk); #1;
 raw_0=(i>3 && !(i>=72 && i<=75));
 raw_1=(i>7 && !(i>=88 && i<=91));
 raw_2=(i>11 && !(i>=104 && i<=107));
 root_raw=(i>15 && !(i>=120 && i<=123));
 a=(i>=22 && i<60) || i>=80;
 b=(i>=31 && i<65) || i>=98;
 c=(i>=43 && i<70) || i>=115;
 @(posedge clk); #1;
 if(i>1) begin
 if(eq!==64'hffffffffffffffff) $fatal(1,"MISMATCH cycle=%0d eq=%h",i,eq);
 comparisons=comparisons+64;
 end
 end
 $display("PASS ORIGIN_LOCKSTEP comparisons=%0d variants=64 added_cycles=0",comparisons);
 $finish;
 end
 endmodule
'''
out = Path(__file__).resolve().parent
(out/'miter.sv').write_text(new+old+tb)
# Incorrect selected-start input: a real functional mutant, not a structural assertion.
(out/'mutant.sv').write_text(new.replace('.p_start(cland_fstart_in_a)', '.p_start(cland_fstart_in_b)')+old+tb)
