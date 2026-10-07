// hfd_stn_r36: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r36 (
    input wire [512:0] a,
    output wire [512:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[512]), .d_i(a[511:0]), .fclk_o(b[512]), .d_o(b[511:0]));
endmodule
