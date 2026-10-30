#!/usr/bin/env python3
"""Small lockstep coupons of generated W1/R1/R2 cell mechanisms; mutants must differ."""
import re,sys,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tools/die_plan'))
from clock_landings import Landings
from test_count_straps import strap_vehicle
from test_clock_landings import A_BODY
from test_writer_start_depth import enable
p,t=strap_vehicle();enable(p,2)
a=Landings(p,t).type_rtl('A',A_BODY)
chain=re.findall(r'\(\* keep = "true" \*\) ot_dp_landing_relay u_cland_writer_start_x_\d+[^;]+;',a)
assert len(chain)==2
chain='\n'.join(chain).replace('rst_n_t0','raw').replace('cland_start_d','din')
ca=(root/'rtl/common/ot_dp_clk_landing_ca.sv').read_text()
co=(root/'rtl/common/ot_dp_clk_landing.sv').read_text()
def module(s,n):return re.search(r'\bmodule '+n+r'\b.*?\bendmodule',s,re.S).group(0)
rr=(root/'tools/die_plan/gen_rtl.py').read_text()
# The generated rrelay's implementation is extracted from its actual CELLS definition.
import gen_rtl
cells='\n'.join([module(ca,'ot_dp_landing_relay'),module(co,'ot_dp_landing_collect'),module(gen_rtl.CELLS,'ot_dp_rrelay')])
bench=r'''
module tb;
reg clk=0;always #5 clk=~clk;
reg raw=0,din=0;reg[2:0] ready=0,fault=0;reg rst=0;
wire cland_writer_start_x_0,cland_writer_start_x_1;
__CHAIN__
reg[1:0] wg=0;wire wmut=cland_writer_start_x_0;
reg rp=0,ra=0,rb=0,oldreset=0;
wire newreset;
ot_dp_rrelay rcopy(.clk(clk),.d(rb),.q(newreset));
wire sr0,sf0,sr1,sf1;
ot_dp_landing_collect #(.N(3)) status0(.clk(clk),.rst_n(rst),.ready_i(ready),.fault_i(fault),.ready_o(sr0),.fault_o(sf0));
ot_dp_landing_collect #(.N(1)) status1(.clk(clk),.rst_n(rst),.ready_i(sr0),.fault_i(sf0),.ready_o(sr1),.fault_o(sf1));
reg gr0=0,gf0=0,gr1=0,gf1=0;
integer i,checks=0,wm=0,rm=0,sm=0;
always @(posedge clk)begin
 if(!raw)wg<=0;else wg<={wg[0],din};
 rp<=rst;ra<=rp;rb<=rp;oldreset<=ra;
 if(!rst)begin gr0<=0;gf0<=0;gr1<=0;gf1<=0;end
 else begin gr0<=&ready;gf0<=|fault;gr1<=gr0;gf1<=gf0;end
end
initial begin
 for(i=0;i<8192;i=i+1)begin
 @(negedge clk);
 raw=(i%61)>3;din=$random;rst=(i%83)>5;ready=$random;fault=$random;
 @(posedge clk);#1;
 if(i>5)begin
  if(cland_writer_start_x_1!==wg[1])$fatal(1,"W1 mismatch %0d",i);
  if(oldreset!==newreset)$fatal(1,"R1 reset edge mismatch %0d",i);
  if({sr1,sf1}!=={gr1,gf1})$fatal(1,"R2 status mismatch %0d",i);
  checks=checks+1;
  if(wmut!==wg[1])wm=wm+1;
  if(rb!==oldreset)rm=rm+1;
  if({sr0,sf0}!=={gr1,gf1})sm=sm+1;
 end
 end
 if(wm==0||rm==0||sm==0)$fatal(1,"mutant survived");
 $display("PASS checks=%0d W1_mutant=%0d R1_mutant=%0d R2_mutant=%0d",checks,wm,rm,sm);
 $finish;
end
endmodule
'''.replace('__CHAIN__',chain)
out=Path(__file__).resolve().parent
(out/'coupon.sv').write_text(cells+'\n'+bench)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'coupon.vvp'),str(out/'coupon.sv')],check=True)
r=subprocess.run(['vvp',str(out/'coupon.vvp')],text=True,capture_output=True);(out/'result.log').write_text(r.stdout+r.stderr);print(r.stdout,end='');r.check_returncode()
