// hfd_stn_r29: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r29 (
    inout wire [975:0] a,
    inout wire [975:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(487)) u_fwd1 (.fclk_i(a[974]), .d_i({a[486:2], a[0], a[1]}), .fclk_o(b[974]), .d_o(b[486:0]));
  ot_hbm_stn_fwd #(.W(487)) u_fwd2 (.fclk_i(b[975]), .d_i(b[973:487]), .fclk_o(a[975]), .d_o(a[973:487]));
endmodule
