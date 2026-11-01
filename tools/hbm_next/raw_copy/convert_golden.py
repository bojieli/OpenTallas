#!/usr/bin/env python3
"""Emit independent bit-golden vectors and a smallest real conversion-part miter."""
import argparse
from pathlib import Path
from formats_probe import decode,F32,BF16
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
v=[]
for fmt in [0,1,2,4,5,6]:
 for raw in (F32 if fmt in [0,5] else BF16 if fmt==1 else range(256)):
  v.append((fmt<<64)|(raw<<32)|decode(raw,fmt))
(a.out/'vectors.mem').write_text(''.join(f'{x:017x}\n'for x in v))
(a.out/'tb_convert_golden.sv').write_text('''`timescale 1ps/1fs
module tb_convert_golden;
reg clk=0;always #416.5 clk=~clk;
reg[2:0]fmt=0;reg[31:0]raw=0;wire[31:0]q,qmut;
for(genvar b=0;b<4;b++)begin
 ot_hbm_dma_convert_part #(.PART(b)) dut(clk,fmt,raw,q[b*8+:8]);
 ot_hbm_dma_convert_part #(.PART(b),.MUT(1)) mutant(clk,fmt,raw,qmut[b*8+:8]);
end
reg[67:0]vectors[0:NVECS-1];integer mutate=0;
initial begin
 if($value$plusargs("MUT=%d",mutate))begin end
 $readmemh("vectors.mem",vectors);
 for(integer i=0;i<NVECS;i++)begin
  @(negedge clk);fmt=vectors[i][66:64];raw=vectors[i][63:32];
  repeat(7)@(negedge clk);
  if((mutate?qmut:q)!==vectors[i][31:0])$fatal(1,"CONVERT_GOLDEN_MISMATCH index=%0d fmt=%0d raw=%h actual=%h expected=%h",i,fmt,raw,mutate?qmut:q,vectors[i][31:0]);
 end
 $display("PASS CONVERT_ALL256_E4_INT8_UE8_ALL6 vectors=NVECS");$finish;
end
endmodule
'''.replace('NVECS',str(len(v))))
print(len(v),'vectors')
