// hfd_stn_r4: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r4 (
    input wire [2067:0] a,
    output wire [2067:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[2063]), .d_i({a[511:2], a[0], a[1]}), .fclk_o(b[2063]), .d_o(b[511:0]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd2 (.fclk_i(a[2064]), .d_i(a[1023:512]), .fclk_o(b[2064]), .d_o(b[1023:512]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd3 (.fclk_i(a[2065]), .d_i(a[1535:1024]), .fclk_o(b[2065]), .d_o(b[1535:1024]));
  ot_hbm_stn_fwd #(.W(512)) u_fwd4 (.fclk_i(a[2066]), .d_i(a[2047:1536]), .fclk_o(b[2066]), .d_o(b[2047:1536]));
  ot_hbm_stn_fwd #(.W(15)) u_fwd5 (.fclk_i(a[2067]), .d_i(a[2062:2048]), .fclk_o(b[2067]), .d_o(b[2062:2048]));
endmodule
