module gold_top (input wire clk, rst_n, input wire [1:0] sr_v, input wire [29:0] sr_addr, output wire [511:0] sr_d, output wire [1:0] sr_rv,
  input wire [15:0] lw, input wire [383:0] lwa, input wire [511:0] lwd, output wire flt);
  ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(16),.MACRO(1),.MUT_XBAR(0),.NS(2)) u_g (
    .clk(clk), .rst_n(rst_n), .rq(16'd0), .rr(16'd0), .ra(384'd0), .rd(), .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sr_d), .sr_rv(sr_rv),
    .sw_v(2'd0), .sw_addr(30'd0), .sw_mask(16'd0), .sw_d(512'd0), .lw(lw), .lwa(lwa), .lwd(lwd), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
module gate_top (input wire clk, rst_n, input wire [1:0] sr_v, input wire [29:0] sr_addr, output wire [511:0] sr_d, output wire [1:0] sr_rv,
  input wire [15:0] lw, input wire [383:0] lwa, input wire [511:0] lwd, output wire flt);
  ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(16),.MACRO(1),.MUT_XBAR(0),.NS(2)) u_g (
    .clk(clk), .rst_n(rst_n), .rq(16'd0), .rr(16'd0), .ra(384'd0), .rd(), .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sr_d), .sr_rv(sr_rv),
    .sw_v(2'd0), .sw_addr(30'd0), .sw_mask(16'd0), .sw_d(512'd0), .lw(lw), .lwa(lwa), .lwd(lwd), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
