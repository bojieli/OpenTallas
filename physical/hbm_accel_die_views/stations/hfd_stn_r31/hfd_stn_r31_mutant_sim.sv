// bench shim of hfd_stn_r31 (split inout ports; body identical)
module hfd_stn_r31_sim (
    input wire [513:0] a_i,
    output wire [513:0] a_o,
    input wire [513:0] b_i,
    output wire [513:0] b_o,
    input wire [0:0] rst
);
  wire [513:0] a;
  assign a[255:0] = a_i[255:0];
  assign a[512:512] = a_i[512:512];
  assign a_o = a;
  wire [513:0] b;
  assign b[511:256] = b_i[511:256];
  assign b[513:513] = b_i[513:513];
  assign b_o = b;
  ot_hbm_stn_fwd #(.W(256)) u_fwd1 (.fclk_i(a[512]), .d_i({a[255:2], a[0], a[1]}), .fclk_o(b[512]), .d_o(b[255:0]));
  ot_hbm_stn_fwd #(.W(256)) u_fwd2 (.fclk_i(b[513]), .d_i(b[511:256]), .fclk_o(a[513]), .d_o(a[511:256]));
endmodule
