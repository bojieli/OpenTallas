// bench shim of hfd_stn_r0 (split inout ports; body identical)
module hfd_stn_r0_sim (
    input wire [1101:0] a,
    output wire [1101:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[1099]), .d_i({a[511:2], a[0], a[1]}), .fclk_o(b[1099]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd2 (.fclk_i(a[1100]), .d_i(a[1023:512]), .fclk_o(b[1100]), .d_o(b[1023:512]));
  ot_hbm_stn_fwd #(.W(75)) u_fwd3 (.fclk_i(a[1101]), .d_i(a[1098:1024]), .fclk_o(b[1101]), .d_o(b[1098:1024]));
endmodule
