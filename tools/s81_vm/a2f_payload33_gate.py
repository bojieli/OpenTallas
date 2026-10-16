#!/usr/bin/env python3
"""Full 53-source, 6,996-bit split payload vs original one-edge payload oracle."""
import argparse,pathlib,subprocess,tempfile,sys
R=pathlib.Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('--mutant',choices=['DATA','MASK','EPOCH','RESET']);a=a.parse_args()
s='''module tb;
reg ck=0;always #5 ck=~ck;
reg rn=0;reg [211:0] mask;reg [6783:0] data;
wire [211:0] om,rm;wire [6783:0] od,rd;wire [11:0] ep;wire [2:0] re;
s81_a2_w0_payload_split4 dut({4{ck}},{4{rn}},mask,data,om,od,ep);
s81_a2_w0_payload refdut(ck,rn,mask,data,rm,rd,re);
integer c,j,q,seed=3317;
initial begin
for(c=0;c<900;c=c+1)begin
 @(negedge ck);rn=!(c<7||(c>=211&&c<212)||(c>=503&&c<510));
 for(j=0;j<212;j=j+1)mask[j]=$random(seed);
 for(j=0;j<212;j=j+1)data[32*j+:32]=$random(seed);
 @(posedge ck);#1;
 if(c>9)begin
  if(om!==rm||od!==rd)begin $display("PAY33 FAIL data_or_mask edge=%0d",c);$finish;end
  for(q=0;q<4;q=q+1)if(ep[3*q+:3]!==re)begin $display("PAY33 FAIL epoch edge=%0d quarter=%0d",c,q);$finish;end
 end
end
$display("PAY33 PASS 900 edges, 53 sources, 6996 data/mask bits, all four epochs");$finish;
end endmodule'''
with tempfile.TemporaryDirectory() as d:
 d=pathlib.Path(d);(d/'tb.sv').write_text(s)
 cmd=['iverilog','-g2012','-s','tb','-o',str(d/'tb')]
 if a.mutant:cmd+=['-DS81_PAY33_MUT_'+a.mutant]
 subprocess.run(cmd+[str(d/'tb.sv'),str(R/'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_a2f_payload33.sv'),str(R/'tools/s81_vm/area_a2_controlled.sv')],check=True)
 out=subprocess.check_output(['vvp',str(d/'tb')],text=True);print(out,end='');sys.exit(0 if 'PAY33 PASS' in out else 1)
