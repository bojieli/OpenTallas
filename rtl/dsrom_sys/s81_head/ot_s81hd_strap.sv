`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_strap (S81-HEAD 10-24): the per-instance position straps of a head tile (row0 = the bundle's first vocab
// row, ten = 1 for a used tile, 0 for a dark one) as mask-programmed tie cells.  The die plan replicates ONE hd_tile
// partition layout (the ROM via code is already per instance); the 18 strap bits are one TIEHI or TIELO cell each at
// a fixed site, so an instance differs from the kit only by the tie master at those 18 sites (TIEHIx1 / TIELOx1 share
// the footprint, area 0.04374 um2 each) - the same mask-variant class as the ROM code.  Synthesis sees explicit
// (kept, dont_touch) library cells, so no constant propagates into the tile logic and every instance has the same
// netlist up to those masters.  The consumer registers (ot_s81hd_tile row0_q / ten_q) are static.
// ---------------------------------------------------------------------------
module ot_s81hd_strap #(
    parameter integer ROW0 = 0,
    parameter integer TEN = 1
) (
    output wire [16:0] row0,
    output wire        ten
);
    localparam [17:0] V = {TEN[0], ROW0[16:0]};
    wire [17:0] o;
    genvar b;
    generate for (b = 0; b < 18; b = b + 1) begin : g_b
`ifdef SYNTHESIS
        if (V[b]) begin : g_h
            (* keep = 1, dont_touch = 1 *) TIEHIx1_ASAP7_75t_R u_t (.H(o[b]));
        end else begin : g_l
            (* keep = 1, dont_touch = 1 *) TIELOx1_ASAP7_75t_R u_t (.L(o[b]));
        end
`else
        assign o[b] = V[b];
`endif
    end endgenerate
    assign row0 = o[16:0];
    assign ten = o[17];
endmodule
