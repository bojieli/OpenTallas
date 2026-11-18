#!/usr/bin/env python3
"""Small existing reset/START EDGE_FALL relay versus an independently priced count frame.

Cases carry measured PHASE, DUTY_HIGH and transport_ps; J is calculated from the
actual falling edge, rather than assuming half a clock. The default rise bypass
runs as a mutant in the same simulation and must disagree with that frame.
"""
import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

BENCH = r'''
`timescale 1ps/1fs
module tb;
 parameter real T=833.0, PHASE=420.0, DUTY=416.5, DATA_R=219.602, DATA_S=219.244;
 parameter integer J_R=1,J_S=1,EXPECT_MUTANT=1;
 reg sc=0,rc=0,rs=0,ss=0; wire rw,sw,r,s,mr,ms;
 integer source_n=-1,receiver_n=-1,checks=0,errors=0,mutant_errors=0;
 reg expected_r=0,expected_s=0,previous_r=0;
 function automatic rst_at(input integer n);
   rst_at=(n>=0) && ((n%5)==0 || (n%5)==2 || (n%5)==3);
 endfunction
 function automatic start_at(input integer n);
   start_at=(n>=0) && ((n%7)==0 || (n%7)==1 || (n%7)==4);
 endfunction
 initial begin #1 sc=1; forever #(T/2.0) sc=~sc; end
 initial begin #(PHASE+1) rc=1; forever begin #(DUTY) rc=0; #(T-DUTY) rc=1; end end
 always @(posedge sc) begin source_n=source_n+1;rs<=rst_at(source_n);ss<=start_at(source_n);end
 assign #(DATA_R) rw=rs; assign #(DATA_S) sw=ss;
 ot_die_start_relay #(.RESET_RELAY(1),.EDGE_FALL(1)) dut
  (.clk(rc),.rst_raw_n_in(rw),.p_start(sw),.rst_raw_n_out(r),.start(s));
 ot_die_start_relay #(.RESET_RELAY(1),.EDGE_FALL(0)) mutant
  (.clk(rc),.rst_raw_n_in(rw),.p_start(sw),.rst_raw_n_out(mr),.start(ms));
 always @(posedge rc) begin
  receiver_n=receiver_n+1;
  expected_r=rst_at(receiver_n-J_R);
  expected_s=start_at(receiver_n-J_S);
  previous_r=expected_r;
  #0.01;
  if(receiver_n>=3) begin
   checks=checks+2;
   if(r!==expected_r || s!==expected_s) begin errors=errors+1;$display("BAD index%0d got%b%b expected%b%b",receiver_n,r,s,expected_r,expected_s);end
   if(mr!==expected_r || ms!==expected_s) mutant_errors=mutant_errors+1;
  end
  if(receiver_n==90) begin
   $display("RESULT checks%0d errors%0d mutant_errors%0d Jr%0d Js%0d",checks,errors,mutant_errors,J_R,J_S);
   if(errors!=0 || (EXPECT_MUTANT && mutant_errors==0)) $fatal(1,"phase frame or mutant failed");
   $finish;
  end
 end
endmodule
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('cases');p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    source=Path(a.source);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    tree=ast.parse(source.read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RELAY_RTL' for t in n.targets))
    rtl='module ot_die_start_relay #(parameter RESET_RELAY=1, EDGE_FALL=1)(input clk,rst_raw_n_in,p_start,output reg rst_raw_n_out,start);\ngenerate if(EDGE_FALL) begin reg rf,sf;always @(negedge clk) begin rf<=rst_raw_n_in;sf<=p_start;end always @(posedge clk) begin rst_raw_n_out<=rf;start<=sf;end end\nelse begin always @(posedge clk) begin rst_raw_n_out<=rst_raw_n_in;start<=p_start;end end endgenerate\nendmodule';(out/'relay.sv').write_text(rtl);(out/'bench.sv').write_text(BENCH)
    cases=json.load(open(a.cases));rows=[]
    for i,c in enumerate(cases):
        T=float(c.get('period_ps',833));phase=float(c['phase_ps']);duty=float(c['duty_high_ps']);dr=float(c['reset_transport_ps']);ds=float(c['start_transport_ps'])
        if not 0<duty<T:raise ValueError('actual positive duty interval required')
        jr=1-math.floor((phase+duty-dr)/T);js=1-math.floor((phase+duty-ds)/T)
        if jr!=js:raise ValueError('RESET/START do not share a deterministic count frame')
        params={'T':T,'PHASE':phase,'DUTY':duty,'DATA_R':dr,'DATA_S':ds,'J_R':jr,'J_S':js,'EXPECT_MUTANT':int((-math.floor((phase-dr)/T)!=jr) or (-math.floor((phase-ds)/T)!=js))}
        cmd=['iverilog','-g2012','-s','tb','-o',str(out/f'case{i}.vvp')]
        cmd += [f'-Ptb.{k}={v}' for k,v in params.items()];cmd += [str(out/'relay.sv'),str(out/'bench.sv')]
        cp=subprocess.run(cmd,text=True,capture_output=True);(out/f'case{i}_compile.log').write_text(cp.stdout+cp.stderr)
        if cp.returncode:raise SystemExit(cp.returncode)
        run=subprocess.run(['vvp',str(out/f'case{i}.vvp')],text=True,capture_output=True);(out/f'case{i}.log').write_text(run.stdout+run.stderr)
        mutants=re.search(r'mutant_errors(\d+)',run.stdout);rows.append(dict(case=c,frame=dict(reset_J=jr,start_J=js),mutant_errors=int(mutants[1]) if mutants else 0,exit=run.returncode,result=run.stdout.strip().splitlines()[-1] if run.stdout.strip() else 'NO OUTPUT'))
    result=dict(schema='opentallas.two_bit_entry_phase_component.v1',source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rows=rows,verdict='PASS' if all(r['exit']==0 for r in rows) and any(r['mutant_errors']>0 for r in rows) else 'FAIL',scope='raw independent two-bit falling pre-capture topology of ODB coupon; all 4 input combinations and independent toggles; production bind/LATCHECK NOT RUN')
    (out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))
    raise SystemExit(0 if result['verdict']=='PASS' else 1)

if __name__=='__main__':main()
