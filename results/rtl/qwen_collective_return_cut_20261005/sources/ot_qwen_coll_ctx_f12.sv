`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_coll_ctx_f12: physical CONTEXT of the Qwen HBM-accel collective endpoint (route vehicle, 2026-10-04).
// The die's TP sequencer (ot_qwen_tp_seq_w12_f12, REG_OUT) and its one-shot collective engine
// (ot_rom_oneshot_die_f12) as they connect in ot_qwen_hbmacc_rt_die_w12 + the HA8 'coll' model: the
// c_* / r_* handshake between them is internal, so its paths are timed in context.  The remaining ports are
// the sequencer's core / descriptor-ROM / vector-memory ports and the engine's link ports (tx record,
// per-destination ready and credit, per-source receive record and credit).
// ---------------------------------------------------------------------------
module ot_qwen_coll_ctx_f12 #(
    parameter integer N         = 2,
    parameter integer RANK      = 0,
    parameter integer DEPTH     = 16,
    parameter integer FIFO_IMPL = 1,
    parameter integer ADD_IMPL  = 1,
    parameter integer REG_OUT   = 1,
    parameter integer NW        = 18,
    parameter integer PAW       = 12,
    parameter integer VWA       = 8,
    parameter integer DAW       = 6,
    parameter integer FW        = 512,
    parameter integer TAGW      = 32,
    parameter integer PW        = FW + 2 + TAGW,
    parameter integer RB        = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output wire              done,
    output wire [NW-1:0]     next_token,
    output wire [31:0]       next_val,
    output wire              fault,
    output wire              coll_busy,
    output wire              core_start,
    output wire [NW-1:0]     core_token,
    output wire [NW-1:0]     core_pos,
    input  wire              core_done,
    input  wire [NW-1:0]     core_next_token,
    input  wire [31:0]       core_next_val,
    input  wire              core_fault,
    output wire [PAW-1:0]    prog_base,
    output wire              desc_re,
    output wire [DAW-1:0]    desc_addr,
    input  wire [63:0]       desc_q,
    output wire              vm_re,
    output wire [VWA-1:0]    vm_raddr,
    input  wire [FW-1:0]     vm_rq,
    output wire              vm_we,
    output wire [VWA-1:0]    vm_waddr,
    output wire [FW-1:0]     vm_wdata,
    // links
    output wire              tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,
    input  wire [N-1:0]      cr_in,
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [N-1:0]      cr_out,
    output wire              c_fault,
    output wire [2:0]        c_fault_code
);
    wire c_valid, c_ready, c_last, c_mode, r_valid, r_last, r_err;
    wire [FW-1:0] c_data, r_data;
    wire [TAGW-1:0] c_tag;
    wire [RB-1:0] r_rank;
    ot_qwen_tp_seq_w12_f12 #(.REG_OUT(REG_OUT), .REG_CDATA(REG_OUT), .N(N), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(DAW), .FW(FW),
        .TAGW(TAGW), .QWEN_FULLSHAPE(1), .ENABLE_AR256(0)) u_seq (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val), .fault(fault), .coll_busy(coll_busy),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos),
        .core_done(core_done), .core_next_token(core_next_token), .core_next_val(core_next_val),
        .core_fault(core_fault), .prog_base(prog_base),
        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
        .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .c_valid(c_valid), .c_ready(c_ready), .c_data(c_data), .c_last(c_last), .c_mode(c_mode), .c_tag(c_tag),
        .r_valid(r_valid), .r_data(r_data), .r_last(r_last), .r_rank(r_rank), .r_err(r_err));
    ot_rom_oneshot_die_f12 #(.N(N), .RANK(RANK), .LANES(FW / 32), .TAGW(TAGW), .DEPTH(DEPTH),
        .FIFO_IMPL(FIFO_IMPL), .ADD_IMPL(ADD_IMPL)) u_coll (
        .clk(clk), .rst_n(rst_n),
        .in_valid(c_valid), .in_ready(c_ready), .in_data(c_data), .in_last(c_last), .in_mode(c_mode), .in_tag(c_tag),
        .tx_valid(tx_valid), .tx_rec(tx_rec), .tx_ready(tx_ready), .cr_in(cr_in),
        .rx_valid(rx_valid), .rx_rec(rx_rec), .cr_out(cr_out),
        .out_valid(r_valid), .out_data(r_data), .out_last(r_last), .out_rank(r_rank), .out_err(r_err),
        .fault(c_fault), .fault_code(c_fault_code));
endmodule
