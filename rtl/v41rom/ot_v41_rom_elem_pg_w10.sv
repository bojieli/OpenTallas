`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_elem_pg_w10 -- the V4.1 ROM-array element (ot_v41_rom_elem_w10) as a power-gated domain.
//
// PG = 0 (default): the element, unchanged; every PG port is ignored and pg_ready = 1.
// PG = 1: the element sits behind a header switch ring; its always-on side (scheduler + W18 power controller,
// output isolation clamps, configuration retention shadow and replay, domain clock gate) is ot_v41_rom_pg_ao.
// ---------------------------------------------------------------------------
module ot_v41_rom_elem_pg_w10 #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,
    parameter integer NCHB = 8,
    parameter integer NB = 1,
    parameter integer MTP = 0,
    parameter integer EARLY = 0,
    parameter integer CG = 1,
    parameter integer DRAIN = 127,
    parameter integer FAST = 0,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer PP = 0,
    parameter integer FRONT_PAR = 0,
    parameter integer BP = 0,
    parameter INSTANCE = "",
    parameter integer PG = 0,          // 1: power-gated domain (opt-in)
    parameter integer NSUB = 4,        // header-ring segments of this element's domain
    parameter integer TW = 24,
    parameter integer DOM_CG = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
    // power gating (PG = 1)
    input  wire         pg_en,
    input  wire         sched_v,
    input  wire [TW-1:0] sched_gap,
    input  wire [TW-1:0] pg_lead,
    input  wire [TW-1:0] pg_bet,
    input  wire [7:0]   pg_idle,
    input  wire [15:0]  pg_step,
    input  wire [7:0]   pg_rst,
    input  wire [15:0]  pg_ack_to,
    output wire [NSUB-1:0] sw_en,
    input  wire [NSUB-1:0] sw_ack,
    output wire         pg_ready,
    output wire         pg_late,
    output wire         pg_fault
);
    // element-side nets
    wire         e_clk, e_rst_n, e_cfg_v, e_go;
    wire [4:0]   e_cfg_a;
    wire [47:0]  e_cfg_d;
    wire [NB-1:0]    e_pv, e_perr;
    wire [32*NB-1:0] e_pval;
    wire [16*NB-1:0] e_prow;
    wire [5*NB-1:0]  e_pseg, e_pnseg;
    wire [3*NB-1:0]  e_ppos;
    wire e_busy, e_fault;

    ot_v41_rom_elem_w10 #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NCHB(NCHB), .NB(NB), .MTP(MTP),
        .EARLY(EARLY), .CG(CG), .DRAIN(DRAIN), .FAST(FAST), .CUT(CUT), .PP(PP), .FRONT_PAR(FRONT_PAR), .BP(BP),
        .INSTANCE(INSTANCE)) u_elem (
        .clk(e_clk), .rst_n(e_rst_n), .cfg_v(e_cfg_v), .cfg_a(e_cfg_a), .cfg_d(e_cfg_d), .go(e_go), .go_bf(go_bf),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
        .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u),
        .xb_d(xb_d), .pv(e_pv), .pval(e_pval), .prow(e_prow), .pseg(e_pseg), .pnseg(e_pnseg), .perr(e_perr),
        .ppos(e_ppos), .busy(e_busy), .fault(e_fault));

    if (PG == 0) begin : g_off
        assign e_clk = clk; assign e_rst_n = rst_n; assign e_cfg_v = cfg_v; assign e_cfg_a = cfg_a;
        assign e_cfg_d = cfg_d; assign e_go = go;
        assign pv = e_pv; assign pval = e_pval; assign prow = e_prow; assign pseg = e_pseg; assign pnseg = e_pnseg;
        assign perr = e_perr; assign ppos = e_ppos; assign busy = e_busy; assign fault = e_fault;
        assign sw_en = {NSUB{1'b1}}; assign pg_ready = 1'b1; assign pg_late = 1'b0; assign pg_fault = 1'b0;
    end else begin : g_pg
        // the always-on side is one module (ot_v41_rom_pg_ao) so it can be hardened and measured on its own
        ot_v41_rom_pg_ao #(.NSEG(NSEG), .NB(NB), .NSUB(NSUB), .TW(TW), .DOM_CG(DOM_CG)) u_ao (
            .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
            .e_clk(e_clk), .e_rst_n(e_rst_n), .e_cfg_v(e_cfg_v), .e_cfg_a(e_cfg_a), .e_cfg_d(e_cfg_d), .e_go(e_go),
            .e_pv(e_pv), .e_pval(e_pval), .e_prow(e_prow), .e_pseg(e_pseg), .e_pnseg(e_pnseg), .e_perr(e_perr),
            .e_ppos(e_ppos), .e_busy(e_busy), .e_fault(e_fault),
            .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .busy(busy),
            .fault(fault), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .pg_lead(pg_lead), .pg_bet(pg_bet),
            .pg_idle(pg_idle), .pg_step(pg_step), .pg_rst(pg_rst), .pg_ack_to(pg_ack_to), .sw_en(sw_en),
            .sw_ack(sw_ack), .pg_ready(pg_ready), .pg_late(pg_late), .pg_fault(pg_fault));
    end
endmodule
