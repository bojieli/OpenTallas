#!/usr/bin/env python3
"""Lockstep the exact EPC slice bodies from two RTL sources; reject a shadow-load mutant."""
import argparse, hashlib, json, subprocess
from pathlib import Path
a=argparse.ArgumentParser()
a.add_argument("--golden",type=Path,required=True);a.add_argument("--candidate",type=Path,required=True)
a.add_argument("--out",type=Path,required=True);a.add_argument("--width",type=int,default=552)
a.add_argument("--cycles",type=int,default=2000000)
x=a.parse_args()
if x.out.exists():raise SystemExit("REFUSE existing evidence directory")
x.out.mkdir(parents=True)
def body(p):
 s=p.read_text();mark=chr(96)+"ifdef OT_HE_EPC_ISLICE"
 z=s.split(mark,1)[1].split(chr(96)+"else",1)[0]
 if "wire        ep_v" not in z or "wire        ep_l" not in z:raise SystemExit("slice extraction failed")
 return z
g=body(x.golden);c=body(x.candidate)
old="if (!isl_sv) isl_sd <= {il, id};"
if c.count(old)!=1:raise SystemExit("candidate must have the measured free-load form")
m=c.replace(old,"if (1'b0) isl_sd <= {il, id};")
def module(n,b):
 return ("module "+n+" #(parameter W=552)(input clk,rst_n,iv,ir,up,il,input [W-1:0] id,"
 "output ready,valid,last,output [W-1:0] data);\n"+b+
 "\nassign ready=ir_g; assign valid=ep_v; assign last=ep_l; assign data=ep_d;\nendmodule\n")
tb=r"""
module tb;
localparam W=WIDTH, NCYC=CYCLES, NW=(W+32)/32;
reg clk=0,rst_n=0,iv=0,ir=0,up=0;
reg [NW*32-1:0] rnd;
wire [W:0] din=rnd[W:0];
wire gr,gv,gl,cr,cv,cl,mr,mv,ml;
wire [W-1:0] gd,cd,md;
gold #(.W(W)) g(clk,rst_n,iv,ir,up,din[W],din[W-1:0],gr,gv,gl,gd);
cand #(.W(W)) c(clk,rst_n,iv,ir,up,din[W],din[W-1:0],cr,cv,cl,cd);
mutant #(.W(W)) m(clk,rst_n,iv,ir,up,din[W],din[W-1:0],mr,mv,ml,md);
integer i,j,mode,err=0,muterr=0,pushes=0,pops=0,stalls=0,blocked=0,resets=0;
initial begin
 rnd=0; #7 rst_n=1;
 for(i=0;i<NCYC;i=i+1)begin
  @(negedge clk); mode=(i/50000)%4;
  iv=(mode==0)?1:($random&1);
  ir=(mode==1)?1:((mode==3)?(($random&7)==0):($random&1));
  up=(($random&63)!=0);
  for(j=0;j<NW;j=j+1)rnd[j*32+:32]=$random;
  #1;
  if(gr!==cr || gv!==cv || (gv&&{gl,gd}!=={cl,cd}))begin
   err=err+1;if(err<4)$display("CAND_MISMATCH cycle=%0d",i);
  end
  if(gr!==mr || gv!==mv || (gv&&{gl,gd}!=={ml,md}))muterr=muterr+1;
  if(iv&&gr)pushes=pushes+1;
  if(gv&&ir)pops=pops+1;
  if(gv&&!ir)stalls=stalls+1;
  if(iv&&up&&!gr)blocked=blocked+1;
  if(i%250000==249999)begin rst_n=0;#1 rst_n=1;resets=resets+1;end
 end
 $display("SLICE_LOCKSTEP cycles=%0d width=%0d errors=%0d pushes=%0d pops=%0d stalls=%0d blocked=%0d resets=%0d",i,W+1,err,pushes,pops,stalls,blocked,resets);
 $display("SHADOW_DROP_MUTANT mismatches=%0d",muterr);
 if(err!=0 || muterr==0 || blocked==0 || stalls==0 || resets==0)$fatal(1,"SLICE_EQ FAIL");
 $display("SLICE_EQ PASS MUTANT_REJECTED");$finish;
end
always #5 clk=~clk;
endmodule
"""
tb=tb.replace("WIDTH",str(x.width)).replace("CYCLES",str(x.cycles))
src=x.out/"miter.sv";src.write_text(chr(96)+"timescale 1ns/1ps\n"+module("gold",g)+module("cand",c)+module("mutant",m)+tb)
subprocess.run(["iverilog","-g2012","-s","tb","-o",str(x.out/"miter"),str(src)],check=True)
r=subprocess.run(["vvp",str(x.out/"miter")],text=True,capture_output=True)
(x.out/"run.log").write_text(r.stdout+r.stderr)
receipt={"golden":str(x.golden),"golden_sha256":hashlib.sha256(x.golden.read_bytes()).hexdigest(),"candidate":str(x.candidate),"candidate_sha256":hashlib.sha256(x.candidate.read_bytes()).hexdigest(),"bits":x.width+1,"cycles":x.cycles,"returncode":r.returncode,"verdict":"PASS" if r.returncode==0 and "SLICE_EQ PASS MUTANT_REJECTED" in r.stdout else "FAIL"}
(x.out/"result.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(r.stdout,end="");raise SystemExit(0 if receipt["verdict"]=="PASS" else 1)
