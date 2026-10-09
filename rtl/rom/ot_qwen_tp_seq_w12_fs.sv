`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_tp_seq_w12_fs (stream qwen-system, 2026-10-08): the W12 tensor-group sequencer with a FULL-SHAPE collective
// tag.  The base (ot_qwen_tp_seq_w12) tags every collective record {token, pos[7:0], seg} (TAGW = 32; with NW = 18 the
// two top token bits are cut).  At full shape the sequencer runs ONE STAGE program per start (38 stages a token: E,
// L0..L35, H; ot_qfd_dctl), so the base tag is identical in all 36 layer stages of a token (the same segment numbers
// repeat) and repeats every 256 positions: a die that slipped a whole stage (or 256 positions with the same token bits)
// would exchange records the one-shot engine accepts as agreeing.  The ot_rom_oneshot_die agreement check then cannot
// catch a stage-desynchronised die.  This wrapper keeps the base unchanged and replaces the tag with
//     c_tag = {gen[1:0], stage[5:0], pos[12:0], token[7:0], seg[2:0]}            (32 b, P <= 8,192, <= 8 segments)
// gen = the package step generation (ot_qfd_pkgctl d_gen via ot_qfd_dctl), stage = ot_qfd_dctl stage; both latched with
// the start, as the base latches token and position.  seg is the base tag's low DAW bits (its segment counter).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_tp_seq_w12_fs #(
    parameter integer ENABLE_AR256 = 0,
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
    input  wire [5:0]        tag_stage,
    input  wire [1:0]        tag_gen,
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
    output wire              c_valid,
    input  wire              c_ready,
    output wire [FW-1:0]     c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err
);
    wire [TAGW-1:0] tag_b;
    ot_qwen_tp_seq_w12 #(.ENABLE_AR256(ENABLE_AR256), .N(N), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(DAW), .FW(FW),
                         .TAGW(TAGW), .QWEN_FULLSHAPE(QWEN_FULLSHAPE)) u_base (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos), .done(done), .next_token(next_token),
        .next_val(next_val), .fault(fault), .coll_busy(coll_busy), .core_start(core_start), .core_token(core_token),
        .core_pos(core_pos), .core_done(core_done), .core_next_token(core_next_token), .core_next_val(core_next_val),
        .core_fault(core_fault), .prog_base(prog_base), .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
        .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .c_valid(c_valid), .c_ready(c_ready), .c_data(c_data), .c_last(c_last), .c_mode(c_mode), .c_tag(tag_b),
        .r_valid(r_valid), .r_data(r_data), .r_last(r_last), .r_rank(r_rank), .r_err(r_err));
    reg [1:0]  gen_t;
    reg [5:0]  stg_t;
    reg [12:0] pos_t;
    reg [7:0]  tok_t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin gen_t <= 0; stg_t <= 0; pos_t <= 0; tok_t <= 0; end
        else if (start) begin gen_t <= tag_gen; stg_t <= tag_stage; pos_t <= pos[12:0]; tok_t <= token[7:0]; end
    end
    assign c_tag = TAGW'({gen_t, stg_t, pos_t, tok_t, tag_b[2:0]});
endmodule
