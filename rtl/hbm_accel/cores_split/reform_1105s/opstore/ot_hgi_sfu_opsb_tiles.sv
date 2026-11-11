// HBM-FORM-SPLIT d44v part 27: opstore_b -> 2 x operand group tile + output group tile. Members and parameters verbatim
// from ot_hgi_sfu_split3_opstore_b_core (ot_hgi_sfu_static_operand_store g_operand[2,3].u_group, u_output). Each tile
// carries its own kit face shell, +1 in and +1 out, the same as the uncut core's shell, so every plan pin keeps its date.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_sfu_opsb_group (
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
`ifdef OT_OPSG_GP   // DIE-HBM-83-OPSG d44v part 57 opt-in (ot_hgi_su_lgroup2_gp.sv): rd +5 edges, flt unchanged
    ot_hgi_su_lgroup2_gp u_g (.clk(clk), .rst_n(rst_n), .rq(q_rq), .rr(q_rq), .ra(q_ra), .rd(rd),
        .sw_v(q_sv), .sw_addr(q_sa), .sw_mask(q_sm), .sw_d(q_sd), .flt(flt));
`else
    ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8),.BREG(1),.FREG(1)) u_g (  // B9 rd +1, B10 rd +2
        .clk(clk), .rst_n(rst_n), .rq(q_rq), .rr(q_rq), .ra(q_ra), .rd(rd),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(q_sv), .sw_addr(q_sa), .sw_mask(q_sm), .sw_d(q_sd),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
`endif
endmodule
module ot_hgi_sfu_opsb_output (
    input  wire          clk, rst_n,
    input  wire [1:0]    sr_v,
    input  wire [29:0]   sr_addr,
    output wire [511:0]  sr_d,
    output wire [1:0]    sr_rv,
    input  wire [15:0]   lw,
    input  wire [383:0]  lwa,
    input  wire [511:0]  lwd,
    output wire          flt
);
    // HBM-REFORM-B11 (ev74 opsb_output RE-FORM; CTS setup -895 ps / 9042 endpoints: lw face reg -> 16-deep lane-write
    // chain -> SRAM wd_in across the 760 um tile): the group tiles' form. IREG: every input registered once more (no reset,
    // all ops move one edge together, so their order is kept); the log-depth lgroup2_lf (lane-write and sector-read selects
    // one-hot); BREG: bank inputs registered; FREG: fault terms registered. sr_d / sr_rv +2 edges, flt +2 edges.
    reg [1:0] q_sv; reg [29:0] q_sa; reg [15:0] q_lw; reg [383:0] q_la; reg [511:0] q_ld;
    always @(posedge clk) begin q_sv <= sr_v; q_sa <= sr_addr; q_lw <= lw; q_la <= lwa; q_ld <= lwd; end
`ifdef OT_OPSB_WP    // HBM-FORM-SPLIT-14-OPSB opt-in: write-pipelined, placement-local form (ot_hgi_su_lgroup2_wp.sv): sr_d /
                     // sr_rv +(2 + WP) edges, flt +WP edges vs this text without defines
`ifdef OT_OPSB_PRESELECT
`ifdef OT_OPSB_PRESELECT_COL
    ot_hgi_su_lgroup2_wp #(.WP(`OT_OPSB_WP),.PRESELECT(1),.LOCAL_COL(`OT_OPSB_PRESELECT_COL)) u_g (
`else
    ot_hgi_su_lgroup2_wp #(.WP(`OT_OPSB_WP),.PRESELECT(1)) u_g (
`endif
`else
    ot_hgi_su_lgroup2_wp #(.WP(`OT_OPSB_WP)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .sr_v(q_sv), .sr_addr(q_sa), .sr_d(sr_d), .sr_rv(sr_rv),
        .lw(q_lw), .lwa(q_la), .lwd(q_ld), .flt(flt));
`else
`ifdef OT_OPSB_RREG   // HBM-FORM-SPLIT-13-OPSB opt-in: bank-local read registers (RREG 1: sr_d / sr_rv +1 edge, 2: +2)
    ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(16),.MACRO(1),.MUT_XBAR(0),.NS(2),.BREG(1),.FREG(1),.RREG(`OT_OPSB_RREG)) u_g (
`else
    ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(16),.MACRO(1),.MUT_XBAR(0),.NS(2),.BREG(1),.FREG(1)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .rq(16'd0), .rr(16'd0), .ra(384'd0), .rd(),
        .sr_v(q_sv), .sr_addr(q_sa), .sr_d(sr_d), .sr_rv(sr_rv),
        .sw_v(2'd0), .sw_addr(30'd0), .sw_mask(16'd0), .sw_d(512'd0),
        .lw(q_lw), .lwa(q_la), .lwd(q_ld), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
`endif
endmodule
`default_nettype wire
