`timescale 1ns/1ps
`default_nettype none
// One local residual half. Explicit first-pin write registers add ONE write
// edge: external sample n -> physical SRAM commit n+1. Compiler must price it.
// Read macro n -> raw n+1 -> output n+2 -> downstream MAC input n+3 (TML3).
module ot_hgi_hc_residual_half_static(
 input wire clk,rst_n,
 input wire write_v,
 input wire [9:0] write_word,
 input wire [255:0] write_data,
 input wire read_v,
 input wire [9:0] read_word,
 output reg read_valid,fault,
 output reg [255:0] residual_data
);
 reg wv_q,rv_q,rv_qq;
 reg [9:0] wa_q;
 reg [255:0] wd_q,raw_capture;
 wire [255:0] raw;
 always @(posedge clk)begin
  wa_q<=write_word;wd_q<=write_data;
  raw_capture<=raw;residual_data<=raw_capture;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wv_q<=0;rv_q<=0;rv_qq<=0;read_valid<=0;fault<=0;end
  else begin
   wv_q<=write_v;rv_q<=read_v;rv_qq<=rv_q;read_valid<=rv_qq;
   if(wv_q&&wa_q>=640)fault<=1;
   if(wv_q&&read_v&&wa_q==read_word)fault<=1;
  end
 end
 ot_sram_1r1w_1024x256_m2_r2c2 u_residual(
  .clk(clk),.r_ce_in(read_v),.r_addr_in(read_word),.rd_out(raw),
  .w_ce_in(wv_q),.w_addr_in(wa_q),.wd_in(wd_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'd0),.rr_addr(18'd0),.cr_en(2'd0),.cr_sel(16'd0));
endmodule
`default_nettype wire
