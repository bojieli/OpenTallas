`timescale 1ns/1ps
`default_nettype none
// Receiver-face source candidate for actual g5 st_ei/st_wi (1088 bits).
// Six SRAM ring slices share the SAME source clock, receiver clock, reset epoch
// and reset-programmed K. No credits/stall. Not adopted by any released parent.
module qfd_slice_st_face_land (
 input wire ck_s, en, ck, rs,
 input wire [3:0] k,
 input wire [1087:0] i,
 output wire [1087:0] o,
 output wire fault
);
 // Boot configuration captured only while receiver reset is asserted.
 // Reset must span >=2 receiving edges, as required by the ring reset landing.
 reg [3:0] k_boot;
 always @(posedge ck) if (!rs) k_boot <= k;
 wire [5:0] f;
 genvar g;
 generate for(g=0;g<6;g=g+1) begin : g_bank
  localparam integer W = (g==5) ? 128 : 192;
  ot_qfd_land8s #(.W(W), .ICG(0)) u_ring (
   .ck_s(ck_s), .en(en), .i(i[g*192 +: W]), .ck(ck), .rs(rs),
   .k(k_boot), .o(o[g*192 +: W]), .fault(f[g]));
 end endgenerate
 assign fault = |f;
endmodule
`default_nettype wire
