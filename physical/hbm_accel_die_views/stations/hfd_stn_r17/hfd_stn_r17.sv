// hfd_stn_r17: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r17 (
    input wire [128:0] a,
    output wire [128:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(128)) u_fwd1 (.fclk_i(a[128]), .d_i(a[127:0]), .fclk_o(b[128]), .d_o(b[127:0]));
endmodule
