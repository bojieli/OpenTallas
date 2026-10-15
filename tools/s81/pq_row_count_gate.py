#!/usr/bin/env python3
"""Exercise the actual native controller count-tree block at production width.

The block is extracted verbatim because unrelated loader/ROM logic does not
belong in this unit test. This is not a production phase/composition gate.
"""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
p.add_argument('--mutant', action='store_true')
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
source = Path('rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_native.sv').read_text()
block = source[source.index('    localparam integer NCA ='):source.index('    // ------------------------------------------------------------------ control\n')]
if a.mutant:
    block = block.replace('localparam integer NCA = NGR;', 'localparam integer NCA = NGR - 1;')
bench = '''`timescale 1ns/1ps
module tb_count;
localparam integer R=128, RG=11, NGR=(R+RG-1)/RG;
reg clk=0,rst_c=0; always #0.4166 clk=~clk;
reg[16*NGR-1:0] ga_i=0;
integer kt,kq;
''' + block + '''
integer errors=0,cyc=0,k,t,n,left,cnt;
reg[7:0] expected0[0:3],expected1[0:3],total[0:3];
initial begin
 for(t=0;t<4;t++) begin expected0[t]=0;expected1[t]=0;end
 repeat(8) @(negedge clk);rst_c=1;
 for(cyc=0;cyc<5000;cyc++) begin
  @(negedge clk);
  for(t=0;t<4;t++) total[t]=0;
  for(k=0;k<NGR;k++) begin
   // Actual topology-G 15/2/15 tiling: four groups of 32 regions.
   left=(k%3==1)?2:15;
   for(t=0;t<4;t++) begin
    cnt=(cyc%5==0)?((t==cyc%4)?left:0):($urandom%(left+1));
    ga_i[16*k+4*t+:4]=cnt;total[t]=total[t]+cnt;left=left-cnt;
   end
  end
  @(posedge clk);#0.001;
  for(t=0;t<4;t++) begin
   if(rc[t] !== expected1[t]) begin
    errors++;
    if(errors<5) $display("COUNT mismatch cycle=%0d tag=%0d actual=%0d expected=%0d",cyc,t,rc[t],expected1[t]);
   end
   expected1[t]=expected0[t];expected0[t]=total[t];
  end
 end
 $display("PQ_COUNT %s cycles=%0d errors=%0d",errors==0?"PASS":"FAIL",cyc,errors);
 $finish;
end
endmodule
'''
(a.out/'tb_count.sv').write_text(bench)
cmd = ['verilator','--binary','--timing','-j','8','-Wno-fatal','--top-module','tb_count','--Mdir',str(a.out/'obj'),str(a.out/'tb_count.sv'),'rtl/common/ot_prefix.sv']
with (a.out/'build.log').open('w') as f:
    subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
r = subprocess.run([str((a.out/'obj/Vtb_count').resolve())], text=True, capture_output=True, check=True)
(a.out/'run.log').write_text(r.stdout)
print(r.stdout)
if ('PQ_COUNT FAIL' if a.mutant else 'PQ_COUNT PASS') not in r.stdout:
    raise SystemExit(1)
