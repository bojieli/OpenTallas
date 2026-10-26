#!/usr/bin/env python3
"""Smallest forwarded-clock landing: capture successor vs one-root-edge delayed gold."""
import argparse
import json
import subprocess
from pathlib import Path

TB=r'''
`timescale 1ns/1ps
module tb;
parameter K=2, PHASE=0;
reg ck=0,ck_f=0,rs=1; reg[15:0] i=16'h3521; wire[15:0] a,b; wire fa,fb;
reg[15:0] delayed=0; reg delayed_f=0;
wire[2:0] k=K;
ot_s81_land #(.W(16)) gold(k,ck_f,i,ck,rs,a,fa);
ot_s81_land_pin_capture #(.W(16)) cand(k,ck_f,i,ck,rs,b,fb);
always #50 ck=~ck;
initial begin #(300+PHASE); forever begin ck_f=1; #50; ck_f=0; #50; end end
always @(negedge ck_f) i <= {i[14:0],i[15]^i[13]^i[12]^i[10]};
always @(posedge ck) begin delayed<=a; delayed_f<=fa; end
integer n;
initial begin
 #10; rs=0; #290; rs=1;
 for(n=0;n<128;n=n+1) begin @(negedge ck);
  if(n>K+8 && (^b === 1'bx)) $fatal(1,"unknown landed data");
  if(b!==delayed || fb!==delayed_f) $fatal(1,"DIFF k%0d phase%0d cycle%0d old%h new%h f%0b/%0b",K,PHASE,n,delayed,b,delayed_f,fb);
 end
 $display("PASS K%0d phase%0d128rootedges",K,PHASE);$finish;
end
endmodule
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];rtl=root/'rtl/dsrom_sys/s81_dv/land';tb=a.out/'tb.sv';tb.write_text(TB)
    rows=[]
    for mutant in (False,True):
      for k,phase in [(k,p) for k in range(1,8) for p in (0,37,99,137,199) if k>1 or p<137]:
        name=f'k{k}_p{phase}_mut{int(mutant)}';exe=a.out/name
        cmd=['iverilog','-g2012','-s','tb',f'-Ptb.K={k}',f'-Ptb.PHASE={phase}',*(['-DOT_S81_LAND_CAPTURE_MUT_POINTER'] if mutant else []),'-o',str(exe),str(tb),str(rtl/'ot_s81_land.sv'),str(rtl/'ot_s81_land_pin_capture.sv')]
        c=subprocess.run(cmd,capture_output=True,text=True)
        if c.returncode: raise RuntimeError(c.stdout+c.stderr)
        r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/(name+'.log')).write_text(r.stdout+r.stderr)
        rows.append(dict(k=k,phase=phase,mutant=mutant,rc=r.returncode,pass_gate=(r.returncode!=0 if mutant else r.returncode==0)))
    result=dict(schema='opentallas.s81_land_capture_gate.v1',rows=rows,added_root_cycles=1,passed=all(r['pass_gate'] for r in rows))
    (a.out/'summary.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(dict(passed=result['passed'],positive=sum(x['pass_gate'] for x in rows if not x['mutant']),mutant_caught=sum(x['pass_gate'] for x in rows if x['mutant']),cases=len(rows))))
    return 0 if result['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
