// bench shim of hfd_stn_r3 (split inout ports; body identical)
module hfd_stn_r3_sim (
    input wire [44:0] a,
    output wire [44:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(44)) u_fwd1 (.fclk_i(a[44]), .d_i(a[43:0]), .fclk_o(b[44]), .d_o(b[43:0]));
endmodule
