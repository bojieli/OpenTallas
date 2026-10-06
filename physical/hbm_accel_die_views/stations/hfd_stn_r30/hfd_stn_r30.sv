// hfd_stn_r30: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r30 (
    inout wire [513:0] a,
    inout wire [513:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(256)) u_fwd1 (.fclk_i(a[512]), .d_i(a[255:0]), .fclk_o(b[512]), .d_o(b[255:0]));
  ot_hbm_stn_fwd #(.W(256)) u_fwd2 (.fclk_i(b[513]), .d_i(b[511:256]), .fclk_o(a[513]), .d_o(a[511:256]));
endmodule
