`timescale 1ns/1ps
`default_nettype none
// H-HARDEN 2026-10-16 (H-DIE option A, lead request): the DMA dispatcher collar folded into its only consumer.
// ot_static_cmd_target MODE 1 (SEQ), CW 308 = {mv_wb_epoch16, mv_wb_bank, mv227, drain_rel32, issue_rel32}, RELF 2,
// TGT_PIN 1 (identity strap tgt[7:0] = 104+QID, a die constant) becomes pin-registered soft logic of hb_dbk_<q>; the
// hb_dbk face takes the F20 host bus (cfg/desc/launch) directly instead of the 308-bit command + 32-bit cycle from a
// separate collar.  Wiring is exactly the die composition it replaces (die.v cp_dma_<q> -> hb_dbk_<q>): cmd slices,
// collar `cycle` = the DMA's absolute compiler clock, tgt_active = busy, tgt_fault = mv_fault; same clock (clk root)
// and reset.  No added cycle, no ready/credit: the collar fires its compiled calendar exactly as before.
module ot_hgi_dma_back_static_vp4_banks_cp #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,     // DMA bench mutants pass through (simulation only)
    parameter integer CP_MUT=0   // 1: wrong command slice (bench negative control)
)(
    input wire clk,rst_n,
    input wire [1:0] stk,
    input wire [7:0] tgt,
    input wire [7:0] clk_bank,
    // F20 host bus (ot_hbm_host_static_ingress broadcast)
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire cp_configured,cp_fault,cp_active,
    output wire mv_src,mv_done,mv_fault,
    output wire quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output wire [15:0] wb_reserve_epoch,wb_fill_epoch,
    output wire [11:0] wb_reserve_sectors,
    output wire [31:0] wb_reserve_base,
    output wire wb_fill_start,
    input wire wb_ready,
    output wire [8*289-1:0] wd,
    input wire [11:0] wa
);
    wire cmd_v; wire [307:0] cmd; wire [31:0] cycle;
    ot_static_cmd_target #(.MODE(1),.CW(308),.RELF(2),.NA(1),.NF(1),.TGT_PIN(1)) u_cp(
        .clk(clk),.rst_n(rst_n),.tgt(tgt),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .tgt_active(busy),.tgt_fault(mv_fault),
        .a_we(),.a_addr(),.a_data(),.b_we(),.b_addr(),.b_data(),.run_v(),.run_base(),.run_count(),   // MODE 1: no windows/run
        .cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(cp_configured),.fault(cp_fault),.active(cp_active));
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_banks u_dbk(
`else
    ot_hgi_dma_back_static_vp4_banks #(.STACK_BYTES(STACK_BYTES),.MUT(MUT)) u_dbk(
`endif
        .clk(clk),.rst_n(rst_n),.stk(stk),.clk_bank(clk_bank),.cycle(cycle),
        .mv_v(cmd_v),.mv((CP_MUT==1)?cmd[291:65]:cmd[290:64]),.issue_at(cmd[31:0]),.drain_at(cmd[63:32]),
        .mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),
        .mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),.quiet(quiet),.busy(busy),.rq(rq),.rr(rr),
        .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),
        .wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),
        .wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
endmodule
`default_nettype wire
