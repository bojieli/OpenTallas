`timescale 1ns/1ps
`default_nettype none
// One local residual half. Explicit first-pin write registers add ONE write
// edge: external sample n -> physical SRAM commit n+1. Compiler must price it.
// v2 (H-NETLIST/kits 2026-10-16, native pin audit of the CLOSED v1 route hbm_hc_residual_half_static-native1-ea5b169e7:
// capture S+R 293.2 ps on rst_n and 231.8..250.7 ps on read_word[9:0] / 192.2 on read_v > 190, because they landed
// directly on the SRAM input latch / async clears): read_v/read_word now captured in first-pin flops too and rst_n
// reaches the two valid pin flops and ONE reset pin flop (async assert, sync release) that resets the rest.
// Read sample n -> pin flop n+1 -> macro n+2 -> raw n+2 -> output n+3 -> downstream MAC input n+4 (TML4, +1 read edge
// vs v1 TML3: the HC engine schedule must add it).
// v3 (H-NETLIST/vmdel 2026-10-16, native audit of the CLOSED v2 route hbm_hc_residual_half_static-native1-36070f827:
// capture 243.8 ps > 190 on rst_n, the only failing pin: rst_n still reached three async-clear / recovery endpoints).
// rst_n now lands ONLY on the D pin of one dedicated synchronous pin flop rst_s (no async clear); the two valid pin
// flops are plain data pin flops (the ports are held 0 while the die is in reset), and every other flop resets from
// rst_s.  Release timing is unchanged (state first updates on the second edge after rst_n rises, as v2's rst_q);
// reset assertion takes effect one edge after rst_n falls (synchronous reset: the die clock runs during reset).
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
 reg rst_s;  // the only rst_n load: a synchronous pin flop (D = rst_n)
 always @(posedge clk) rst_s<=rst_n;
 reg wv_q,rv_p,rv_q,rv_qq;
 reg [9:0] wa_q,ra_q;
 reg [255:0] wd_q,raw_capture;
 wire [255:0] raw;
 always @(posedge clk)begin
  wa_q<=write_word;wd_q<=write_data;ra_q<=read_word;
  raw_capture<=raw;residual_data<=raw_capture;
 end
 // the two valid pin flops are plain data pin flops (a command on the first edge after release is captured, as in v1)
 always @(posedge clk) begin wv_q<=write_v;rv_p<=read_v;end
 always @(posedge clk)begin
  if(!rst_s)begin rv_q<=0;rv_qq<=0;read_valid<=0;fault<=0;end
  else begin
   rv_q<=rv_p;rv_qq<=rv_q;read_valid<=rv_qq;
   if(wv_q&&wa_q>=640)fault<=1;
   if(wv_q&&rv_p&&wa_q==ra_q)fault<=1;
  end
 end
 ot_sram_1r1w_1024x256_m2_r2c2 u_residual(
  .clk(clk),.r_ce_in(rv_p),.r_addr_in(ra_q),.rd_out(raw),
  .w_ce_in(wv_q),.w_addr_in(wa_q),.wd_in(wd_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'd0),.rr_addr(18'd0),.cr_en(2'd0),.cr_sel(16'd0));
endmodule
`default_nettype wire
