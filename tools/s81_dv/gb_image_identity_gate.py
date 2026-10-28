#!/usr/bin/env python3
"""Native 72-bit bank file-lookup miter; synthetic masks, not frame numerics."""
import argparse,json,subprocess
from pathlib import Path
import gb_image_identity as I
ROOT=Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True)
 ref=(ROOT/'rtl/dsrom_sys/s81_dv/frame_lp/vg/col_h10_l4_lp.sv').read_text()
 src=(ROOT/'results/token_pass/gb_candidate_1355/src/actual_col_h10_plan_gb.sv').read_text()
 fixed,rec=I.restore(src,ref)
 assert rec['restored']==185
 # An existing wrong identity is refused rather than silently overwritten.
 wrong=fixed.replace('.INSTANCE({INSTANCE, "_c0_1"})','.INSTANCE({INSTANCE, "_c0_0"})',1)
 try:I.restore(wrong,ref)
 except ValueError as e:assert 'differs from canonical' in str(e)
 else:raise AssertionError('identity collision mutant admitted')
 for bank in range(2):
  lines=[]
  for row in range(512):
   value=0
   for bit in range(72):
    for sel in range(8):
     addr=row*8+sel
     one=((addr*0x9e3779b97f4a7c15 + bank*0xd1b54a32d192ed03) ^ (addr<<(bit%13)) ^ (bit*0x45d9f3b))>> (bit%53)&1
     value|=one<<(bit*8+sel)
   lines.append(f'{value:0144x}')
  (a.out/f'f_c0_{bank}.viamap.hex').write_text('\n'.join(lines)+'\n')
 tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
reg [11:0] addr=0;wire[71:0]r0,r1,c0,c1;integer mut=0;
ot_rom_4096x72_m8 #(.INSTANCE("f_c0_0")) ref0(clk,1'b1,addr,r0);
ot_rom_4096x72_m8 #(.INSTANCE("f_c0_1")) ref1(clk,1'b1,addr,r1);
ot_rom_4096x72_m8 #(.INSTANCE({"f","_c0_0"})) can0(clk,1'b1,addr,c0);
wire[71:0]good,bad;
ot_rom_4096x72_m8 #(.INSTANCE({"f","_c0_1"})) can1(clk,1'b1,addr,good);
ot_rom_4096x72_m8 #(.INSTANCE({"f","_c0_0"})) wrongbank(clk,1'b1,addr,bad);
assign c1=mut?bad:good;
initial begin
if($value$plusargs("MUT=%d",mut))begin end
for(integer n=0;n<4096;n=n+1)begin
 @(negedge clk);addr=12'(n);@(posedge clk);#0.001;
 if(c0!==r0 || c1!==r1)$fatal(1,"IMAGE_BIND_DIFF addr%0d mutant%0d",n,mut);
end
$display("GB_IMAGE_BIND_PASS 8192words 72bits 833ps");$finish;
end endmodule
'''
 (a.out/'tb.sv').write_text(tb)
 with (a.out/'build.log').open('w') as f:
  subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(a.out/'obj'),str(ROOT/'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v'),str(a.out/'tb.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
 for m in (0,1):
  with(a.out/f'run{m}.log').open('w')as f:r=subprocess.run([str(a.out/'obj/Vtb'),f'+MUT={m}',f'+OT_ROM_DIR={a.out}'],stdout=f,stderr=subprocess.STDOUT)
  log=(a.out/f'run{m}.log').read_text();assert (r.returncode==0 and 'GB_IMAGE_BIND_PASS'in log)if m==0 else(r.returncode!=0 and'IMAGE_BIND_DIFF'in log),log
 rec.update(pass_=True,native_words=8192,bits=72,clock_ps=833,collision_mutant='CAUGHT',wrong_native_bank_mutant='CAUGHT',full_frame_qualified=False,mask_data='synthetic mechanism vectors')
 (a.out/'check.json').write_text(json.dumps(rec,indent=1)+'\n');print('GB_IMAGE_IDENTITY_PASS native+static collision mutants CAUGHT')
if __name__=='__main__':main()
