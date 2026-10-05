`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// In-context physical wrapper of ot_qwen_tp_seq_async_w12 (W12 TP4 die point:
// G 6144 -> NP = G >> SMIN = 48 ME result ports, MAW 24, N 4, SNW 18, FW 512,
// ENABLE_AR256 1, QWEN_FULLSHAPE 1).  Physical evidence only; no simulation
// or runtime uses it.
//
// Every port of the sequencer faces a REGISTER here, as in the die:
//   * me_we/me_addr/me_mask: the matrix engine's result-write registers
//     (ot_qwen_w12_matvec o_we2/o_addr2/o_mask2), which also drive the VM
//     write port -- the observation tap is a branch of those nets;
//   * vm_rq, desc_q: the synchronous-read data registers of the VM and the
//     descriptor memory; vm_re/vm_raddr/vm_we/..., desc_re/desc_addr: their
//     address/write registers (a synchronous memory samples them at the edge);
//   * c_* / r_*: the one-shot collective unit's registered die port;
//   * core_*: the decode core's start/done handshake registers.
// So with --false-path-io the route times exactly the sequencer's own
// register-to-register paths, including the ME-tap scoreboard (ports ->
// offset compare -> one-hot -> 48-port OR -> lw) and the cut-through read
// gate (lw -> word_ok -> rd_go -> vm_re/vm_raddr), both A/B with ASYNC_COLL.
// ---------------------------------------------------------------------------
module ot_qwen_tp_seq_async_ctx_w12 #(
    parameter integer ASYNC_COLL = 1,
    parameter integer SB_PIPE = 0,         // 1: pipelined cut-through scoreboard set (ot_qwen_tp_seq_async_w12)
    parameter integer ENABLE_AR256 = 1,
    parameter integer NP   = 48,
    parameter integer MAW  = 24,
    parameter integer N    = 4,
    parameter integer NW   = 18,
    parameter integer PAW  = 12,
    parameter integer VWA  = 8,
    parameter integer DAW  = 6,
    parameter integer FW   = 512,
    parameter integer TAGW = 32,
    parameter integer QWEN_FULLSHAPE = 1,
    parameter integer RB   = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg               fault,
    output reg               coll_busy,
    output reg               core_start,
    output reg  [NW-1:0]     core_token,
    output reg  [NW-1:0]     core_pos,
    input  wire              core_done,
    input  wire [NW-1:0]     core_next_token,
    input  wire [31:0]       core_next_val,
    input  wire              core_fault,
    output reg  [PAW-1:0]    prog_base,
    output reg               desc_re,
    output reg  [DAW-1:0]    desc_addr,
    input  wire [63:0]       desc_q,
    output reg               vm_re,
    output reg  [VWA-1:0]    vm_raddr,
    input  wire [FW-1:0]     vm_rq,
    output reg               vm_we,
    output reg  [VWA-1:0]    vm_waddr,
    output reg  [FW-1:0]     vm_wdata,
    output reg               c_valid,
    input  wire              c_ready,
    output reg  [FW-1:0]     c_data,
    output reg               c_last,
    output reg               c_mode,
    output reg  [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err,
    input  wire [NP-1:0]     me_we,
    input  wire [NP*MAW-1:0] me_addr,
    input  wire [NP*16-1:0]  me_mask
);
    // input registers (the neighbours' output registers)
    reg              i_start, i_core_done, i_core_fault, i_c_ready, i_r_valid, i_r_last, i_r_err;
    reg [NW-1:0]     i_token, i_pos, i_core_next_token;
    reg [31:0]       i_core_next_val;
    reg [63:0]       i_desc_q;
    reg [FW-1:0]     i_vm_rq, i_r_data;
    reg [RB-1:0]     i_r_rank;
    reg [NP-1:0]     i_me_we;
    reg [NP*MAW-1:0] i_me_addr;
    reg [NP*16-1:0]  i_me_mask;
    always @(posedge clk) begin
        i_start <= start; i_token <= token; i_pos <= pos;
        i_core_done <= core_done; i_core_next_token <= core_next_token; i_core_next_val <= core_next_val;
        i_core_fault <= core_fault; i_desc_q <= desc_q; i_vm_rq <= vm_rq; i_c_ready <= c_ready;
        i_r_valid <= r_valid; i_r_data <= r_data; i_r_last <= r_last; i_r_rank <= r_rank; i_r_err <= r_err;
        i_me_we <= me_we; i_me_addr <= me_addr; i_me_mask <= me_mask;
    end

    wire              s_done, s_fault, s_coll_busy, s_core_start, s_desc_re, s_vm_re, s_vm_we;
    wire              s_c_valid, s_c_last, s_c_mode;
    wire [NW-1:0]     s_next_token, s_core_token, s_core_pos;
    wire [31:0]       s_next_val;
    wire [PAW-1:0]    s_prog_base;
    wire [DAW-1:0]    s_desc_addr;
    wire [VWA-1:0]    s_vm_raddr, s_vm_waddr;
    wire [FW-1:0]     s_vm_wdata, s_c_data;
    wire [TAGW-1:0]   s_c_tag;

    ot_qwen_tp_seq_async_w12 #(.ENABLE_AR256(ENABLE_AR256), .ASYNC_COLL(ASYNC_COLL), .SB_PIPE(SB_PIPE), .NP(NP), .MAW(MAW),
        .N(N), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(DAW), .FW(FW), .TAGW(TAGW),
        .QWEN_FULLSHAPE(QWEN_FULLSHAPE)) seq (
        .clk(clk), .rst_n(rst_n), .start(i_start), .token(i_token), .pos(i_pos),
        .done(s_done), .next_token(s_next_token), .next_val(s_next_val), .fault(s_fault),
        .coll_busy(s_coll_busy),
        .core_start(s_core_start), .core_token(s_core_token), .core_pos(s_core_pos),
        .core_done(i_core_done), .core_next_token(i_core_next_token), .core_next_val(i_core_next_val),
        .core_fault(i_core_fault), .prog_base(s_prog_base),
        .desc_re(s_desc_re), .desc_addr(s_desc_addr), .desc_q(i_desc_q),
        .vm_re(s_vm_re), .vm_raddr(s_vm_raddr), .vm_rq(i_vm_rq),
        .vm_we(s_vm_we), .vm_waddr(s_vm_waddr), .vm_wdata(s_vm_wdata),
        .c_valid(s_c_valid), .c_ready(i_c_ready), .c_data(s_c_data), .c_last(s_c_last), .c_mode(s_c_mode),
        .c_tag(s_c_tag),
        .r_valid(i_r_valid), .r_data(i_r_data), .r_last(i_r_last), .r_rank(i_r_rank), .r_err(i_r_err),
        .me_we(i_me_we), .me_addr(i_me_addr), .me_mask(i_me_mask));

    // output registers (the neighbours' input / address registers)
    always @(posedge clk) begin
        done <= s_done; next_token <= s_next_token; next_val <= s_next_val; fault <= s_fault;
        coll_busy <= s_coll_busy; core_start <= s_core_start; core_token <= s_core_token; core_pos <= s_core_pos;
        prog_base <= s_prog_base; desc_re <= s_desc_re; desc_addr <= s_desc_addr;
        vm_re <= s_vm_re; vm_raddr <= s_vm_raddr; vm_we <= s_vm_we; vm_waddr <= s_vm_waddr; vm_wdata <= s_vm_wdata;
        c_valid <= s_c_valid; c_data <= s_c_data; c_last <= s_c_last; c_mode <= s_c_mode; c_tag <= s_c_tag;
    end
endmodule
