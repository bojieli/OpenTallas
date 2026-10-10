`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_pkgctl (stream qwen-system, 2026-10-08): the full-shape package controller (on die 0, master qfd_sysctl),
// successor of the reduced-vehicle ot_qwen_sys_pkg_ctl with the same host_if engine contract.  Differences:
//   * the dies are reached over the package control channel (CTRL class on the die-to-die link: D-1 remote dies with
//     a link latency, die 0 local), so a die's done level is stale for a link round trip after a start.  Every start
//     carries a 2-bit step generation and a die's done counts only with that generation (the reduced controller's
//     two-edge guard assumed zero-latency wires);
//   * done = every die done for this generation AND drained (the die's stage stepper raises done only after its KV
//     write-back drained, ot_qfd_dctl);
//   * the dies must agree on {token, logit}; any die fault, a disagreement, an out-of-time step (WDOG) or a start
//     before sys_ready completes the step at once with a fault (fail closed).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_pkgctl #(
    parameter integer D    = 4,
    parameter integer NW   = 18,
    parameter integer AW   = 24,
    parameter integer WDOG = 1 << 22,
    // drive-0158 '-cl' (default 0 = reviewed form): DONE_REG=1 registers the D-die reductions (all done for the current
    // generation, any fault, token/value agreement) one edge before use; cleared at a start so a stale previous-
    // generation completion is never seen.  Step completion +1 edge.  Fixes qfd_sysctl_stn_pb2 a3e585f3f TT -91
    // (reg->reg d_gen -> all_done -> n_steps / eng_next_*: compare tree + 100-load enable fan-out in one cycle).
    parameter integer DONE_REG = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            ready,
    // host interface engine port (ot_host_if MODE 0)
    input  wire            eng_start,
    input  wire [NW-1:0]   eng_token,
    input  wire [NW-1:0]   eng_pos,
    input  wire [AW-1:0]   eng_kv_base,
    output reg             eng_done,
    output reg  [NW-1:0]   eng_next_token,
    output reg  [31:0]     eng_next_val,
    output reg  [31:0]     eng_cycles,
    output wire            eng_fault,
    // dies (through the control channel)
    output reg             d_start,
    output reg  [NW-1:0]   d_token,
    output reg  [NW-1:0]   d_pos,
    output reg  [AW-1:0]   d_kv_base,
    output reg  [1:0]      d_gen,
    input  wire [D-1:0]    d_done,
    input  wire [D*2-1:0]  d_done_gen,
    input  wire [D*NW-1:0] d_next_token,
    input  wire [D*32-1:0] d_next_val,
    input  wire [D-1:0]    d_drained,
    input  wire [D-1:0]    d_fault,
    output reg             disagree,
    output reg             wdog_fault,
    output reg             start_unready,
    output reg             die_fault,
    output reg  [31:0]     n_steps
);
    reg busy;
    reg [31:0] wd;
    integer k;
    reg agree_c, all_done_c, any_fault_c;
    reg agree_q, all_done_q, any_fault_q;
    wire agree = DONE_REG ? agree_q : agree_c;
    wire all_done = DONE_REG ? all_done_q : all_done_c;
    wire any_fault = DONE_REG ? any_fault_q : any_fault_c;
    always @(*) begin
        agree_c = 1'b1; all_done_c = 1'b1; any_fault_c = 1'b0;
        for (k = 0; k < D; k = k + 1) begin
            if (d_next_token[k*NW +: NW] != d_next_token[0 +: NW] || d_next_val[k*32 +: 32] != d_next_val[0 +: 32])
                agree_c = 1'b0;
            if (!(d_done[k] && d_drained[k] && d_done_gen[k*2 +: 2] == d_gen)) all_done_c = 1'b0;
            if (d_done[k] && d_done_gen[k*2 +: 2] == d_gen && d_fault[k]) any_fault_c = 1'b1;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin agree_q <= 1'b1; all_done_q <= 1'b0; any_fault_q <= 1'b0; end
        else if (eng_start || !busy) begin agree_q <= 1'b1; all_done_q <= 1'b0; any_fault_q <= 1'b0; end
        else begin agree_q <= agree_c; all_done_q <= all_done_c; any_fault_q <= any_fault_c; end
    assign eng_fault = die_fault || disagree || wdog_fault || start_unready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; eng_done <= 1'b0; eng_next_token <= 0; eng_next_val <= 0; eng_cycles <= 0;
            d_start <= 1'b0; d_token <= 0; d_pos <= 0; d_kv_base <= 0; d_gen <= 2'd0;
            disagree <= 1'b0; wdog_fault <= 1'b0; start_unready <= 1'b0; die_fault <= 1'b0; wd <= 0; n_steps <= 0;
        end else begin
            d_start <= 1'b0;
            if (eng_start && !ready) begin
                start_unready <= 1'b1; eng_done <= 1'b1;
            end else if (eng_start) begin
                busy <= 1'b1; eng_done <= 1'b0; d_start <= 1'b1; d_gen <= d_gen + 1'b1; wd <= 0; eng_cycles <= 0;
                d_token <= eng_token; d_pos <= eng_pos; d_kv_base <= eng_kv_base;
            end else if (busy && any_fault) begin
                die_fault <= 1'b1; busy <= 1'b0; eng_done <= 1'b1;
            end else if (busy && wdog_fault) begin
                busy <= 1'b0; eng_done <= 1'b1;
            end else if (busy) begin
                eng_cycles <= eng_cycles + 1;
                wd <= wd + 1;
                if (wd >= WDOG) wdog_fault <= 1'b1;
                if (all_done) begin
                    busy <= 1'b0; eng_done <= 1'b1; n_steps <= n_steps + 1;
                    eng_next_token <= d_next_token[0 +: NW]; eng_next_val <= d_next_val[0 +: 32];
                    if (!agree) disagree <= 1'b1;
                end
            end
        end
    end
endmodule
