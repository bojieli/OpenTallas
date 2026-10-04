`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_pkg_ctl: the package controller between the host interface's
// step engine port (ot_host_if MODE 0) and the D dies of a TP-D tensor group.
// NEW.  It presents the group to the host interface as one decode engine:
//
//   start   one registered start pulse to every die (token, position and the
//           user's KV base latched with it); the dies' KV services take it as
//           their token boundary.
//   done    raised when EVERY die's sequencer is done AND every die's KV
//           service is drained (every KV write of the step has its tagged
//           HBM write-done): a token is reported to the host only once the
//           KV state it created is durable.  The done level falls on the edge
//           that samples the host's next start (the host_if contract).
//   check   the D dies must agree on {token, logit} (they computed the same
//           argmax through the all-gather); a disagreement is a fault.
//   fault   any die fault, a disagreement, or a step that exceeds WDOG cycles;
//           a fault during a step completes it at once (fail closed), as does
//           a start before the reset sequencer reports ready.
// ---------------------------------------------------------------------------
module ot_qwen_sys_pkg_ctl #(
    parameter integer D    = 4,
    parameter integer NW   = 16,
    parameter integer AW   = 24,
    parameter integer WDOG = 1 << 22
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            ready,             // the reset sequencer's sys_ready
    // host interface engine port
    input  wire            eng_start,
    input  wire [NW-1:0]   eng_token,
    input  wire [NW-1:0]   eng_pos,
    input  wire [AW-1:0]   eng_kv_base,
    output reg             eng_done,
    output reg  [NW-1:0]   eng_next_token,
    output reg  [31:0]     eng_next_val,
    output reg  [31:0]     eng_cycles,
    output wire            eng_fault,
    // dies
    output reg             d_start,
    output reg  [NW-1:0]   d_token,
    output reg  [NW-1:0]   d_pos,
    output reg  [AW-1:0]   d_kv_base,
    input  wire [D-1:0]    d_done,
    input  wire [D*NW-1:0] d_next_token,
    input  wire [D*32-1:0] d_next_val,
    input  wire [D-1:0]    d_drained,
    input  wire [D-1:0]    d_fault,
    output reg             disagree,
    output reg             wdog_fault,
    output reg             start_unready,
    output reg  [31:0]     n_steps
);
    reg busy, s1, s2;
    reg [31:0] wd;
    integer k;
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (k = 1; k < D; k = k + 1)
            if (d_next_token[k*NW +: NW] != d_next_token[0 +: NW] || d_next_val[k*32 +: 32] != d_next_val[0 +: 32])
                agree = 1'b0;
    end
    assign eng_fault = (|d_fault) || disagree || wdog_fault || start_unready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; s1 <= 1'b0; s2 <= 1'b0; eng_done <= 1'b0; eng_next_token <= 0; eng_next_val <= 0;
            eng_cycles <= 0; d_start <= 1'b0; d_token <= 0; d_pos <= 0; d_kv_base <= 0;
            disagree <= 1'b0; wdog_fault <= 1'b0; start_unready <= 1'b0; wd <= 0; n_steps <= 0;
        end else begin
            d_start <= 1'b0;
            s1 <= d_start; s2 <= s1;
            if (eng_start && !ready) begin
                // fail closed: the step completes at once with a fault (an error completion to the host)
                start_unready <= 1'b1; eng_done <= 1'b1;
            end else if (eng_start) begin
                busy <= 1'b1; eng_done <= 1'b0; d_start <= 1'b1; wd <= 0; eng_cycles <= 0;
                d_token <= eng_token; d_pos <= eng_pos; d_kv_base <= eng_kv_base;
            end else if (busy && (|d_fault || wdog_fault)) begin
                // a die fault aborts the step: the host gets an error completion instead of a hang
                busy <= 1'b0; eng_done <= 1'b1;
            end else if (busy) begin
                eng_cycles <= eng_cycles + 1;
                wd <= wd + 1;
                if (wd >= WDOG) wdog_fault <= 1'b1;
                // the dies clear `done` on the edge that samples d_start: wait two edges past it
                if (!d_start && !s1 && !s2 && (&d_done) && (&d_drained)) begin
                    busy <= 1'b0; eng_done <= 1'b1; n_steps <= n_steps + 1;
                    eng_next_token <= d_next_token[0 +: NW]; eng_next_val <= d_next_val[0 +: 32];
                    if (!agree) disagree <= 1'b1;
                end
            end
        end
    end
endmodule
