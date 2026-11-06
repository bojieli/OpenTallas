// Distinct source capability: bank-local read capture; read response +1, write/fault unchanged.
// HBM-FORM-SPLIT d44v part 27: opstore_b -> 2 x operand group tile + output group tile. Members and parameters verbatim
// from ot_hgi_sfu_split3_opstore_b_core (ot_hgi_sfu_static_operand_store g_operand[2,3].u_group, u_output). Each tile
// carries its own kit face shell, +1 in and +1 out, the same as the uncut core's shell, so every plan pin keeps its date.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_sfu_opsb_group_rreg_1106__fcore (
    input  wire          clk, rst_n,
    input  wire [15:0]   rq,
    input  wire [383:0]  ra,
    output wire [511:0]  rd,
    input  wire [7:0]    sw_v,
    input  wire [119:0]  sw_addr,
    input  wire [63:0]   sw_mask,
    input  wire [2047:0] sw_d,
    output wire          flt
);
    // HBM-REFORM-B10 IREG: every input registered once more (no reset) before the lgroup2 selects; with BREG / FREG
    // rd is +2 edges and flt +2 edges (COORD 15:16 pre-approved form).
    reg [15:0] q_rq; reg [383:0] q_ra; reg [7:0] q_sv; reg [119:0] q_sa; reg [63:0] q_sm; reg [2047:0] q_sd;
    always @(posedge clk) begin q_rq <= rq; q_ra <= ra; q_sv <= sw_v; q_sa <= sw_addr; q_sm <= sw_mask; q_sd <= sw_d; end
    ot_hgi_su_lgroup2_local_1106 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8),.BREG(1),.FREG(1),.RREG(1)) u_g (  // B9 rd +1, B10 rd +2
        .clk(clk), .rst_n(rst_n), .rq(q_rq), .rr(q_rq), .ra(q_ra), .rd(rd),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(q_sv), .sw_addr(q_sa), .sw_mask(q_sm), .sw_d(q_sd),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
`default_nettype wire
