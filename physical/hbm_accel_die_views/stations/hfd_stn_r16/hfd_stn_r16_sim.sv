// bench shim of hfd_stn_r16 (split inout ports; body identical)
module hfd_stn_r16_sim (
    input wire [128:0] a,
    output wire [128:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(128)) u_fwd1 (.fclk_i(a[128]), .d_i(a[127:0]), .fclk_o(b[128]), .d_o(b[127:0]));
endmodule
