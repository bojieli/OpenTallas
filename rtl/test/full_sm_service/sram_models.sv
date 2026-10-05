`timescale 1ns/1ps
// Functional one-cycle macro models only; no corner/timing/abstract qualification.
module ot_sram_1r1w_128x256_m1_r2c2 (
 input wire clk,r_ce_in,w_ce_in,input wire [6:0] r_addr_in,w_addr_in,
 output reg [255:0] rd_out,input wire [255:0] wd_in,w_mask_in,
 input wire [1:0] rr_en,cr_en,input wire [11:0] rr_addr,input wire [15:0] cr_sel
);
 reg [255:0] mem[0:127];
 always @(posedge clk) begin
  if(r_ce_in && w_ce_in && r_addr_in==w_addr_in) $fatal(1,"RF read/write collision");
  if(r_ce_in) rd_out<=mem[r_addr_in];
  if(w_ce_in) mem[w_addr_in]<=(wd_in & w_mask_in)|(mem[w_addr_in] & ~w_mask_in);
 end
endmodule
module ot_sram_1r1w_1024x256_m2_r2c2 (
 input wire clk,r_ce_in,w_ce_in,input wire [9:0] r_addr_in,w_addr_in,
 output reg [255:0] rd_out,input wire [255:0] wd_in,w_mask_in,
 input wire [1:0] rr_en,cr_en,input wire [17:0] rr_addr,input wire [15:0] cr_sel
);
 reg [255:0] mem[0:1023];
 always @(posedge clk) begin
  if(r_ce_in && w_ce_in && r_addr_in==w_addr_in) $fatal(1,"scratch read/write collision");
  if(r_ce_in) rd_out<=mem[r_addr_in];
  if(w_ce_in) mem[w_addr_in]<=(wd_in & w_mask_in)|(mem[w_addr_in] & ~w_mask_in);
 end
endmodule
