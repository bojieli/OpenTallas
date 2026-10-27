#!/usr/bin/env python3
"""Check distinct image identity and zero extra cycles across one shared Verilated ROM type."""
import argparse,json,os,subprocess
from pathlib import Path
from head_token_sources import scope_rom_model
ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
imgs=a.out/'images';imgs.mkdir()
for i in (0,1):
 p=Path(f'results/rtl/s81_head_tile_1021/img/ha{i}_0.viamap.hex')
 if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show','HEAD:'+str(p)]))
 (imgs/f'tb_head_hier.dut{i}.head_rom_cell.r.viamap.hex').symlink_to(os.path.relpath(p,imgs))
macro=Path('physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v').read_text()
(a.out/'scope.sv').write_text(scope_rom_model(macro))
(a.out/'reference.sv').write_text(macro.replace('module ot_rom_4096x274_m8 ', 'module ot_rom_reference ',1))
tb=r'''`timescale 1ns/100fs
module head_rom_cell(input wire ck,ce,input wire[11:0]addr,output wire[273:0]q);
/*verilator hier_block*/
ot_rom_4096x274_m8 r(.clk(ck),.ce_in(ce),.addr_in(addr),.rd_out(q));
endmodule
module tb_head_hier;
reg ck=0;always #0.4165 ck=~ck;
reg[11:0]addr=0;wire[273:0]a0,a1,b0,b1;
ot_rom_reference #(.VIAMAP("results/rtl/s81_head_tile_1021/img/ha0_0.viamap.hex"))ref0(.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(a0));
ot_rom_reference #(.VIAMAP("results/rtl/s81_head_tile_1021/img/ha1_0.viamap.hex"))ref1(.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(a1));
head_rom_cell dut0(.ck(ck),.ce(1'b1),.addr(addr),.q(b0));
head_rom_cell dut1(.ck(ck),.ce(1'b1),.addr(addr),.q(b1));
integer n,checks=0;
initial begin
 for(n=0;n<4098;n++)begin
  @(posedge ck);#1ps;
  if(a0!==b0||a1!==b1)$fatal(1,"HEAD_HIER_IMAGE wrong image or cycle at%0d",n);
  checks+=2;@(negedge ck);addr=(n+1)&4095;
 end
 $display("HEAD_HIER_IMAGE PASS checks%0d banks2 shared_type1 clock833ps added_cycles0",checks);$finish;
end
endmodule
'''
(a.out/'tb.sv').write_text(tb)
with(a.out/'build.log').open('w')as f:
 subprocess.run(['verilator','--binary','--hierarchical','--timing','-O1','-Wno-fatal','--top-module','tb_head_hier','--Mdir',str(a.out/'obj'),'--build-jobs','8',str(a.out/'scope.sv'),str(a.out/'reference.sv'),str(a.out/'tb.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
exe=a.out/'obj/Vtb_head_hier'
with(a.out/'positive.log').open('w')as f:p=subprocess.run([str(exe),'+OT_HEAD_ROM_DIR='+str(imgs)],stdout=f,stderr=subprocess.STDOUT)
if p.returncode or'HEAD_HIER_IMAGE PASS'not in(a.out/'positive.log').read_text():raise SystemExit('hierarchical baseline failed')
q=imgs/'tb_head_hier.dut1.head_rom_cell.r.viamap.hex';q.unlink();q.symlink_to(os.path.relpath(Path('results/rtl/s81_head_tile_1021/img/ha0_0.viamap.hex'),imgs))
with(a.out/'wrong_bank.log').open('w')as f:p=subprocess.run([str(exe),'+OT_HEAD_ROM_DIR='+str(imgs)],stdout=f,stderr=subprocess.STDOUT)
if not p.returncode or'HEAD_HIER_IMAGE wrong image or cycle'not in(a.out/'wrong_bank.log').read_text():raise SystemExit('hierarchical wrong-bank control missed')
(a.out/'result.json').write_text(json.dumps(dict(verdict='PASS',checks=8196,banks=2,shared_type=1,added_cycles=0,wrong_bank_caught=True,scope='hierarchical source method only; no head token or FT adapter claim'),indent=2)+'\n')
print('HEAD_HIER_IMAGE_GATE PASS')
