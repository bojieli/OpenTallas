#!/usr/bin/env python3
"""Canonical seam vs functional-cut seam; one removed-boundary-stage mutant."""
import argparse
import json
from pathlib import Path
import subprocess
from gb_functional_source import seam_module

ROOT = Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
canonical=(ROOT/'physical/die_plan/s81/bind/models/s81_asb_models.sv').read_text()
functional=(ROOT/'results/token_pass/gb_candidate_1355/src/functional_s81_asb_models.sv').read_text()
ref=seam_module(canonical).group();gold=seam_module(functional).group()
assert ref==gold, 'functional overlay differs from canonical seam source'
mut=gold.replace('b <= a;', 'b <= d;')
assert mut!=gold
tb='''`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;reg[1263:0]d=0;
wire[1263:0]r,g,b;integer mutant=0;
ref_fint #(.W(1264)) refdut(clk,clk,d,r);
gold_fint #(.W(1264)) golddut(clk,clk,d,g);
bad_fint #(.W(1264)) baddut(clk,clk,d,b);
initial begin
if($value$plusargs("MUT=%d",mutant))begin end
for(int n=0;n<514;n++)begin
 @(negedge clk);for(int k=0;k<40;k++)begin if(k<39)d[32*k+:32]=$urandom;else d[1248+:16]=16'($urandom);end
 @(posedge clk);#0.001;
 if(n>=2 && (mutant?b:g)!==r)$fatal(1,"SEAM_DIFF edge%0d mutant%0d",n,mutant);
end
$display("GB_FUNCTIONAL_SEAM PASS512 full1264-bit comparisons,833ps,addedcycles0");$finish;
end endmodule
'''
src='\n'.join([ref.replace('module s81b_fint','module ref_fint',1),gold.replace('module s81b_fint','module gold_fint',1),mut.replace('module s81b_fint','module bad_fint',1),tb])
(a.out/'tb.sv').write_text(src)
with (a.out/'build.log').open('w') as f:
 subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(a.out/'obj'),str(a.out/'tb.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
for m in (0,1):
 with (a.out/f'run{m}.log').open('w') as f:r=subprocess.run([str(a.out/'obj/Vtb'),f'+MUT={m}'],stdout=f,stderr=subprocess.STDOUT)
 log=(a.out/f'run{m}.log').read_text()
 assert (r.returncode==0 and 'PASS512' in log) if m==0 else (r.returncode!=0 and 'SEAM_DIFF' in log),log
(a.out/'check.json').write_text(json.dumps(dict(pass_=True,comparisons=512,width=1264,clock_ps=833,added_cycles=0,removed_stage_mutant='CAUGHT'),indent=2)+'\n')
print('GB_FUNCTIONAL_SEAM_LOCKSTEP_PASS MUTANT_CAUGHT')
