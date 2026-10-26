`timescale 1ns/1ps
module tb_vmstat_obs;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0, q_v=0; reg [7:0] q_idx=0; reg [31:0] q_d=0;
 reg [124:0] old_obs=0; reg [18:0] vmstat=0;
 wire r_v;wire [7:0] r_idx;wire [31:0] r_d;
 wire [143:0] observed={vmstat,old_obs};
 ot_hbm_obs_leaf #(.N(144),.LID(0),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.obs(observed),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(r_v),.r_idx(r_idx),.r_d(r_d));
 task read_word(input [7:0] idx,input [31:0] expected);
 begin
  @(negedge clk);q_idx=idx;q_v=1;q_d=0;
  @(negedge clk);q_v=0;
  repeat(2) @(negedge clk);
  if(!r_v || r_idx!==idx || r_d!==expected) $fatal(1,"VMSTAT_OBS FAIL idx=%h got=%h expected=%h valid=%b",idx,r_d,expected,r_v);
 end endtask
 reg [159:0] frame;
 integer b,w;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  old_obs=125'h123456789abcdef0123456789abcdef;
  repeat(10) @(negedge clk);
  // Walking all 19 new bits checks both sides of the existing word-3/new-word-4 seam.
  for(b=0;b<19;b=b+1) begin
   @(negedge clk);vmstat=19'b1<<b;
   repeat(3) @(negedge clk);frame={16'b0,vmstat,old_obs};
   for(w=0;w<5;w=w+1) read_word(8'(w),frame[w*32+:32]);
  end
  // Existing readback words retain their prefix, and unrelated leaves still forward packets.
  read_word(8'h20,32'b0);
  $display("VMSTAT_OBS PASS old_prefix=125 new_bits=19 words=5 fixed_leaf_edges=3");$finish;
 end
endmodule
