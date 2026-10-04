// Source-component runtime adapter only: no alternative arithmetic or engine.
module s81_native_he_bootstrap (
 input wire clk, rst_n,
 input wire he_go, input wire [20:0] he_nout, he_k,
 input wire [29:0] he_wbase, he_xbase, he_obase, he_xps, he_ops,
 input wire [2:0] he_m,
 output wire he_ready, he_idle, he_fault,
 output wire [7:0] he_w_re, output wire [127:0] he_w_addr,
 input wire [2047:0] he_w_data,
 output wire [7:0] he_x_re, output wire [239:0] he_x_addr,
 input wire [255:0] he_x_q,
 output wire he_o_we, output wire [29:0] he_o_addr,
 output wire [31:0] he_o_mask, output wire [1023:0] he_o_data,
 input wire ssx_valid, ssx_last, input wire [8191:0] ssx_x,
 output wire ssx_we, output wire [29:0] ssx_addr,
 output wire [31:0] ssx_data, output wire ssx_busy, ssx_fault
);
 ot_hdc_v41x_he_adapt #(.HW(8), .TL(9), .KCMAX(2560), .PMAX(2),
   .BAW(16), .AW(30), .NW(21), .S(8), .MP(1)) he (
   .clk(clk), .rst_n(rst_n), .go(he_go), .ready(he_ready), .idle(he_idle),
   .i_nout(he_nout), .i_k(he_k), .i_wbase(he_wbase), .i_xbase(he_xbase),
   .i_obase(he_obase), .i_m(he_m), .i_xps(he_xps), .i_ops(he_ops),
   .w_re(he_w_re), .w_addr(he_w_addr), .w_data(he_w_data),
   .x_re(he_x_re), .x_addr(he_x_addr), .x_q(he_x_q),
   .o_we(he_o_we), .o_addr(he_o_addr), .o_mask(he_o_mask),
   .o_data(he_o_data), .fault(he_fault));
 // Same SUN256 chunk8 arithmetic leaf: whole H, 80 vectors. The padded time
 // tree has capacity128 vectors. R-ARITH su split_sum is csum over all H.
 ot_hdc_vreduce #(.SW(256), .LV(7), .AW(30)) ssx (
   .clk(clk), .rst_n(rst_n), .v_in(ssx_valid), .mx_in(1'b0), .sq_in(1'b1),
   .last_in(ssx_last), .addr_in(30'd40960), .x_in(ssx_x),
   .o_we(ssx_we), .o_addr(ssx_addr), .o_data(ssx_data),
   .busy(ssx_busy), .fault(ssx_fault));
endmodule
