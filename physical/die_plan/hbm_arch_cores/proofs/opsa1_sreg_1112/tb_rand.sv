// HBM-CORES-B 11-12 OPSA1 SREG random lock-step bench (complements the BMC miter): same pairing as miter.sv
// (ref = SREG 0 on inputs delayed one edge, dut = SREG 1 / SREG_MUT); counts output mismatches per edge.
module tb_rand #(parameter integer MUT = 0, parameter integer CYC = 200000, parameter integer SEED = 1);
  localparam integer N = 16, NS = 2, LWB = 5, AW = 5;
  reg clk = 0;
  reg [15:0] rq, rr; reg [N*AW-1:0] ra; reg [1:0] sr_v, sw_v; reg [NS*LWB-1:0] sr_addr, sw_addr; reg [NS*8-1:0] sw_mask; reg [NS*256-1:0] sw_d;
  reg [15:0] q_rq, q_rr; reg [N*AW-1:0] q_ra; reg [1:0] q_srv, q_swv; reg [NS*LWB-1:0] q_sra, q_swa; reg [NS*8-1:0] q_swm; reg [NS*256-1:0] q_swd;
  always @(posedge clk) begin q_rq <= rq; q_rr <= rr; q_ra <= ra; q_srv <= sr_v; q_sra <= sr_addr; q_swv <= sw_v; q_swa <= sw_addr; q_swm <= sw_mask; q_swd <= sw_d; end
  wire [N*32-1:0] rd_r, rd_d; wire [NS*256-1:0] sd_r, sd_d; wire [NS-1:0] rv_r, rv_d; wire f_r, f_d;
  ot_hgi_su_lgroup2_lf #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(0),.MACRO(0),.NS(NS),.BREG(1),.FREG(1),.SREG(0)) u_ref (
    .clk(clk), .rst_n(1'b1), .rq(q_rq), .rr(q_rr), .ra(q_ra), .rd(rd_r), .sr_v(q_srv), .sr_addr(q_sra), .sr_d(sd_r), .sr_rv(rv_r),
    .sw_v(q_swv), .sw_addr(q_swa), .sw_mask(q_swm), .sw_d(q_swd), .lw(1'b0), .lwa(5'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(5'd0), .s1_d(32'd0), .flt(f_r));
  ot_hgi_su_lgroup2_lf #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(0),.MACRO(0),.NS(NS),.BREG(1),.FREG(1),.SREG(1),.SREG_MUT(MUT)) u_dut (
    .clk(clk), .rst_n(1'b1), .rq(rq), .rr(rr), .ra(ra), .rd(rd_d), .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sd_d), .sr_rv(rv_d),
    .sw_v(sw_v), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_d(sw_d), .lw(1'b0), .lwa(5'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(5'd0), .s1_d(32'd0), .flt(f_d));
  integer c, i, bad_rd, bad_sd, bad_rv, bad_f, first, x;
  initial begin
    x = $urandom(SEED); bad_rd = 0; bad_sd = 0; bad_rv = 0; bad_f = 0; first = -1;
    rq = 0; rr = 0; ra = 0; sr_v = 0; sw_v = 0; sr_addr = 0; sw_addr = 0; sw_mask = 0; sw_d = 0;
    for (c = 0; c < CYC; c = c + 1) begin
      #1 clk = 1; #1 clk = 0;
      // compare after the edge settles (outputs of edge c), skip the first 2 edges (delay regs uninitialised)
      if (c > 2) begin
        if (rd_r !== rd_d) bad_rd = bad_rd + 1; if (sd_r !== sd_d) bad_sd = bad_sd + 1;
        if (rv_r !== rv_d) bad_rv = bad_rv + 1; if (f_r !== f_d) bad_f = bad_f + 1;
        if (first < 0 && (rd_r !== rd_d || sd_r !== sd_d || rv_r !== rv_d || f_r !== f_d)) first = c;
      end
      rr = $urandom; rq = rr | ($urandom & $urandom); for (i = 0; i < N; i = i + 1) ra[i*AW +: AW] = $urandom;
      sr_v = (($urandom % 4) == 0) ? $urandom : 2'd0; sr_addr = $urandom;
      sw_v = $urandom; sw_addr = $urandom; sw_mask = $urandom; for (i = 0; i < NS*8; i = i + 1) sw_d[32*i +: 32] = $urandom;
    end
    $display("SREG_RAND MUT=%0d SEED=%0d cycles %0d mismatches rd %0d sr_d %0d sr_rv %0d flt %0d first_edge %0d", MUT, SEED, CYC, bad_rd, bad_sd, bad_rv, bad_f, first);
    $finish;
  end
endmodule
