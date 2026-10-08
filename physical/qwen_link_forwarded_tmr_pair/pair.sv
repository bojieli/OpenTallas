// Minimum full two-hop NL1 bidirectional physical vehicle. Source-synchronous
// ba travels east to west; ab west to east. No clock mux, gating or shared root.
module ot_qwen_link_forwarded_tmr_pair(
 input wire rst_n, clk_ab, clk_ba,
 input wire [527:0] a_i,b_i,
 output wire [527:0] a_o,b_o,
 output wire clk_ab_o,clk_ba_o
);
 wire ab_mid,ba_mid;
 wire [527:0] ab_data,ba_data;
 (* keep_hierarchy=1 *) ot_qwen_die_link_fwd_full_tmr #(.NL(1),.ENABLE(1)) s0(
  .rst_n(rst_n),.fclk_ab_i(clk_ab),.fclk_ab_o(ab_mid),
  .fclk_ba_i(ba_mid),.fclk_ba_o(clk_ba_o),
  .a_i(a_i),.b_o(ab_data),.b_i(ba_data),.a_o(a_o));
 (* keep_hierarchy=1 *) ot_qwen_die_link_fwd_full_tmr #(.NL(1),.ENABLE(1)) s1(
  .rst_n(rst_n),.fclk_ab_i(ab_mid),.fclk_ab_o(clk_ab_o),
  .fclk_ba_i(clk_ba),.fclk_ba_o(ba_mid),
  .a_i(ab_data),.b_o(b_o),.b_i(b_i),.a_o(ba_data));
endmodule
