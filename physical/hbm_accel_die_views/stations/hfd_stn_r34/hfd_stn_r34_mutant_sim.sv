// bench shim of hfd_stn_r34 (split inout ports; body identical)
module hfd_stn_r34_sim (
    input wire [512:0] a,
    output wire [512:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[512]), .d_i({a[511:2], a[0], a[1]}), .fclk_o(b[512]), .d_o(b[511:0]));
endmodule
