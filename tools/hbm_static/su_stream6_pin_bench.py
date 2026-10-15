#!/usr/bin/env python3
"""Exact real-SRAM stream6 boundary/clock gate; run through ot-run."""
import argparse, json, os, subprocess
from pathlib import Path
import su_programme_compile as compiler
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 m=compiler.lower(a.image,out,line_bits=64,index_pack=16,param_prefix='STREAM')
 assert m['edges']==9489 and m['total_macros']==6 and m['dictionary_banks']==[1]
 tb=(out/'tb.sv').read_text()
 start=tb.index('ot_hbm_su_programme #');end=tb.index('task automatic tick;',start)
 tb=tb[:start]+"""integer halt_macro=-1;
wire[5:0] macro_clock={6{clk}} & (halt_macro<0?6'h3f:~(6'd1<<halt_macro));
ot_hbm_su_stream_calendar6_pin dut(
 .clk(clk),.clk_macro0(macro_clock[0]),.clk_macro1(macro_clock[1]),.clk_macro2(macro_clock[2]),
 .clk_macro3(macro_clock[3]),.clk_macro4(macro_clock[4]),.clk_macro5(macro_clock[5]),
 .rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
 .start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),
 .edge_index(edge_index),.command(command));
"""+tb[end:]
 tb=tb.replace('k<2;k=k+1','k<3;k=k+1').replace('tick(); @(negedge clk); rst_n=1;', 'repeat(3)tick(); @(negedge clk); rst_n=1;')
 tb=tb.replace('data_mut=$test$plusargs', 'if($test$plusargs("MUT_CLOCK"))halt_macro=5;\n data_mut=$test$plusargs')
 (out/'tb.sv').write_text(tb)
 clock="""`timescale 1ns/1ps
module tb_clock;
reg[5:0] pulse=0; integer counts[0:5]; bit collapse,swap;
wire[5:0] mapped=collapse?{6{pulse[0]}}:swap?{pulse[5:2],pulse[0],pulse[1]}:pulse;
ot_hbm_su_stream_calendar6_pin dut(.clk(1'b0),.clk_macro0(mapped[0]),.clk_macro1(mapped[1]),.clk_macro2(mapped[2]),
 .clk_macro3(mapped[3]),.clk_macro4(mapped[4]),.clk_macro5(mapped[5]),.rst_n(1'b0),
 .cfg_we(1'b0),.cfg_bank(16'd0),.cfg_row(7'd0),.cfg_data(256'd0),.start(1'b0),.length(16'd0),
 .busy(),.valid(),.done(),.fault(),.edge_index(),.command());
"""
 for i in range(6):
  path=f'ix[0].mem.g[{i}].mem' if i<5 else 'dt[0].mem.g[0].mem'
  clock+=f'always @(posedge dut.u_programme.{path}.clk) counts[{i}]++;\n'
 clock+="""initial begin
 collapse=$test$plusargs("COLLAPSE");swap=$test$plusargs("SWAP");
 for(integer i=0;i<6;i++)counts[i]=0;
 for(integer root=0;root<6;root++)begin
  #2;pulse=6'd1<<root;#2;
  for(integer i=0;i<6;i++)if(counts[i]!=(i<=root?1:0))$fatal(1,"STREAM6_CLOCK FAIL root=%0d leaf=%0d",root,i);
  pulse=0;
 end
 $display("STREAM6_CLOCK PASS checks=36");$finish;
end
endmodule
"""
 (out/'tb_clock.sv').write_text(clock)
 vl=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
 sources=[ROOT/'rtl/hbm_accel/generic/adapters/static_su/programme'/x for x in ['ot_hbm_su_programme.sv','ot_hbm_su_stream_calendar6_pin.sv']]
 sources+=[ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
 for top,bench,mutants,mark in [('tb','tb.sv',['DATA','ADDR','PHASE','CLOCK'],'SU_PROGRAMME'),('tb_clock','tb_clock.sv',['COLLAPSE','SWAP'],'STREAM6_CLOCK')]:
  obj=out/top
  with (out/f'{top}_build.log').open('w') as f:subprocess.run([vl,'--binary','--timing','-O1','-j','1','-Wno-fatal','--top-module',top,'--Mdir',str(obj),*map(str,sources),str(out/bench)],stdout=f,stderr=subprocess.STDOUT,check=True)
  for mut in ['positive',*mutants]:
   log=out/f'{top}_{mut}.log';args=[str(obj/f'V{top}'),f'+DIR={out}']
   if mut!='positive':args+=[f'+MUT_{mut}' if top=='tb' else f'+{mut}']
   with log.open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
   msg=log.read_text();expected='PASS' if mut=='positive' else 'FAIL'
   assert (r.returncode==0)==(mut=='positive') and f'{mark} {expected}' in msg,(mut,r.returncode,msg[-1000:])
 print('SU_STREAM6_PIN_GATE PASS edges=9489 restarts=2 clock_checks=36 semantic_mutants=4 clock_mutants=2')
if __name__=='__main__':main()
