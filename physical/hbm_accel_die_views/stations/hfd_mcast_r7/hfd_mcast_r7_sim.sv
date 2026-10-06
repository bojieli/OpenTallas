// bench shim of hfd_mcast_r7 (split inout ports; body identical)
module hfd_mcast_r7_sim (
    input wire [2067:0] a,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
  wire [511:0] m_u_meso1;
  ot_hbm_stn_meso #(.W(512)) u_meso1 (.fclk_i(a[2063]), .d_i(a[511:0]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso1));
  assign t0[511:0] = m_u_meso1;
  assign t1[511:0] = m_u_meso1;
  wire [511:0] m_u_meso2;
  ot_hbm_stn_meso #(.W(512)) u_meso2 (.fclk_i(a[2064]), .d_i(a[1023:512]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso2));
  assign t0[1023:512] = m_u_meso2;
  assign t1[1023:512] = m_u_meso2;
  wire [511:0] m_u_meso3;
  ot_hbm_stn_meso #(.W(512)) u_meso3 (.fclk_i(a[2065]), .d_i(a[1535:1024]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso3));
  assign t0[1535:1024] = m_u_meso3;
  assign t1[1535:1024] = m_u_meso3;
  wire [511:0] m_u_meso4;
  ot_hbm_stn_meso #(.W(512)) u_meso4 (.fclk_i(a[2066]), .d_i(a[2047:1536]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso4));
  assign t0[2047:1536] = m_u_meso4;
  assign t1[2047:1536] = m_u_meso4;
  wire [14:0] m_u_meso5;
  ot_hbm_stn_meso #(.W(15)) u_meso5 (.fclk_i(a[2067]), .d_i(a[2062:2048]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso5));
  assign t0[2062:2048] = m_u_meso5;
  assign t1[2062:2048] = m_u_meso5;
endmodule
