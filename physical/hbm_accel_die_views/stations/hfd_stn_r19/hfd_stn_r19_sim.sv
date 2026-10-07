// bench shim of hfd_stn_r19 (split inout ports; body identical)
module hfd_stn_r19_sim (
    input wire [1040:0] a,
    output wire [1040:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[1038]), .d_i(a[511:0]), .fclk_o(b[1038]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd2 (.fclk_i(a[1039]), .d_i(a[1023:512]), .fclk_o(b[1039]), .d_o(b[1023:512]));
  ot_hbm_stn_fwd #(.W(14)) u_fwd3 (.fclk_i(a[1040]), .d_i(a[1037:1024]), .fclk_o(b[1040]), .d_o(b[1037:1024]));
endmodule
