`timescale 1ns/1ps
// mutant: two key events NB-1 edges apart must raise the producer-shim spacing fault
module tb_sp; parameter integer NB=3; reg clk=0; always #1 clk=~clk; reg rst_n=0,lv=0;
 wire f; wire[7:0]a,b2,c; wire x1,x2,x3,x4; wire[(8792+NB-1)/NB-1:0]s;
 ot_hnx_idxn_kb_tx #(.NB(NB)) tx(.clk(clk),.rst_n(rst_n),.clear(1'b0),.live_v(lv),.live_index(8'd0),.key_in(8792'd0),.pre_v(1'b0),
  .pre_index(8'd0),.replay_v(1'b0),.replay_index(8'd0),.o_clear(x1),.o_live_v(x2),.o_live_index(a),.o_key_ser(s),.o_pre_v(x3),
  .o_pre_index(b2),.o_replay_v(x4),.o_replay_index(c),.fault(f));
 initial begin repeat(2)@(negedge clk); rst_n=1; @(negedge clk) lv=1; repeat(NB-2) @(negedge clk) lv=0;   // second event NB-1 edges after the first
  @(negedge clk) lv=1; @(negedge clk) lv=0; repeat(3)@(negedge clk); $display("SPACING_MUTANT NB=%0d fault=%0d %s",NB,f,f?"FAIL-as-expected":"NOT-DETECTED"); $finish; end
endmodule
