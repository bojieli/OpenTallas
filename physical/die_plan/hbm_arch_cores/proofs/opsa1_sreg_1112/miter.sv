// HBM-CORES-B 11-12 OPSA1 SREG: EQ_CYCLE_SHIFTED miter on a reduced ot_hgi_su_lgroup2_lf (N=16, M=16, NS=2, RB=1; N=8 is degenerate: off < LN'(8) truncates to 0,
// behavioural banks, BREG=1, FREG=1 as in opsa).  ref = SREG 0 core fed every input one edge late (registered);
// dut = SREG 1 core (MUT selects the negative controls).  Every output must match on every edge.
module miter #(parameter integer MUT = 0) (input wire clk,
  input wire [15:0] rq, rr, input wire [16*5-1:0] ra, input wire [1:0] sr_v, input wire [2*5-1:0] sr_addr,
  input wire [1:0] sw_v, input wire [2*5-1:0] sw_addr, input wire [2*8-1:0] sw_mask, input wire [2*256-1:0] sw_d);
  localparam integer N = 16, NS = 2, LWB = 5, AW = 5;
  reg [15:0] q_rq, q_rr; reg [N*AW-1:0] q_ra; reg [1:0] q_srv, q_swv; reg [NS*LWB-1:0] q_sra, q_swa; reg [NS*8-1:0] q_swm; reg [NS*256-1:0] q_swd;
  always @(posedge clk) begin q_rq <= rq; q_rr <= rr; q_ra <= ra; q_srv <= sr_v; q_sra <= sr_addr; q_swv <= sw_v; q_swa <= sw_addr; q_swm <= sw_mask; q_swd <= sw_d; end
  wire [N*32-1:0] rd_r, rd_d; wire [NS*256-1:0] sd_r, sd_d; wire [NS-1:0] rv_r, rv_d; wire f_r, f_d;
  ot_hgi_su_lgroup2_lf #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(0),.MACRO(0),.NS(NS),.BREG(1),.FREG(1),.SREG(0)) u_ref (
    .clk(clk), .rst_n(1'b1), .rq(q_rq), .rr(q_rr), .ra(q_ra), .rd(rd_r), .sr_v(q_srv), .sr_addr(q_sra), .sr_d(sd_r), .sr_rv(rv_r),
    .sw_v(q_swv), .sw_addr(q_swa), .sw_mask(q_swm), .sw_d(q_swd), .lw(1'b0), .lwa(5'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(5'd0), .s1_d(32'd0), .flt(f_r));
  ot_hgi_su_lgroup2_lf #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(0),.MACRO(0),.NS(NS),.BREG(1),.FREG(1),.SREG(1),.SREG_MUT(MUT)) u_dut (
    .clk(clk), .rst_n(1'b1), .rq(rq), .rr(rr), .ra(ra), .rd(rd_d), .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sd_d), .sr_rv(rv_d),
    .sw_v(sw_v), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_d(sw_d), .lw(1'b0), .lwa(5'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(5'd0), .s1_d(32'd0), .flt(f_d));
  always @* begin assert(rd_r == rd_d); assert(sd_r == sd_d); assert(rv_r == rv_d); assert(f_r == f_d); end
endmodule
