`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: SRAM-bodied link-end FIFO.  Same ports as ot_qkvd_fifo RH=1, order- and data-exact, dout /
// empty registered; count / full are the occupancy (pushes - pops) exactly as RH=1.  Contract difference: empty means
// "no word at the head" -- while words are in the SRAM read pipeline the head can be empty with count > 0 (a few cycles
// of extra latency, never a reorder or loss).  ot_qkvd_d2d pops only on !empty and uses full only for its overflow
// fault, so it is a drop-in there (cycles may differ; the data stream does not).
//
// Why: the KV end's deep FIFOs (UCX 48 x 2 TX, 32 x 2 RX, W 528) were flop arrays (~97k flops) whose binary rp / wp
// fanned out to every bit of a 32/48:1 read mux and write decode (qkd_d2d_b-765c8c422: 17-19 levels, TT -46.65; the
// d2d_a line only reached TT -0.38 / FF -16.96 with LVT + hold ECO on the same structure).
//
// Structure (every macro pin registered, capture flop on the macro output, no logic before it):
//   push  -> [write stage: sw_v / sw_a / sw_d]  -> 64 x 512 macro (data 511:0) + 64 x (W-512) tag flops
//   req   -> [ra / rq] -> macro read            -> [cap / cap_v] -> output queue (ot_qkvd_fifo RH=1, D = P)
//   push goes straight to the output queue when nothing is in the SRAM path and the queue has room, otherwise to SRAM;
//   the SRAM is read ahead while (queue count + in-flight) < P, so the head is refilled before it drains (P covers the
//   3-cycle request -> queue latency at one pop a cycle).  Pointers drive only macro address pins (fanout 1).
module ot_qkvd_fifo_sb #(
    parameter integer W = 528,                    // > 512: bits 511:0 in the macro, W-1:512 in tag flops
    parameter integer D = 48,                     // <= 64 (macro depth); occupancy is bounded by the caller's credits
    parameter integer P = 8                       // output queue (prefetch) depth
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire [W-1:0] dout,
    output wire         empty,
    output wire         full,
    output reg  [$clog2(D+1)-1:0] count
);
    localparam integer TW = W - 512;
`ifdef KVD_SBP
    localparam integer PQ = `KVD_SBP;             // bench only: a shallow head queue forces traffic through the SRAM path
`else
    localparam integer PQ = P;
`endif
    localparam integer CW = $clog2(PQ + 1);
    assign full = (count == D[$clog2(D+1)-1:0]);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) count <= 0;
        else count <= count + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);

    // ---- SRAM path state -----------------------------------------------------------------------------------------
    reg  [5:0]    wp_s, rp_s, ra, sw_a;
    reg  [6:0]    ns;                             // words staged / in the SRAM, not yet requested
    reg  [CW:0]   f;                              // requested, not yet in the output queue
    reg           sw_v, rq, rd_v, cap_v;
    reg  [511:0]  sw_d;
    reg  [TW-1:0] sw_t, tag_rd;
    reg  [W-1:0]  cap;
    reg  [TW-1:0] tagm [0:63];
    wire [511:0]  rd_out;
    wire [CW-1:0] oc;
    `ifdef KVD_FSBMUT
    wire direct = push && (oc < PQ[CW-1:0]);       // bench mutant: bypasses words still in the SRAM path (reorders)
`else
    wire direct = push && (ns == 0) && (f == 0) && (oc < PQ[CW-1:0]);
`endif
    wire tos    = push && !direct;
    wire req    = (ns != 0) && ({1'b0, oc} + f < PQ);

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wp_s <= 0; rp_s <= 0; ns <= 0; f <= 0; sw_v <= 1'b0; rq <= 1'b0; rd_v <= 1'b0; cap_v <= 1'b0;
        end else begin
            sw_v  <= tos;
            rq    <= req;
            rd_v  <= rq;
            cap_v <= rd_v;
            if (tos) wp_s <= wp_s + 1'b1;
            if (req) rp_s <= rp_s + 1'b1;
            ns <= ns + (tos ? 1'b1 : 1'b0) - (req ? 1'b1 : 1'b0);
            f  <= f + (req ? 1'b1 : 1'b0) - (cap_v ? 1'b1 : 1'b0);
        end
    always @(posedge clk) begin
        if (tos) begin sw_a <= wp_s; sw_d <= din[511:0]; sw_t <= din[W-1:512]; end
        if (sw_v) tagm[sw_a] <= sw_t;
        if (req) ra <= rp_s;
        if (rq) tag_rd <= tagm[ra];
        cap <= {tag_rd, rd_out};
    end

    ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(rq), .r_addr_in(ra), .rd_out(rd_out),
        .w_ce_in(sw_v), .w_addr_in(sw_a), .wd_in(sw_d), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));

    // ---- output queue (registered head) ----------------------------------------------------------------------------
    wire oq_empty, oq_full;
    ot_qkvd_fifo #(.RH(1), .W(W), .D(PQ)) u_oq (.clk(clk), .rst_n(rst_n), .push(direct || cap_v),
        .din(cap_v ? cap : din), .pop(pop), .dout(dout), .empty(oq_empty), .full(oq_full), .count(oc));
    assign empty = oq_empty;
endmodule
