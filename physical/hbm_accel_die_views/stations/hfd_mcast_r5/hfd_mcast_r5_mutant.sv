// hfd_mcast_r5: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator master, tools/hbm_die_views.py)
module hfd_mcast_r5 (
    input wire [2067:0] a,
    output wire [2067:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
  ot_hbm_stn_fwd #(.W(512)) u_fwd1 (.fclk_i(a[2063]), .d_i({a[511:2], a[0], a[1]}), .fclk_o(b[2063]), .d_o(b[511:0]));
  wire [511:0] m_u_meso2;
  ot_hbm_stn_meso #(.W(512)) u_meso2 (.fclk_i(a[2063]), .d_i(a[511:0]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso2));
  assign t0[511:0] = m_u_meso2;
  assign t1[511:0] = m_u_meso2;
  ot_hbm_stn_fwd #(.W(512)) u_fwd3 (.fclk_i(a[2064]), .d_i(a[1023:512]), .fclk_o(b[2064]), .d_o(b[1023:512]));
  wire [511:0] m_u_meso4;
  ot_hbm_stn_meso #(.W(512)) u_meso4 (.fclk_i(a[2064]), .d_i(a[1023:512]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso4));
  assign t0[1023:512] = m_u_meso4;
  assign t1[1023:512] = m_u_meso4;
  ot_hbm_stn_fwd #(.W(512)) u_fwd5 (.fclk_i(a[2065]), .d_i(a[1535:1024]), .fclk_o(b[2065]), .d_o(b[1535:1024]));
  wire [511:0] m_u_meso6;
  ot_hbm_stn_meso #(.W(512)) u_meso6 (.fclk_i(a[2065]), .d_i(a[1535:1024]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso6));
  assign t0[1535:1024] = m_u_meso6;
  assign t1[1535:1024] = m_u_meso6;
  ot_hbm_stn_fwd #(.W(512)) u_fwd7 (.fclk_i(a[2066]), .d_i(a[2047:1536]), .fclk_o(b[2066]), .d_o(b[2047:1536]));
  wire [511:0] m_u_meso8;
  ot_hbm_stn_meso #(.W(512)) u_meso8 (.fclk_i(a[2066]), .d_i(a[2047:1536]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso8));
  assign t0[2047:1536] = m_u_meso8;
  assign t1[2047:1536] = m_u_meso8;
  ot_hbm_stn_fwd #(.W(15)) u_fwd9 (.fclk_i(a[2067]), .d_i(a[2062:2048]), .fclk_o(b[2067]), .d_o(b[2062:2048]));
  wire [14:0] m_u_meso10;
  ot_hbm_stn_meso #(.W(15)) u_meso10 (.fclk_i(a[2067]), .d_i(a[2062:2048]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso10));
  assign t0[2062:2048] = m_u_meso10;
  assign t1[2062:2048] = m_u_meso10;
endmodule
