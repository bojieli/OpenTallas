`timescale 1ns/1ps
module tb_s81_static_hc_faults;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,write_slot=0,word_valid=0,word_error=0,emit_slot=0;
 reg[3:0]word_index=0;reg[511:0]word_data=0;reg[31:0]word_tag=42,emit_tag=42;
 wire row_valid,fault;wire[8191:0]row_data;wire[31:0]row_tag;
 s81_static_hc_assemble dut(.*);
 task clear;
 begin @(negedge clk);rst_n=0;write_slot=0;word_valid=0;emit_slot=0;word_error=0;word_tag=42;emit_tag=42;
 repeat(2)@(negedge clk);rst_n=1;end endtask
 task put(input integer idx);
 begin @(negedge clk);write_slot=1;word_valid=1;word_index=idx;word_data=idx;end endtask
 task check_fault;
 begin @(negedge clk);write_slot=0;word_valid=0;emit_slot=0;@(negedge clk);
 if(!fault||row_valid)$fatal(1,"invalid compiler event did not fail closed");end endtask
 initial begin
  clear(); // missing word at scheduled write
  @(negedge clk);write_slot=1;word_valid=0;check_fault();
  clear(); // unexpected word outside calendar
  @(negedge clk);word_valid=1;write_slot=0;check_fault();
  clear();put(0);put(0);check_fault(); // duplicate index
  clear();put(0);@(posedge clk);#1;word_tag=43;put(1);check_fault(); // different transaction
  clear();put(0);@(negedge clk);write_slot=0;word_valid=0;emit_slot=1;check_fault(); // partial row
  clear();for(integer j=0;j<16;j=j+1)put(j);
  @(negedge clk);write_slot=0;word_valid=0;emit_slot=1;emit_tag=43;check_fault(); // wrong emit tag
  clear();word_error=1;put(0);check_fault();
  clear();for(integer j=0;j<16;j=j+1)put(j);
  @(negedge clk);write_slot=1;word_valid=1;emit_slot=1;check_fault(); // overlapping reservation
  $display("PASS assembler fixed-slot fault suite: missing, unsolicited, duplicate, tag, partial, emit-tag, arithmetic, overlap");$finish;
 end
endmodule
