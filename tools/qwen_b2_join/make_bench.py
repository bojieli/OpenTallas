#!/usr/bin/env python3
"""Emit full native NB6 SRAM readback bench from the actual source ABI."""
from pathlib import Path
import sys,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
from die_port_bind import parse_modules
src=R/'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2.sv'
s=re.sub(r'^`(?:ifdef|endif).*\n','',src.read_text(),flags=re.M)
m=parse_modules(s,str(src))[0]
# non-partitioned simulation uses real native bank RTL and macro models;
# every actual independent root gets the same ideal synchronous clock only in this bench.
con=[]
expr={'ck':'clk','rst_n':'rst_n','mee':"1'b1",'svr':'svr','svq':'svq','svq_v':'svq_v','ld':'ld','fault':'vf'}
for p,(d,_) in m.ports.items():
 if p in ('native_ck','return_ck','read_control_ck','write_ck','relay_ck'):continue
 if p in expr:e=expr[p]
 elif re.fullmatch('rb[0-5]',p):e=f'rb[{p[-1]}]'
 elif p.startswith('ck_'):e='clk'
 elif d=='input':e="'0"
 else:e=''
 con.append(f'.{p}({e})')
head='''`timescale 1ns/1ps
module tb_b2_vm;
reg clk=0,rst_n=0; always #1 clk=~clk;
integer mut=0;
initial void'($value$plusargs("MUT=%d",mut));
reg [2212:0] rq[0:5]; wire[550:0]rb0[0:5];wire[550:0]rb[0:5];wire[5:0]sf;
reg [20:0]svr=0;wire[511:0]svq;wire svq_v;wire[15:0]ld;wire vf;
for(genvar h=0;h<6;h=h+1)begin:g_ser
 qfd_res_ser_half_b2 #(.HB(h))u(.ck(clk),.rst_n(rst_n),.me_en(1'b1),.rq(rq[h]),.rb(rb0[h]),.fault(sf[h]));
 // Native result-link negative controls: payload corruption, and an illegal simultaneous producer.
 assign rb[h]=(mut==1&&h==4)?(rb0[h]^551'd1):
              (mut==2&&h==1)?rb0[0]:rb0[h];
end
qfd_sp_vector_memory_b2 #(.USE_MACRO(1),.NATIVE_BANKS(1),.RETURN_RO(6),.RETURN_PIN_INPUT(1))dut(
'''
body='''
);
function automatic [511:0]image(input integer row);
 for(integer l=0;l<16;l=l+1)image[32*l+:32]=32'h3f800000+32'(row*16+l);
endfunction
integer cycle=-1,start_cycle=-1,emitted=0,ends=0,replies=0;
integer first_end=-1,last_end=-1,read_cycle=0;
always @(negedge clk)if(rst_n)begin
 cycle=cycle+1;
 for(integer h=0;h<6;h=h+1)if(rb[h][550])begin
  if(!rb[h][548])emitted=emitted+1;
  if(rb[h][549])begin
   if(h!=5||emitted!=(ends+1)*24)$fatal(1,"end before all native producers landed");
   if(first_end<0)first_end=cycle;
   if(ends>0&&cycle-last_end!=24)$fatal(1,"calendar end spacing");
   last_end=cycle;ends=ends+1;
  end
 end
 if(svq_v)begin
  if(svq!==image(replies))$fatal(1,"SRAM readback row%0d got%h want%h",replies,svq,image(replies));
  replies=replies+1;
 end
end
initial begin
 for(integer h=0;h<6;h=h+1)rq[h]=0;
 repeat(5)@(negedge clk);rst_n=1;repeat(30)@(negedge clk);
 start_cycle=cycle;
 for(integer k=0;k<64;k=k+1)begin
  for(integer h=0;h<6;h=h+1)begin
   rq[h]=0;rq[h][2212]=1;rq[h][2211:2208]=4'hf;
   for(integer j=0;j<4;j=j+1)rq[h][552*j+:552]={24'(24*k+4*h+j),16'hffff,image(24*k+4*h+j)};
  end
  @(negedge clk);for(integer h=0;h<6;h=h+1)rq[h]=0;
  repeat(23)@(negedge clk);
 end
 repeat(50)@(negedge clk);
 if(ends!=64||ld!=64||emitted!=1536||sf!=0||vf)$fatal(1,"native result fault ends%0d landed%0d rows%0d sf%b vf%b",ends,ld,emitted,sf,vf);
 for(integer row=0;row<1536;row=row+1)begin svr={1'b1,20'(row)};@(negedge clk);end
 svr=0;repeat(50)@(negedge clk);
 if(replies!=1536)$fatal(1,"missing SRAM replies %0d",replies);
 $display("PASS b2 native NB6 SRAM rows=%0d bursts=%0d first_end_delta=%0d last_end_delta=%0d",replies,ends,first_end-start_cycle,last_end-start_cycle);
 $finish;
end
endmodule
'''
(R/'tools/qwen_b2_join/tb_b2_vm.sv').write_text(head+',\n'.join(con)+body)
