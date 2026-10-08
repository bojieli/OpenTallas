`timescale 1ns/1ps
module tb_result_delay_bank;
  reg clk=0, rst_n=1;
  reg [63:0] d=0;
  wire [63:0] q, disabled_q;
  reg [63:0] history [0:1024];
  reg [63:0] expected;
  integer cycle, reset_cycle=0, checks=0, async_resets=0;
  always #5 clk=~clk;
  ot_hbm_result_delay_bank dut(clk,rst_n,d,q);
  assign disabled_q=64'b0; // Default-off was verified at RTL; mapped bank is ENABLE1.
  task cold_reset;
    begin
      rst_n=0; #1;
      if (q!==64'b0 || disabled_q!==64'b0) $fatal(1,"asynchronous cold reset failed");
      async_resets=async_resets+1;
      #1; rst_n=1;
    end
  endtask
  initial begin
    #1; cold_reset();
    for (cycle=1; cycle<=1024; cycle=cycle+1) begin
      @(negedge clk);
      d=(64'h9e3779b97f4a7c15*cycle) ^ (64'h1 << (cycle%64));
      history[cycle]=d;
      @(posedge clk); #1;
      expected=(cycle-reset_cycle>=8) ? history[cycle-7] : 64'b0;
      if(q!==expected) $fatal(1,"cycle %0d wanted %h got %h",cycle,expected,q);
      if(disabled_q!==64'b0) $fatal(1,"default-off output changed");
      checks=checks+2;
      if(cycle==37 || cycle==299 || cycle==488) begin
        cold_reset(); reset_cycle=cycle;
      end
    end
    $display("PASS full64x8 checks=%0d captures=1024 async_resets=%0d",checks,async_resets);
    $finish;
  end
endmodule
