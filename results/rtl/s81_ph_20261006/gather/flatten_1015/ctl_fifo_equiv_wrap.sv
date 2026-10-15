module gold (input wire wclk, wrst_n, w_v, input wire [158:0] w_d, output wire w_rdy, input wire rclk, rrst_n, r_rdy,
           output wire r_v, output wire [158:0] r_d, output wire w_live, r_live);
  ot_ratio_cdc_fifo_old #(.W(159), .DEPTH(4)) u (.wclk(wclk), .wrst_n(wrst_n), .w_v(w_v), .w_rdy(w_rdy), .w_d(w_d), .rclk(rclk), .rrst_n(rrst_n),
      .r_v(r_v), .r_rdy(r_rdy), .r_d(r_d), .w_live(w_live), .r_live(r_live));
endmodule
module gate (input wire wclk, wrst_n, w_v, input wire [158:0] w_d, output wire w_rdy, input wire rclk, rrst_n, r_rdy,
           output wire r_v, output wire [158:0] r_d, output wire w_live, r_live);
  ot_ratio_cdc_fifo #(.W(159), .DEPTH(4)) u (.wclk(wclk), .wrst_n(wrst_n), .w_v(w_v), .w_rdy(w_rdy), .w_d(w_d), .rclk(rclk), .rrst_n(rrst_n),
      .r_v(r_v), .r_rdy(r_rdy), .r_d(r_d), .w_live(w_live), .r_live(r_live));
endmodule
