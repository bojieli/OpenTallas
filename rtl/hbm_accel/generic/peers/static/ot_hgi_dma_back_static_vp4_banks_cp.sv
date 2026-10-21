`timescale 1ns/1ps
`default_nettype none
// H-HARDEN 2026-10-16 (H-DIE option A, lead request): the DMA dispatcher collar folded into its only consumer.
// ot_static_cmd_target MODE 1 (SEQ), CW 308 = {mv_wb_epoch16, mv_wb_bank, mv227, drain_rel32, issue_rel32}, RELF 2,
// TGT_PIN 1 (identity strap tgt[7:0] = 104+QID, a die constant).  The hb_dbk face takes the F20 host bus
// (cfg/desc/launch) directly instead of the 308-bit command + 32-bit cycle from a separate collar.  Wiring is exactly
// the die composition it replaces (die.v cp_dma_<q> -> hb_dbk_<q>): cmd slices, collar `cycle` = the DMA's absolute
// compiler clock, tgt_active = busy, tgt_fault = mv_fault.  No ready, no credit: the collar fires its compiled calendar.
//
// HCDMA-DBK 2026-10-17 structural successor (measured hv15_dbk_cp gate 1f18141cb: clk_cp 1,844 sinks TT 421.6 /
// spread 126.5 with the collar smeared between the 8 banks; rst_n port -> 793 loads unregistered incl. 8 bank macros
// and the controller, in->macro -296.1; in->reg -170.8 u_cp.cmd[26]):
//   * the collar (core + both 128x256 command-table SRAMs) is ONE hard leaf ot_hgi_dma_back_cp_collar
//     (ot_hgi_dma_back_cp_collar.sv) on its own
//     compact clock clk_cp (CTS root inside the leaf; the table SRAMs hang on that leaf tree, so the parent clk_tab
//     entries are gone).  Every leaf pin is flop-first: the core's pin flops / output registers, rst_n -> one pin flop.
//   * reset: rst_n drives only two ot_rst_relay instances on a new parent CTS root clk_rst (a few dozen sinks):
//     u_rst_bk (9 region copies: 8 landing banks + collar) and u_rst_ctl (controller, one extra tree stage).
//     Release edges after the port rises (E = first clk edge with rst_n high), against the folded original:
//        banks        E+3   (was E+0; the bank rst_n is a synchronous gate on its pin-captured enables)
//        collar core  E+4   (was E+0; relay E+3 + leaf pin flop)
//        controller   E+6   (was E+2; relay E+4 + its own two-flop leaf)
//     The collar leaves reset 2 edges before the controller exactly as before (the controller checks that `cycle`
//     advances by one from its own release), so the compiled calendar is launch-relative and unchanged:
//     RESET RELEASE LATENCY +4 EDGES (host programs no earlier than E+4), NO DATAPATH CYCLE ADDED.
//     RST_MUT=1 (bench negative): controller reset straight from the port (released before the collar) -> must FAIL.
// Clocks (all the same die clock, related): clk = controller hard pin, clk_cp = collar leaf hard pin, clk_bank[b] =
// bank b hard pin, clk_rst = parent CTS root of the relay flops only (a parent entry drives exactly one hard child
// pin; a parent CTS root reaches only standard cells).
// ot_hgi_dma_back_static_vp4_banks with per-region reset inputs (same controller + 8 landing banks, same instance
// names u_control / L[b].u_bank, same wiring); only the reset nets differ.
module ot_hgi_dma_back_static_vp4_banks_rs #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,
    parameter integer RR_RT=7
)(
    input wire clk,
    input wire rst_ctl_n,
    input wire [7:0] rst_bank_n,
    input wire [1:0] stk,
    input wire [7:0] clk_bank,
    input wire [31:0] cycle,
    input wire mv_v,
    input wire [226:0] mv,
    input wire [31:0] issue_at,drain_at,
    input wire mv_wb_bank,
    input wire [15:0] mv_wb_epoch,
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
    wire [7:0] rr_valid_i,bank_read_en,bank_output_en;
    wire [6:0] rslot_s,rslot_w,rslot_n,wslot_s,wslot_w,wslot_n;   // per bank-group copies (S 0-2, W 3-4, N 5-7)
    wire [255:0] bank_read_addr;
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_controller u_control(
`else
    ot_hgi_dma_back_static_vp4_controller #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT)) u_control(
`endif
        .clk(clk),.rst_n(rst_ctl_n),.stk(stk),.cycle_in(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
        .mv_wb_bank(mv_wb_bank),.mv_wb_epoch(mv_wb_epoch),.mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),
        .quiet(quiet),.busy(busy),.rq(rq),.wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),
        .wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),
        .wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),
        .wb_ready(wb_ready),.wa(wa),.rr_valid_i(rr_valid_i),.bank_read_en(bank_read_en),
        .bank_read_slot_s(rslot_s),.bank_read_slot_w(rslot_w),.bank_read_slot_n(rslot_n),
        .bank_write_slot_s(wslot_s),.bank_write_slot_w(wslot_w),.bank_write_slot_n(wslot_n),.bank_output_en(bank_output_en),
        .bank_read_addr_s(bank_read_addr[95:0]),.bank_read_addr_w(bank_read_addr[159:96]),.bank_read_addr_n(bank_read_addr[255:160]));
    for(genvar b=0;b<8;b=b+1)begin:L
        assign rr_valid_i[b]=rr[b*257+256];
        ot_hgi_dma_back_landing_bank u_bank(
            .clk(clk_bank[b]),.rst_n(rst_bank_n[b]),
            .read_en(bank_read_en[b]),.read_slot(b<3?rslot_s:b<5?rslot_w:rslot_n),
            .write_en(rr_valid_i[b]),.write_slot(b<3?wslot_s:b<5?wslot_w:wslot_n),.rr_data(rr[b*257+:256]),
            .read_addr(bank_read_addr[b*32+:32]),.output_en(bank_output_en[b]),.wd(wd[b*289+:289]));
    end
endmodule

module ot_hgi_dma_back_static_vp4_banks_cp #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,     // DMA bench mutants pass through (simulation only)
    parameter integer CP_MUT=0,  // 1: wrong command slice (bench negative control)
    parameter integer RST_MUT=0, // 1: controller reset straight from the port (bench negative control)
    // HBM-BANKLAT-DMA 10-19: VM read round trip at the controller pins (rq launch -> rr launch, edges, all 8 banks;
    // the die pads the short rq lanes). Default 7 = closed behaviour; d4g budget 80. Under OT_DBK_HARD the controller
    // is the hard view kitted with this value (its PARAMS), so the parent takes no override there.
    parameter integer RR_RT=7
)(
    input wire clk,rst_n,
    input wire clk_cp,              // collar leaf clock pin (related, same die clock as clk)
    input wire clk_rst,             // parent reset-relay CTS root (related, same die clock as clk)
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
    // ---- regional reset (relay flops on clk_rst; the port loads only the two relays)
    wire [8:0] rst_bk_n; wire [0:0] rst_ctl_q;
    ot_rst_relay #(.REGIONS(9),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_bk(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_bk_n));
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(2)) u_rst_ctl(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_ctl_q));
    wire rst_ctl_n = (RST_MUT==1) ? rst_n : rst_ctl_q[0];
    // ---- collar leaf
    wire cmd_v; wire [307:0] cmd; wire [31:0] cycle;
    ot_hgi_dma_back_cp_collar u_cp(
        .clk(clk_cp),.rst_n(rst_bk_n[8]),.tgt(tgt),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .tgt_active(busy),.tgt_fault(mv_fault),
        .cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(cp_configured),.fault(cp_fault),.active(cp_active));
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_banks_rs u_dbk(
`else
    ot_hgi_dma_back_static_vp4_banks_rs #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT)) u_dbk(
`endif
        .clk(clk),.rst_ctl_n(rst_ctl_n),.rst_bank_n(rst_bk_n[7:0]),.stk(stk),.clk_bank(clk_bank),.cycle(cycle),
        .mv_v(cmd_v),.mv((CP_MUT==1)?cmd[291:65]:cmd[290:64]),.issue_at(cmd[31:0]),.drain_at(cmd[63:32]),
        .mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),
        .mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),.quiet(quiet),.busy(busy),.rq(rq),.rr(rr),
        .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),
        .wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),
        .wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
endmodule
`default_nettype wire
