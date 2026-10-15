"""Fixed-slot argmax protocol/finite IEEE ordering tests with genuine DUT mutation."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
def test_static_argmax():
 with tempfile.TemporaryDirectory(prefix='mtp-static-argmax-')as d:
  p=Path(d);src=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_s81_markov_static_argmax.sv'
  tb=p/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,clear_slot=0,candidate_slot=0,carry_slot=0,result_slot=0,candidate_valid=0,carry_valid=0;
 reg[31:0]candidate_bits=0,carry_bits=0;reg[16:0]candidate_row=0,carry_row=0;
 reg[59:0]candidate_identity=7,carry_identity=7,identity=7;
 wire result_valid,fault;wire[31:0]result_bits;wire[16:0]result_row;wire[59:0]result_identity;
 ot_s81_markov_static_argmax dut(.*);
 task step;begin @(negedge clk);#1;end endtask
 task candidate(input[31:0]bits,input[16:0]row);begin candidate_slot=1;candidate_valid=1;candidate_bits=bits;candidate_row=row;step();candidate_slot=0;candidate_valid=0;step();end endtask
 task clear;begin clear_slot=1;step();clear_slot=0;step();end endtask
 task result(input[31:0]bits,input[16:0]row);begin result_slot=1;step();if(!result_valid||result_bits!==bits||result_row!==row||result_identity!=7||fault)$fatal(1,"argmax failed");result_slot=0;step();if(result_valid)$fatal(1,"stretched result");end endtask
 initial begin
  repeat(3)step();rst_n=1;step();clear();
  candidate(32'hc0000000,8);candidate(32'hbf800000,9);candidate(32'h80000000,10);candidate(32'h00000000,7);result(32'h00000000,7);
  clear();candidate(32'h3f800000,100);candidate(32'h40000000,101);
  carry_slot=1;carry_valid=1;carry_bits=32'h40000000;carry_row=99;step();carry_slot=0;carry_valid=0;step();result(32'h40000000,99);
  clear();candidate_identity=8;candidate(32'h3f800000,4);if(!fault)$fatal(1,"wrong identity accepted");
  $display("STATIC_ARGMAX PASS finiteordering zero_tie rowtie carry fixedpulse identityfault");$finish;
 end
endmodule
''')
  for mutant in(0,1):
   actual=p/f'dut{mutant}.sv'
   text=src.read_text()
   if mutant:text=text.replace('row<best_row','row>best_row')
   actual.write_text(text);exe=p/f'run{mutant}'
   subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(actual),str(tb)],check=True,capture_output=True)
   r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
   if mutant:assert r.returncode!=0 and'argmax failed'in r.stdout,r.stdout
   else:assert r.returncode==0 and'STATIC_ARGMAX PASS'in r.stdout,r.stdout
