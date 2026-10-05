`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA1 (R1b): per-consumer tx-count arrival counter, mbarrier-style.
//
// Every participant's arrival is a toggle-coded sense (as ot_gpu_barrier_node
// expects from ot_gpu_simt_sm.bar_arrive).  Each consumer owns one of these
// counters and receives every participant's sense on its own point-to-point
// wire; there is no root and no release broadcast.  The consumer's phase
// completes when the count of arrivals of the current phase reaches K
// (EXPECT), and `rel` (the consumer's release sense) toggles one register
// later.  An arrival is attributed to a phase by its sense (arrival n carries
// parity n), so a fast participant that already arrived at the next barrier
// is counted into the next phase, never the current one: two counters,
// current and next, as in an mbarrier's pending/next-phase count.  A
// participant can be at most one phase ahead of any consumer, because its
// next arrival needs this consumer's arrival first.
//   seen   last sense received per source (edge detection; 1 flop per source)
//   cur    arrivals of the current phase (parity ~phase)
//   nxt    arrivals already received for the next phase
// ENABLE = 0: inert (rel = 0).
// ---------------------------------------------------------------------------
module ot_hbm_txcount_arrival #(
    parameter integer ENABLE = 0,
    parameter integer K      = 32,
    parameter integer EXPECT = K
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [K-1:0] arr,        // participants' arrival senses (after their wire stages)
    output wire         rel         // this consumer's release sense
);
    localparam integer CW = $clog2(K + 1);
generate if (ENABLE == 0) begin : g_off
    assign rel = 1'b0;
end else begin : g_on
    reg [K-1:0]  seen;
    reg [CW-1:0] cur, nxt;
    reg          phase;             // parity of completed phases; current arrivals carry ~phase
    wire [K-1:0] edge_v = arr ^ seen;
    // an edge whose new sense is ~phase belongs to the current phase, otherwise to the next
    wire [K-1:0] e_cur = edge_v & ~(arr ^ {K{~phase}});
    wire [K-1:0] e_nxt = edge_v &  (arr ^ {K{~phase}});
    reg  [CW-1:0] n_cur, n_nxt;
    integer i;
    always @* begin
        n_cur = 0; n_nxt = 0;
        for (i = 0; i < K; i = i + 1) begin
            n_cur = n_cur + {{(CW-1){1'b0}}, e_cur[i]};
            n_nxt = n_nxt + {{(CW-1){1'b0}}, e_nxt[i]};
        end
    end
    wire [CW:0] tot = {1'b0, cur} + {1'b0, n_cur};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seen <= {K{1'b0}}; cur <= 0; nxt <= 0; phase <= 1'b0;
        end else begin
            seen <= arr;
            if (tot == EXPECT) begin
                phase <= ~phase;
                cur   <= nxt + n_nxt;
                nxt   <= 0;
            end else begin
                cur   <= tot[CW-1:0];
                nxt   <= nxt + n_nxt;
            end
        end
    end
    assign rel = phase;
end endgenerate
endmodule
