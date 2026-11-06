module gold_top (input wire clk, rst_n, input wire [15:0] rq, input wire [383:0] ra, output wire [511:0] rd, input wire [7:0] sw_v,
  input wire [119:0] sw_addr, input wire [63:0] sw_mask, input wire [2047:0] sw_d, output wire flt);
  ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8)) u_g (
        .clk(clk), .rst_n(rst_n), .rq(rq), .rr(rq), .ra(ra), .rd(rd),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(sw_v), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_d(sw_d),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
