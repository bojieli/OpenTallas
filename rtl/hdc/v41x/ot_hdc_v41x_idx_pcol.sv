`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Pooled-indexer collector (spec R-U2): gathers the pooled block-dot tile's
// per-(key, head-group) score rows into one IH-score beat per key for
// ot_hdc_v41x_idx_hsum.
//
// The tile runs an index op in split mode (d_split): row r = (key r / (IH/M),
// head group r mod (IH/M)), M heads per row on its M positions; a result event
// carries 2G rows in row order -- for chunk unit u, row 2u on o_ys/o_fs (o_smask)
// then row 2u+1 on o_y/o_f (o_mask).  So an event is 2GM consecutive heads of
// one key (2GM divides IH), and IH / (2GM) events complete a key.  Rows are
// taken in order; a masked row (past the op's last row) is skipped.
// Output: k_v with the key's IH FP32 scores (head h at [32h +: 32]) and
// per-head faults, registered; no back-pressure (hsum is fixed-latency).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_pcol #(
    parameter integer G  = 1,
    parameter integer M  = 1,
    parameter integer IH = 32
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               i_v,
    input  wire [G-1:0]       i_smask,
    input  wire [G*M*32-1:0]  i_ys,
    input  wire [G*M-1:0]     i_fs,
    input  wire [G-1:0]       i_mask,
    input  wire [G*M*32-1:0]  i_y,
    input  wire [G*M-1:0]     i_f,
    output reg                k_v,
    output reg  [IH*32-1:0]   k_score,
    output reg  [IH-1:0]      k_fault
);
    localparam integer HE = 2 * G * M;              // heads per event
    localparam integer NE = IH / HE;                // events per key
    localparam integer EW = (NE <= 1) ? 1 : $clog2(NE);
    reg [IH*32-1:0] buf_s;
    reg [IH-1:0]    buf_f;
    reg [EW-1:0]    ev;
    // this event's heads, in order
    reg [HE*32-1:0] es;
    reg [HE-1:0]    ef;
    integer u, p;
    always @* begin
        for (u = 0; u < G; u = u + 1)
            for (p = 0; p < M; p = p + 1) begin
                es[((2*u) * M + p) * 32 +: 32]     = i_ys[(u * M + p) * 32 +: 32];
                ef[(2*u) * M + p]                  = i_fs[u * M + p];
                es[((2*u + 1) * M + p) * 32 +: 32] = i_y[(u * M + p) * 32 +: 32];
                ef[(2*u + 1) * M + p]              = i_f[u * M + p];
            end
    end
    wire full_ev = (&i_smask) && (&i_mask);
    generate
        if (NE == 1) begin : g_one
            always @(posedge clk) begin
                k_v <= rst_n && i_v && full_ev;
                if (i_v && full_ev) begin k_score <= es; k_fault <= ef; end
            end
        end else begin : g_acc
            always @(posedge clk) begin
                k_v <= 1'b0;
                if (!rst_n) ev <= 0;
                else if (i_v && full_ev) begin
                    buf_s[ev * HE * 32 +: HE * 32] <= es;
                    buf_f[ev * HE +: HE] <= ef;
                    if (ev == NE - 1) begin
                        k_score <= {es, buf_s[0 +: (NE - 1) * HE * 32]};
                        k_fault <= {ef, buf_f[0 +: (NE - 1) * HE]};
                        k_v <= 1'b1;
                        ev <= 0;
                    end else ev <= ev + 1;
                end
            end
        end
    endgenerate
endmodule
