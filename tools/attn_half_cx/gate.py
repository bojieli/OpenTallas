#!/usr/bin/env python3
"""Full583bit actual q/rst pipe minimum gate; run remotely with admission."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TB=r'''
`timescale 1ps/1fs
module tb;
parameter integer MUT=0;
reg clk=0;
// Explicit positive-edge period833.333ps; simulation precision1fs.
always begin #416.666 clk=1;#416.667 clk=0;end
reg [582:0] d=0;wire [582:0] orig,got;wire [38:0] tail;
ot_attn_bpipe #(.W(544),.N(5),.EW0(1)) a0(.clk(clk),.d(d[543:0]),.q(orig[543:0]));
ot_attn_fpipe #(.W(39),.N(5)) a1(.clk(clk),.d(d[582:544]),.q(orig[582:544]));
ot_attn_bpipe #(.W(544),.N(5),.EW0(1)) b0(.clk(clk),.d(d[543:0]),.q(got[543:0]));
ot_attn_half_qtail #(.N(MUT==2?4:5),.FLAT(1)) b1(.clk(clk),.d(d[582:544]),.q(tail));
assign got[582:544]=MUT==1?{1'b0,tail[37:0]}:tail;
reg [582:0] hist[0:4];integer c,j,k,checks=0;time last_pos=0;realtime last_rt=0;
always @(posedge clk)begin
 for(integer n=4;n>0;n=n-1)hist[n]<=hist[n-1];hist[0]<=d;
end
initial begin
 for(c=0;c<1024;c=c+1)begin
  @(negedge clk);
  for(j=0;j<583;j=j+1)d[j]=$random;
  // Exercise asserted/released reset carried as data and all query modes.
  d[582]=(c%17<8);d[581:580]=c%4;
  @(posedge clk);#0.001;
  if(c>0 && ($realtime-last_rt < 833.3325 || $realtime-last_rt>833.3335))$fatal(1,"clock period");
  last_rt=$realtime;
  if(c>=4)begin
   if(got!==orig || got!==hist[4])$fatal(1,"QTAIL mismatch cycle=%0d mut=%0d",c,MUT);
   checks=checks+583;
  end
 end
 $display("PASS_ATTN_QTAIL full_bits=583 tail_bits=39 stages=5 FF=195 period_ps=833.333 cycles=1024 bit_checks=%0d",checks);$finish;
end
initial begin #2000000;$fatal(1,"watchdog");end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 tb=a.out/'tb.sv';tb.write_text(TB)
 files=['rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv']
 cases=[]
 for name,mut in [('golden',0),('reset_lost',1),('tail_one_edge_early',2)]:
  exe=a.out/(name+'.vvp');cmd=['iverilog','-g2012','-s','tb',f'-Ptb.MUT={mut}','-o',str(exe),str(tb),*[str(ROOT/p) for p in files]]
  p=subprocess.run(cmd,capture_output=True,text=True);(a.out/(name+'.compile.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
  p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/(name+'.run.log')).write_text(p.stdout+p.stderr)
  assert (p.returncode==0)==(mut==0),(name,p.stdout,p.stderr)
  assert ('PASS_ATTN_QTAIL' in p.stdout)==(mut==0),(name,p.stdout)
  cases.append(dict(name=name,returncode=p.returncode,expect='PASS' if mut==0 else 'FAIL',output=p.stdout));exe.unlink()
 rec=dict(verdict='PASS',scope='actual583bit q/rst pipe, not wholequad/die',timeunit='1ps',timeprecision='1fs',positive_edge_period_ps=833.333,half_rate_mechanism=False,cases=cases,sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files+['tools/attn_half_cx/gate.py']})
 (a.out/'terminal.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True)
if __name__=='__main__':main()
