// bench shim of hfd_stn_r29 (split inout ports; body identical)
module hfd_stn_r29_sim (
    input wire [975:0] a_i,
    output wire [975:0] a_o,
    input wire [975:0] b_i,
    output wire [975:0] b_o,
    input wire [0:0] rst
);
  wire [975:0] a;
  assign a[486:0] = a_i[486:0];
  assign a[974:974] = a_i[974:974];
  assign a_o = a;
  wire [975:0] b;
  assign b[973:487] = b_i[973:487];
  assign b[975:975] = b_i[975:975];
  assign b_o = b;
  ot_hbm_stn_fwd #(.W(487)) u_fwd1 (.fclk_i(a[974]), .d_i(a[486:0]), .fclk_o(b[974]), .d_o(b[486:0]));
  ot_hbm_stn_fwd #(.W(487)) u_fwd2 (.fclk_i(b[975]), .d_i(b[973:487]), .fclk_o(a[975]), .d_o(a[973:487]));
endmodule
