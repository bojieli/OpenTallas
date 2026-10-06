// bench shim of hfd_stn_r2 (split inout ports; body identical)
module hfd_stn_r2_sim (
    input wire [43:0] a_i,
    output wire [43:0] a_o,
    output wire [44:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
  wire [43:0] a;
  assign a[42:0] = a_i[42:0];
  assign a_o = a;
  ot_hbm_stn_launch #(.W(44)) u_lau1 (.ck(ck[0]), .d_i({1'b0, a[42], a[41], a[40], a[39], a[38], a[37], a[36], a[35], a[34], a[33], a[32], a[31], a[30], a[29], a[28], a[27], a[26], a[25], a[24], a[23], a[22], a[21], a[20], a[19], a[18], a[17], a[16], a[15], a[14], a[13], a[12], a[11], a[10], a[9], a[8], a[7], a[6], a[5], a[4], a[3], a[2], a[1], a[0]}), .fclk_o(b[44]), .d_o(b[43:0]));
  reg r_one_43; always @(posedge ck[0]) r_one_43 <= rst[0];  // SM req_ready: no ready return
  assign a[43] = r_one_43;
endmodule
