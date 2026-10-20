`timescale 1ns/1ps
`default_nettype none
// Complete actual dvs_E1 -> dvs_E2 input cohort: 10 buses, 2743 bits.
// Every data/control bit shares a calendar and a reset epoch. No flow control.
module qfd_slice_ei_face_land (
 input wire ck_s, en, ck, rs,
 input wire [3:0] k,
 input wire [2742:0] i,
 output wire [2742:0] o,
 output wire fault
);
 wire [14:0] f;
 genvar g;
 generate for(g=0;g<15;g=g+1) begin : g_bank
  localparam integer W = (g==14) ? 55 : 192;
  // Kept regional boot copies: <=15 loads per external K bit, no shared
  // offset flop drives 15*4 internal pointer cones after mapping.
  (* keep = "true", dont_touch = "true" *) reg [3:0] k_boot;
  always @(posedge ck) if (!rs) k_boot <= k;
  ot_qfd_land8s #(.W(W), .ICG(0)) u_ring (
   .ck_s(ck_s), .en(en), .i(i[g*192 +: W]), .ck(ck), .rs(rs),
   .k(k_boot), .o(o[g*192 +: W]), .fault(f[g]));
 end endgenerate
 assign fault = |f;
endmodule
`default_nettype wire
