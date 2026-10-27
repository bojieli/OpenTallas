#!/usr/bin/env python3
"""Prove hierarchy image assignment against original ROM VIAMAP initialization.
Run through ot-run after staging the released HEAD images at SK11.
"""
import argparse,json,subprocess,os
from pathlib import Path
from head_token_sources import scope_rom_model
ap=argparse.ArgumentParser();ap.add_argument('images',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
scope_dir=a.out/'images';scope_dir.mkdir()
for name,src in [('dut0','ha0_0.viamap.hex'),('dut1','ha1_0.viamap.hex')]:
 (scope_dir/('tb_head_images.'+name+'.viamap.hex')).symlink_to(os.path.relpath(a.images/src,scope_dir))
# Same checked-in full 4096x274 model on every side. Only initial image lookup differs.
ref0=str(a.images/'ha0_0.viamap.hex');ref1=str(a.images/'ha1_0.viamap.hex')
tb=r'''`timescale 1ns/100fs
module tb_head_images;
reg ck=0;always #0.4165 ck=~ck;
reg ce=1;reg[11:0]addr=0;wire[273:0]a0,a1,b0,b1;
ot_rom_4096x274_m8 #(.VIAMAP("REF0")) ref0(.clk(ck),.ce_in(ce),.addr_in(addr),.rd_out(a0));
ot_rom_4096x274_m8 #(.VIAMAP("REF1")) ref1(.clk(ck),.ce_in(ce),.addr_in(addr),.rd_out(a1));
ot_rom_4096x274_m8 dut0(.clk(ck),.ce_in(ce),.addr_in(addr),.rd_out(b0));
ot_rom_4096x274_m8 dut1(.clk(ck),.ce_in(ce),.addr_in(addr),.rd_out(b1));
LOADER
initial begin
 if($test$plusargs("MUT_BANK"))begin #2ps; $readmemh("REF0",dut1.arr);end
end
integer n,checks=0;
initial begin
 for(n=0;n<4098;n++)begin
  @(posedge ck);#1ps;
  if(a0!==b0||a1!==b1)$fatal(1,"HEAD_IMAGE miter wrong image bank at%0d",n);
  checks+=2;
  @(negedge ck);addr=(n+1)&4095;
 end
 $display("HEAD_IMAGE_MITER PASS full4096x274 banks2 checks%0d target_clock833ps",checks);$finish;
end
endmodule
'''.replace('REF0',ref0).replace('REF1',ref1).replace('LOADER','')
(a.out/'tb_head_images.sv').write_text(tb)
macro0=Path('physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v')
macro=a.out/'ot_rom_4096x274_m8_scope.sv';macro.write_text(scope_rom_model(macro0.read_text()))
with(a.out/'build.log').open('w')as f:
 subprocess.run(['verilator','--binary','--timing','-O1','-Wno-fatal','--top-module','tb_head_images','--Mdir',str(a.out/'obj'),'--build-jobs','8',str(macro),str(a.out/'tb_head_images.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
results={}
for label,args in [('positive',[]),('wrong_bank',['+MUT_BANK'])]:
 with(a.out/(label+'.log')).open('w')as f:
  p=subprocess.run([str(a.out/'obj/Vtb_head_images'),'+OT_HEAD_ROM_DIR='+str(scope_dir)]+args,stdout=f,stderr=subprocess.STDOUT)
 log=(a.out/(label+'.log')).read_text()
 good=(p.returncode==0 and 'HEAD_IMAGE_MITER PASS' in log)if label=='positive'else(p.returncode!=0 and'HEAD_IMAGE miter wrong image bank'in log)
 results[label]=dict(returncode=p.returncode,qualified=good)
 if not good:raise SystemExit(label+' failed, see '+str(a.out))
with(a.out/'missing_image.log').open('w')as f:
 p=subprocess.run([str(a.out/'obj/Vtb_head_images'),'+OT_HEAD_ROM_DIR='+str(a.out/'missing')],stdout=f,stderr=subprocess.STDOUT)
if p.returncode==0 or 'HEAD missing scope image' not in (a.out/'missing_image.log').read_text():raise SystemExit('missing-image negative control failed')
results['missing_image']=dict(returncode=p.returncode,qualified=True)
(a.out/'result.json').write_text(json.dumps(dict(verdict='PASS',results=results,added_cycles=0,scope='ROM initialization only; no whole-head/token claim'),indent=2)+'\n')
print('HEAD_IMAGE_ASSIGNMENT_GATE PASS')
