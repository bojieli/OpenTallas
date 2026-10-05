`timescale 1ns/1ps
// ot_v41_rom_elem_q_pg_sp_w10: ot_v41_rom_elem_q_pg_w10 with the gated stage clock spine (SPINE = 1 by default here: this
// top exists only to harden and measure the spine-gated domain; aon_clk is the always-on island's clock branch).
// Derived from ot_v41_rom_elem_q_pg_w10: the hardened FP8/FP4 pair element (the S81 element core: ot_v41_rom_elem_w10 BF16 = 0,
// NB = 2 as in ot_v41_rom_elem_q_w10) inside the power-gated wrapper ot_v41_rom_elem_pg_w10 (PG = 1 by default here:
// this top exists only to harden and measure the gated domain plus its always-on side).  BF16 x ports tied off as in
// ot_v41_rom_elem_q_w10.
module ot_v41_rom_elem_q_pg_sp_w10 #(
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer PG = 1,
    parameter integer NSUB = 4,
    parameter integer TW = 24,
    parameter integer DOM_CG = 0,
    parameter integer SPINE = 1,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         aon_clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
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
    ot_v41_rom_elem_pg_sp_w10 #(.BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .PG(PG), .NSUB(NSUB),
        .TW(TW), .DOM_CG(DOM_CG), .SPINE(SPINE), .INSTANCE(INSTANCE)) u_pg (
        .clk(clk), .aon_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_bf(1'b0),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
        .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(3'd0), .xb_v(1'b0), .xb_b(3'd0), .xb_sv(4'd0), .xb_u(32'd0),
        .xb_d(1024'd0), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos),
        .busy(busy), .fault(fault), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .pg_lead(pg_lead),
        .pg_bet(pg_bet), .pg_idle(pg_idle), .pg_step(pg_step), .pg_rst(pg_rst), .pg_ack_to(pg_ack_to),
        .sw_en(sw_en), .sw_ack(sw_ack), .pg_ready(pg_ready), .pg_late(pg_late), .pg_fault(pg_fault));
endmodule
