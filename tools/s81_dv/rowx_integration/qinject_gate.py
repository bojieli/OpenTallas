#!/usr/bin/env python3
"""Smallest lockstep of the zero-cycle entry-q adapter, including exclusive-window assertions."""
import argparse, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
tb='''`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg rst_n=0,book=0,nv=0,rv=0;reg[511:0]nd=0,rd=0;
wire qv,fault;wire[511:0]qd;
dsdv_rowx_qinject #(.MUT(MUTANT)) d(clk,rst_n,book,nv,nd,rv,rd,qv,qd,fault);
integer n=0;reg expected_fault=0;
task check;
begin #0.001;if(qv!==(book?rv:nv)||qd!==(book?rd:nd))$fatal(1,"zero-cycle payload/valid mismatch at%0d",n);
@(posedge clk);#0.001;if(fault!==expected_fault)$fatal(1,"collision assertion at%0d",n);n=n+1;end endtask
initial begin
repeat(2)@(negedge clk);rst_n=1;
// Existing normal q traffic and a 2050-edge reservation with booked idle gaps.
for(int j=0;j<2097;j++)begin
 @(negedge clk);book=(j>=40&&j<2090);nv=!book&&(j%3!=0);rv=book&&(j%17!=0);
 for(int k=0;k<16;k++)begin nd[32*k+:32]=$urandom;rd[32*k+:32]=$urandom;end
 check();
end
@(negedge clk);book=1;nv=1;rv=0;expected_fault=1;check();
@(negedge clk);nv=0;book=0;rv=0;check();
@(negedge clk);rst_n=0;#0.001;expected_fault=0;check();
@(negedge clk);rst_n=1;book=0;rv=1;expected_fault=1;check();
$display("ROWX_QINJECT_GATE PASS %0d lockstep edges, booked-normal and unbooked-XM collisions caught, addedcycles0",n);$finish;
end endmodule
'''.replace('MUTANT',str(a.mutant))
(a.out/'tb.sv').write_text(tb)
cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(a.out/'obj'),str(ROOT/'rtl/dsrom_sys/s81_dv/svc_rs/rowx/dsdv_rowx_qinject.sv'),str(a.out/'tb.sv')]
with (a.out/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (a.out/'run.log').open('w') as f:r=subprocess.run([str(a.out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT)
print((a.out/'run.log').read_text(),end='');raise SystemExit(r.returncode)
