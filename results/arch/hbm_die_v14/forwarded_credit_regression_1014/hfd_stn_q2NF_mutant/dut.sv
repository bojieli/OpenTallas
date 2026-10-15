// hfd_stn_q2NF: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_stn_q2NF (
    input wire [1:0] a,
    output wire [1:0] b,
    input wire [0:0] rst
);
  ot_hbm_stn_fwd #(.W(1)) u_fwd1 (.fclk_i(a[1]), .d_i(~a[0]), .fclk_o(b[1]), .d_o(b[0]));
endmodule
