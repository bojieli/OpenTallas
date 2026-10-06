// hfd_stn_r3: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_r3 (
    input wire [44:0] a,
    output wire [44:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(44)) u_fwd1 (.fclk_i(a[44]), .d_i({a[43:2], a[0], a[1]}), .fclk_o(b[44]), .d_o(b[43:0]));
endmodule
