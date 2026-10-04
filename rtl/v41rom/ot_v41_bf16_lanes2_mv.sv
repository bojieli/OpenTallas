`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bf16_lanes2_mv: NV activation vectors on ONE BF16 ROM word stream (DS ROM lever L2, the batched DSpark
// draft head: the LM-head matvec of all draft-slot vectors in one head ROM sweep).  Physical screening vehicle.
//
// The captured 256-bit word (16 BF16 weights) is multiplied by NV independent x slices, one unchanged
// ot_v41_bf16_lanes2 per vector (16 exact BF16 products, 16 NCHB-slot golden chunk chains, the 15-adder lane-group
// tree) and, with TREE = 1, one unchanged ot_v41_segtree2 per vector (the element's segment tree).  Every vector's
// arithmetic is therefore the qualified single-vector path, bit for bit: the golden chunk-8 order per vector does
// not depend on NV.  Synthesis merges the NV identical weight-capture registers inside the lanes, so the word
// register fans out to NV x 16 multipliers: that fan-out and the x port width (NV x 256) are what this screens.
// NV = 1, TREE = 0 is ot_v41_bf16_lanes2 itself.  Not instantiated by any shipped element (default-off).
// ---------------------------------------------------------------------------
module ot_v41_bf16_lanes2_mv #(
    parameter integer NV = 1,
    parameter integer NCHB = 8,
    parameter integer TRW = 7,          // {position 3, tree id}: the element's TG at NSEG 8, MTP 1
    parameter integer TREE = 1,
    parameter integer NT = 16,
    parameter integer LV = 5,
    parameter integer EARLY = 1,
    parameter [8:0] CUT = 9'b1_0111_1011
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    v,
    input  wire [255:0]            w,
    input  wire [NV*256-1:0]       x,
    input  wire [$clog2(NCHB)-1:0] slot,
    input  wire                    first,
    input  wire                    last,
    input  wire [TRW-1:0]          tree,
    input  wire                    final_i,
    output wire [NV-1:0]           ov,
    output wire [NV*32-1:0]        oval,
    output wire [NV*TRW-1:0]       otree,
    output wire [NV*3-1:0]         opos,
    output wire [NV-1:0]           oerr,
    output wire                    fault
);
    localparam integer PW = $clog2(NT);
    wire [NV-1:0] lf, tf;
    genvar n;
    generate for (n = 0; n < NV; n = n + 1) begin : g_v
        wire          bv, bfin, berr;
        wire [31:0]   bval;
        wire [TRW-1:0] btree;
        ot_v41_bf16_lanes2 #(.NCHB(NCHB), .TRW(TRW), .CUT(CUT)) u_l (.clk(clk), .rst_n(rst_n), .v(v), .w(w),
            .x(x[256*n +: 256]), .slot(slot), .first(first), .last(last), .tree(tree), .final_i(final_i),
            .ov(bv), .oval(bval), .otree(btree), .ofinal(bfin), .oerr(berr), .fault(lf[n]));
        if (TREE != 0) begin : g_t
            wire [PW-1:0] ot;
            ot_v41_segtree2 #(.CUT(CUT), .NT(NT), .LV(LV), .EARLY(EARLY), .QD(8)) u_t (.clk(clk), .rst_n(rst_n),
                .in_v(bv), .in_tree(btree[PW-1:0]), .in_pos(btree[TRW-1 -: 3]), .in_val(bval), .in_final(bfin),
                .in_err(berr), .ov(ov[n]), .otree(ot), .opos(opos[3*n +: 3]), .oval(oval[32*n +: 32]),
                .oerr(oerr[n]), .fault(tf[n]));
            assign otree[TRW*n +: TRW] = {{(TRW-PW){1'b0}}, ot};
        end else begin : g_nt
            assign ov[n] = bv; assign oval[32*n +: 32] = bval; assign otree[TRW*n +: TRW] = btree;
            assign opos[3*n +: 3] = btree[TRW-1 -: 3]; assign oerr[n] = berr; assign tf[n] = 1'b0;
        end
    end endgenerate
    assign fault = |{lf, tf};
endmodule
