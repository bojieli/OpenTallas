#!/usr/bin/env python3
"""Actual Engram relay component: all 105 bits, exact edge, reset and DUT fault controls."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TB=r"""
`timescale 1ns/1ps
module tb;
 reg clk=0;always #1 clk=~clk;
 reg arst_n=0;reg [68:0] up_i=0;reg [35:0] dn_i=0;
 wire [68:0] up_o;wire [35:0] dn_o;
 ot_s81_engram_rly dut(clk,arst_n,up_i,dn_i,up_o,dn_o);
 integer epoch,i,checks=0;reg [68:0] eu;reg [35:0] ed;
 initial begin
  for(epoch=0;epoch<4;epoch=epoch+1)begin
   @(negedge clk);arst_n=0;up_i=0;dn_i=0;
   #0.1;if(up_o[68:32]!==0||dn_o[3:0]!==0)$fatal(1,"RELAY_FAIL reset");
   repeat(3)@(negedge clk);arst_n=1;
   repeat(4)@(negedge clk);
   for(i=0;i<1024;i=i+1)begin
    up_i={$urandom,$urandom,$urandom};dn_i={$urandom,$urandom};
    if(i<105)begin up_i=0;dn_i=0;if(i<69)up_i[i]=1;else dn_i[i-69]=1;end
    eu=up_i;ed=dn_i;@(posedge clk);#0.1;
    if(up_o!==eu||dn_o!==ed)$fatal(1,"RELAY_FAIL edge epoch=%0d row=%0d",epoch,i);
    checks=checks+105;
    // A changed input between edges must never pass through the relay.
    up_i=~up_i;dn_i=~dn_i;#0.2;
    if(up_o!==eu||dn_o!==ed)$fatal(1,"RELAY_FAIL combinational");
    checks=checks+105;@(negedge clk);
   end
  end
  $display("PASS Engram relay actual105bits vectors4096 checks%0d resets4 exact1edge",checks);$finish;
 end
endmodule
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--mut',type=int,choices=[0,1,2],default=0);a=ap.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 p=ROOT/'rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv';s=p.read_text();original=hashlib.sha256(p.read_bytes()).hexdigest()
 if a.mut==1:
  old='up_o[31:0]<=up_i[31:0];';assert s.count(old)==1;s=s.replace(old,"up_o[31:0]<=up_i[31:0]^32'h1;")
 if a.mut==2:
  old='up_o[68:32]<=up_i[68:32];';assert s.count(old)==1;s=s.replace(' wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);\n // up:', ' reg [36:0] fault_delay;always @(posedge clk)fault_delay<=up_i[68:32];\n wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);\n // up:');s=s.replace(old,'up_o[68:32]<=fault_delay;')
 (out/'dut.sv').write_text(s);(out/'tb.sv').write_text(TB)
 (out/'receipt.json').write_text(json.dumps(dict(scope='actual relay component only; whole MIX4 remains open',original_source_sha256=original,mut=a.mut,mutated_source_sha256=hashlib.sha256(s.encode()).hexdigest(),test_sha256=hashlib.sha256(TB.encode()).hexdigest()),indent=1))
 vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 cmd=[str(vl) if vl.exists() else 'verilator','--binary','--timing','-O1','-j','2','-Wno-fatal','-Wno-WIDTH','--top-module','tb','-Mdir',str(out/'obj'),str(out/'dut.sv'),str(out/'tb.sv')]
 r=subprocess.run(cmd,capture_output=True,text=True);(out/'build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise SystemExit(r.returncode)
 r=subprocess.run([str(out/'obj/Vtb')],capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,flush=True);raise SystemExit(r.returncode)
if __name__=='__main__':main()
