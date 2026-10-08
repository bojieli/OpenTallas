// hfd_stn_r20: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r20 (
    input wire [1025:0] a,
    output wire [1025:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[1024]), .d_i(a[511:0]), .fclk_o(b[1024]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd2 (.fclk_i(a[1025]), .d_i(a[1023:512]), .fclk_o(b[1025]), .d_o(b[1023:512]));
endmodule
