`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_stall_export -- per-die stall/trace export (gap S0 of
// /tmp/claude-review-20261003/rombridge: "the original L0 has no DONE and no
// exported stall signal, so it cannot be diagnosed").  Pure observer: every
// input is an existing port-level condition of the die (a valid without its
// ready, a unit busy, a gate low); nothing here feeds back into the datapath.
// New module; a die that does not instantiate it is unchanged (DIAG off).
//
//   * per-cause cycle counters (saturating 32-bit) of each `cause` bit;
//   * progress detector: `progress` pulses (any retirement, handshake or
//     write); after STUCK cycles without one while `active`, `stuck` latches
//     and `stuck_snap` captures the cause vector at that cycle and
//     `stuck_cycle` its time -- the named blocker of a hang;
//   * change trace: on every change of `cause` an entry {cycle, cause} is
//     pushed to a TRACE_DEPTH FIFO drained by trace_valid/trace_ready; when
//     full the entry is counted in `trace_drops` (never silent).
// ---------------------------------------------------------------------------
module ot_dsrom_stall_export #(
    parameter integer NC          = 16,       // cause bits
    parameter integer STUCK       = 100000,   // cycles without progress
    parameter integer TRACE_DEPTH = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              active,
    input  wire              progress,
    input  wire [NC-1:0]     cause,
    output reg  [NC*32-1:0]  cnt,
    output reg               stuck,
    output reg  [NC-1:0]     stuck_snap,
    output reg  [31:0]       stuck_cycle,
    output reg  [31:0]       idle_run,        // current cycles since the last progress
    output reg  [31:0]       idle_max,        // longest such run so far
    output wire              trace_valid,
    input  wire              trace_ready,
    output wire [32+NC-1:0]  trace_data,
    output reg  [31:0]       trace_drops
);
    localparam integer TB = (TRACE_DEPTH > 1) ? $clog2(TRACE_DEPTH) : 1;
    reg [31:0] now;
    reg [NC-1:0] prev;
    reg [32+NC-1:0] tq [0:TRACE_DEPTH-1];
    reg [TB-1:0] tw, tr;
    reg [TB:0] tn;
    assign trace_valid = tn != 0;
    assign trace_data = tq[tr];
    wire tpop = trace_valid && trace_ready;
    wire tpush = (cause != prev);
    wire tfull = (tn == TRACE_DEPTH);
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            now <= 0; prev <= 0; tw <= 0; tr <= 0; tn <= 0; trace_drops <= 0;
            cnt <= 0; stuck <= 1'b0; stuck_snap <= 0; stuck_cycle <= 0; idle_run <= 0; idle_max <= 0;
        end else begin
            now <= now + 1;
            prev <= cause;
            for (i = 0; i < NC; i = i + 1)
                if (cause[i] && cnt[i*32 +: 32] != 32'hFFFFFFFF) cnt[i*32 +: 32] <= cnt[i*32 +: 32] + 1;
            if (progress || !active) idle_run <= 0;
            else begin
                idle_run <= idle_run + 1;
                if (idle_run + 1 > idle_max) idle_max <= idle_run + 1;
                if (idle_run + 1 == STUCK && !stuck) begin
                    stuck <= 1'b1; stuck_snap <= cause; stuck_cycle <= now;
                end
            end
            if (tpush) begin
                if (tfull && !tpop) trace_drops <= trace_drops + 1;
                else begin tq[tw] <= {now, cause}; tw <= tw + 1'b1; end
            end
            if (tpop) tr <= tr + 1'b1;
            tn <= tn + ((tpush && !(tfull && !tpop)) ? 1 : 0) - (tpop ? 1 : 0);
        end
    end
endmodule
