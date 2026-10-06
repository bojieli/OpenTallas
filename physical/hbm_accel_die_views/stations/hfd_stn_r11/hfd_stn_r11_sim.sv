// bench shim of hfd_stn_r11 (split inout ports; body identical)
module hfd_stn_r11_sim (
    input wire [2164:0] a,
    output wire [2164:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[2160]), .d_i(a[511:0]), .fclk_o(b[2160]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd2 (.fclk_i(a[2161]), .d_i(a[1023:512]), .fclk_o(b[2161]), .d_o(b[1023:512]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd3 (.fclk_i(a[2162]), .d_i(a[1535:1024]), .fclk_o(b[2162]), .d_o(b[1535:1024]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd4 (.fclk_i(a[2163]), .d_i(a[2047:1536]), .fclk_o(b[2163]), .d_o(b[2047:1536]));
  ot_hbm_stn_fwd #(.W(112)) u_fwd5 (.fclk_i(a[2164]), .d_i(a[2159:2048]), .fclk_o(b[2164]), .d_o(b[2159:2048]));
endmodule
