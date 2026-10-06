// bench shim of hfd_meso_r1 (split inout ports; body identical)
module hfd_meso_r1_sim (
    input wire [1101:0] a,
    output wire [1098:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
  wire [511:0] m_u_meso1;
  ot_hbm_stn_meso #(.W(512)) u_meso1 (.fclk_i(a[1099]), .d_i({a[511:2], a[0], a[1]}), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso1));
  assign b[511:0] = m_u_meso1;
  wire [511:0] m_u_meso2;
  ot_hbm_stn_meso #(.W(512)) u_meso2 (.fclk_i(a[1100]), .d_i(a[1023:512]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso2));
  assign b[1023:512] = m_u_meso2;
  wire [74:0] m_u_meso3;
  ot_hbm_stn_meso #(.W(75)) u_meso3 (.fclk_i(a[1101]), .d_i(a[1098:1024]), .ck(ck[0]), .rst_n(rst[0]), .d_o(m_u_meso3));
  assign b[1098:1024] = m_u_meso3;
endmodule
