// bench shim of hfd_stn_r22 (split inout ports; body identical)
module hfd_stn_r22_sim (
    input wire [581:0] a,
    output wire [581:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[580]), .d_i(a[511:0]), .fclk_o(b[580]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(68)) u_fwd2 (.fclk_i(a[581]), .d_i(a[579:512]), .fclk_o(b[581]), .d_o(b[579:512]));
endmodule
