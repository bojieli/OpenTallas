`timescale 1ns/1ps
`default_nettype none
// L2H-PAD l21 (LEAD2-HBM, 2026-10-19): host observation readback leaf.
//
// Every observation export of the d4g die (fault_cause codes, stat_cycles counters, done/busy/quiet completion flags,
// calendar sequence / client fields, edge indices, ...) that no datapath consumer reads lands in one of these leaves, so
// the host can read it back over the existing AXI-lite read channel of the host ingress (window 0x000-0x3FF, see
// ot_hbm_host_static_ingress_obs). The leaves form one registered chain (a ring from the ingress through every leaf
// back to the ingress); nothing in the chain gates, stalls or reschedules execution (static schedule untouched).
//
//  obs[N-1:0]  observation bits. Every bit lands in a pin flop (p1). SYNC_MASK bits (sources in another clock domain:
//              serial SU programme slices, clock-generator status) take a second synchroniser flop (p2); a read that
//              coincides with a change of such a multi-bit field may mix old and new bits (read twice for coherence).
//  live        = registered sample (page 0).  sticky = OR of live since the last page-1 read of that word (page 1,
//              read-to-clear), so a one-cycle done / fault pulse is never missed by the host.
//  chain       q_* in -> r_* out, one request packet {v, idx, d}. idx = {lid[2:0], page, word[3:0]}. A leaf whose LID
//              matches ORs its word into d; every other leaf forwards d unchanged (the ingress injects d = 0, exactly
//              one leaf matches, so the OR is a select). Fixed latency 3 edges per leaf (pin regs in, one-hot decode,
//              registered out); the die relay planner adds registered stations on hops longer than the reach, so the
//              ring latency is fixed per die revision; the ingress waits for the returning v (single read in flight).
//  Safe design: all pins registered; reset lands in 2+1 relay stages (ot_rst_relay); payload flops have no reset;
//              one-hot selects are registered and replicated per page / clear (each drives 32 loads); the read OR is
//              <= 2*NW = 32 terms (5 levels); N <= 512 (live + sticky <= 1024 flops, below the 2 kb SRAM threshold;
//              they must be parallel-sampled flops, not a runtime-indexed array that SRAM could hold).
// MUT (bench only): 1 page-1 read does not clear, 2 obs[N-1] dropped, 3 page select swapped (live <-> sticky).
module ot_hbm_obs_leaf #(
    parameter integer N = 32,
    parameter integer LID = 0,
    parameter [511:0] SYNC_MASK = 512'd0,
    parameter integer MUT = 0
)(
    input  wire clk, rst_n,
    input  wire [N-1:0] obs,
    input  wire q_v,
    input  wire [7:0] q_idx,
    input  wire [31:0] q_d,
    output reg  r_v,
    output reg  [7:0] r_idx,
    output reg  [31:0] r_d
);
    localparam integer NW = (N + 31) / 32;
    localparam integer NP = NW * 32;
    wire [0:0] lrst_n;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(lrst_n));

    // observation pin flops (+ synchroniser stage for SYNC_MASK bits); no reset: sampled every edge
    reg [N-1:0] p1, p2;
    always @(posedge clk) begin p1 <= obs; p2 <= p1; end
    wire [N-1:0] sm = SYNC_MASK[N-1:0];
    wire [N-1:0] live_n = (p1 & ~sm) | (p2 & sm);
    wire [NP-1:0] live;
    assign live[N-1:0] = live_n & ((MUT == 2) ? ({N{1'b1}} >> 1) : {N{1'b1}});
    generate if (NP > N) begin : g_pad
        assign live[NP-1:N] = {(NP - N){1'b0}};
    end endgenerate

    // chain pin flops
    reg a_v; reg [7:0] a_idx; reg [31:0] a_d;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) a_v <= 1'b0; else a_v <= q_v;
    always @(posedge clk) begin a_idx <= q_idx; a_d <= q_d; end

    // registered one-hot word selects, one copy per use (page 0 read, page 1 read, page 1 clear)
    (* keep = "true" *) reg [NW-1:0] oh0, oh1, clr;
    reg b_v; reg [7:0] b_idx; reg [31:0] b_d;
    wire hit = a_v && ({29'd0, a_idx[7:5]} == LID);
    integer w;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) begin oh0 <= {NW{1'b0}}; oh1 <= {NW{1'b0}}; clr <= {NW{1'b0}}; b_v <= 1'b0; end
        else begin
            b_v <= a_v;
            for (w = 0; w < NW; w = w + 1) begin
                oh0[w] <= hit && (a_idx[4] == (MUT == 3)) && {28'd0, a_idx[3:0]} == w;
                oh1[w] <= hit && (a_idx[4] != (MUT == 3)) && {28'd0, a_idx[3:0]} == w;
                clr[w] <= hit &&  a_idx[4] && {28'd0, a_idx[3:0]} == w && MUT != 1;
            end
        end
    always @(posedge clk) begin b_idx <= a_idx; b_d <= a_d; end

    // sticky (page 1): OR of live since the last page-1 read of the word; read returns the pre-clear value
    reg [NP-1:0] sticky;
    integer k;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) sticky <= {NP{1'b0}};
        else for (k = 0; k < NP; k = k + 1) sticky[k] <= (sticky[k] & ~clr[k / 32]) | live[k];

    reg [31:0] word;
    integer j;
    always @* begin
        word = 32'd0;
        for (j = 0; j < NW; j = j + 1)
            word = word | ({32{oh0[j]}} & live[j * 32 +: 32]) | ({32{oh1[j]}} & sticky[j * 32 +: 32]);
    end
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) r_v <= 1'b0; else r_v <= b_v;
    always @(posedge clk) begin
        r_idx <= b_idx;
        r_d <= b_d | word;
    end
endmodule
`default_nettype wire
