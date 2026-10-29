#!/usr/bin/env python3
from pathlib import Path
import re,sys
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
old=Path('/srv/opentallas-scratch2/claude/head-kits-8/kits/hd_st_str/rtl/ot_s81hd_st_str.sv').read_text();new=Path('/srv/opentallas-scratch2/claude/codex-head-kits-0822/control_trial/hd_st_str/rtl/ot_s81hd_st_str.sv').read_text()
(out/'old.sv').write_text(old.replace('ot_s81hd_st_str','old_ft'))
(out/'new.sv').write_text(new.replace('ot_s81hd_st_str','new_ft'))
mut=new.replace('.d(u_s4_q), .ea(u_s4_eq)', '.d(u_s3_q), .ea(u_s3_eq)')
assert mut!=new
(out/'mut.sv').write_text(mut.replace('ot_s81hd_st_str','mut_ft'))
def inst(s,mod,nm,u,d,rs,st):
 clocks=re.findall(r'input\s+wire\s+(clk(?:_t\d+)?)\s*,',s)
 con=[f'.{n}(clk)' for n in clocks]+['.arst_n(rst)', '.start_i(start)', '.u_i(ui)', '.d_i(di)',f'.u_o({u})',f'.d_o({d})',f'.rst_o_0({rs}[0])',f'.rst_o_1({rs}[1])',f'.start_o_0({st}[0])',f'.start_o_1({st}[1])']
 return f'{mod} {nm} ('+','.join(con)+');'
s='''`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,start=0;always #5 clk=~clk;
reg[514:0]ui=0;reg[512:0]di=0;wire[514:0]uo,un,um;wire[512:0]do_,dn,dm;wire[1:0]ro,rn,rm,so,sn,sm;
reg[513:0]pu0,pu1;reg[511:0]pd0,pd1;reg eu0,eu1,ed0,ed1;
integer i,b,seed=12345,checks=0,caught=0,settle=0;reg[31:0]a,c;
'''
s+=inst(old,'old_ft','gold','uo','do_','ro','so')+'\n'+inst(new,'new_ft','dut','un','dn','rn','sn')+'\n'+inst(new,'mut_ft','mutant','um','dm','rm','sm')+'\n'
s+='''initial begin
for(i=0;i<4096;i=i+1)begin
 @(negedge clk);rst=!(i<12 || (i>=2020 && i<2032));start=!(i<18 || (i>=2020 && i<2038));
 a=$random(seed);c=$random(seed);ui={i[0],a[1:0],{16{a}}};di={!i[0],{16{c}}};
 @(posedge clk);#1;
 if(i>8)begin
  if(un[513:0]!==pu1 || dn[511:0]!==pd1)$fatal(1,"payload miter i=%0d",i);
  if(um[513:0]!==pu1)caught=caught+1;
  if(ro!==rn || so!==sn)$fatal(1,"boot depth changed i=%0d",i);
  if(!rst || !start)settle=0;else settle=settle+1;
  if(settle>20)begin
   if(un[514]!==eu1 || dn[512]!==ed1)$fatal(1,"epoch miter i=%0d",i);
  end
  if(rn==0 && (un[514]!==0 || dn[512]!==0))$fatal(1,"reset epoch i=%0d",i);
  checks=checks+1;
 end
 pu1=pu0;pu0=uo[513:0];pd1=pd0;pd0=do_[511:0];eu1=eu0;eu0=uo[514];ed1=ed0;ed0=do_[512];
end
if(caught==0)$fatal(1,"mutant escaped");
$display("PASS lockstep payload1026bits +epoch/reset: checks=%0d mutant_caught=%0d added_data_cycles=2 boot_delta=0",checks,caught);$finish;
end
endmodule
'''
(out/'tb.sv').write_text(s)
