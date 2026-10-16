`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 VM wide BLOCK-read client (hgi-1010/d, 2026-10-10): one client of a 32-lane VM lane group (ot_hgi_vm_lanearb,
// LANE-GROUP DIE CONTRACT) that reads BLOCKS of 4 consecutive sectors (32 FP32 words: one quant_fp8 / FP4 block), one
// block an edge: block i's sector k (< 4) goes on lane (s_i + k) mod 32 (lane b <-> VM bank b), so a block is 4 lane
// requests in one edge.  Blocks may sit anywhere (strided: e.g. the SM x-load's block-dot fragment reads blocks 8
// apart, which all land on the same 4 banks -- one block an edge is that bank set's limit).
//   Ownership: req from open to the end of the burst (closed, every block delivered, every credit home).
//   Credits: LQ a lane, spent at issue, returned by cr.  Responses: in order per lane, any latency / skew; a response on
//   lane L completes the oldest outstanding block that has a sector on L still missing (per-lane slot queues).
//   Delivery: blocks in issue order, one an edge (o_v, o_data = the 4 sectors, o_tag), once all 4 sectors are in; at
//   most D blocks outstanding (issued, not delivered).  The consumer takes every delivery.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_wblk #(
    parameter integer LQ  = 16,
    parameter integer D   = 16,           // blocks outstanding (a power of two)
    parameter integer SW  = 15,
    parameter integer TGW = 8,
    parameter integer MUT = 0             // bench mutant: 1 = sector 3 of a block lands in sector 2's place
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              open,        // a burst begins (req rises)
    input  wire              close,       // no more blocks this burst (level, from the last block's acceptance on)
    input  wire              b_v,
    output wire              b_rdy,
    input  wire [SW-1:0]     b_sec,       // the block's first sector
    input  wire [TGW-1:0]    b_tag,
    output reg               done,        // pulse: closed, every block delivered, every credit home
    output reg               fault,
    output reg               req,
    input  wire              gnt,
    output reg  [32*16-1:0]  q,
    input  wire [31:0]       cr,
    input  wire [32*257-1:0] rsp,
    output reg               o_v,
    output reg  [1023:0]     o_data,
    output reg  [TGW-1:0]    o_tag
);
    localparam integer CW = $clog2(LQ + 1), DW = $clog2(D);
    reg [CW-1:0] crd [0:31];
    reg [1023:0] bd [0:D-1]; reg [3:0] bh [0:D-1]; reg [TGW-1:0] btg [0:D-1];   // slot: data, sectors in, tag
    reg [DW:0] nout; reg [DW-1:0] sh, stl;                                     // slots: outstanding, head, tail
    // per lane: the queue of (slot, sector k) of its outstanding requests
    reg [DW+1:0] lq [0:31][0:D-1]; reg [DW:0] ln [0:31]; reg [DW-1:0] lh [0:31], lt [0:31];
    integer b, k;
    reg can, home;
    always @* begin
        can = req && gnt && b_v && nout < D;
        home = 1'b1;
        for (b = 0; b < 32; b = b + 1) if (crd[b] != LQ[CW-1:0]) home = 1'b0;
        for (k = 0; k < 4; k = k + 1) if (crd[(b_sec[4:0] + k) % 32] == 0) can = 1'b0;
    end
    assign b_rdy = can;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req <= 1'b0; done <= 1'b0; fault <= 1'b0; q <= '0; o_v <= 1'b0; nout <= '0; sh <= '0; stl <= '0;
            for (b = 0; b < 32; b = b + 1) begin crd[b] <= LQ[CW-1:0]; ln[b] <= '0; lh[b] <= '0; lt[b] <= '0; end
            for (k = 0; k < D; k = k + 1) bh[k] <= 4'd0;
        end else begin : seq
            reg [4:0] lb; reg [DW+1:0] e; reg [DW-1:0] sl; reg [1:0] kk; reg dlv; reg [DW:0] n_;
            done <= 1'b0; o_v <= 1'b0; q <= '0;
            if (open && !req) req <= 1'b1;
            // credits back
            for (b = 0; b < 32; b = b + 1) crd[b] <= crd[b] + (cr[b] ? 1 : 0)
                - ((can && ((b - b_sec[4:0]) & 5'h1F) < 4) ? 1 : 0);
            // responses: each completes its lane's oldest outstanding (slot, k)
            for (b = 0; b < 32; b = b + 1) begin
                n_ = ln[b];
                if (rsp[b*257 + 256]) begin
                    if (n_ == 0) fault <= 1'b1;
                    else begin
                        e = lq[b][lh[b]]; sl = e[DW+1:2]; kk = e[1:0];
                        if (MUT == 1 && kk == 2'd3) kk = 2'd2;
                        bd[sl][256*kk +: 256] <= rsp[b*257 +: 256]; bh[sl][kk] <= 1'b1;
                        lh[b] <= lh[b] + 1'b1; n_ = n_ - 1'b1;
                    end
                end
                if (can && ((b - b_sec[4:0]) & 5'h1F) < 4) begin
                    lq[b][lt[b]] <= {stl, 2'(b - b_sec[4:0])}; lt[b] <= lt[b] + 1'b1; n_ = n_ + 1'b1;
                end
                ln[b] <= n_;
            end
            // issue the block (4 lanes, one edge)
            if (can) begin
                for (k = 0; k < 4; k = k + 1) begin
                    lb = b_sec[4:0] + k; q[lb*16 +: 16] <= {1'b1, b_sec + SW'(k)};
                end
                btg[stl] <= b_tag; bh[stl] <= 4'd0; stl <= stl + 1'b1;
            end
            // deliver the head block when complete
            dlv = (nout != 0) && (bh[sh] == 4'hF);
            if (dlv) begin o_v <= 1'b1; o_data <= bd[sh]; o_tag <= btg[sh]; bh[sh] <= 4'd0; sh <= sh + 1'b1; end
            nout <= nout + (can ? 1 : 0) - (dlv ? 1 : 0);
            if (req && close && !b_v && nout == 0 && !dlv && !can && home) begin req <= 1'b0; done <= 1'b1; end
        end
    end
endmodule
`default_nettype wire
