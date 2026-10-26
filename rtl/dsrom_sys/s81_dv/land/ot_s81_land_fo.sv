`timescale 1ns/1ps
`default_nettype none
// S81-P9-CF (2026-10-23): ot_s81_land_fo = ot_s81_land (rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv, contract and calendar
// unchanged, line for line) for a 1-bit lane with NO kept copies of the registered output o: a landed marker bit that
// masks hundreds of data bits (dsfd_cfifo_crs4p) gets one copy per <= ~30 loads (native census <= 32) with no added
// edge.  Same mutant defines as ot_s81_land.
module ot_s81_land_fo #(
    parameter integer NO = 1,       // kept copies of the 1-bit output o (each drives <= ~30 loads)
        parameter integer D  = 4,       // ring depth (power of two, >= 2): window width in periods
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer KW = AW + 1   // LANDFIX-SQ (10-18): strap width.  KW = AW + 1 (default) = the original tiles
                                    // (1 <= K <= 2D-1).  A long lane (E > 2D-1, e.g. the 24-mm S81 host plane, E 28)
                                    // takes KW > AW + 1: the slot / epoch arithmetic stays mod 2D (2^KW is a multiple
                                    // of 2D), only the warm-up count uses the full K, so K = E + G - R0 needs no
                                    // reset-calendar offset between the source gate G and the receiver release R0.
) (
    input  wire [KW-1:0] k,         // read offset K: identity STRAP (die tie, compile-time per lane from the die STA dL
                                    // at TT and FF; 1 <= K <= 2^KW-1); case-analysed in the tile and die STA
    input  wire         ck_f,       // lane forwarded clock (last station ck_o)
    input  wire         i,          // lane data (last station o)
    input  wire         ck,         // block root clock
    input  wire         rs,         // block regional reset, active low (asynchronous assert, release synchronous on ck)
    output wire [NO-1:0] o,
    output reg          fault
);
    reg          bank [0:D-1];
    (* keep *) reg [NO-1:0] oc;
    assign o = oc;
    reg [AW:0]   epo  [0:D-1];
    reg [AW:0]   wc;
    reg [KW-1:0] rc;                // read counter: low AW+1 bits = the read epoch; full width = the warm-up count
    reg          warm;
    // ------------------------------------------------------------------ write side (ck_f)
    always @(posedge ck_f or negedge rs)
        if (!rs) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    genvar s;
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge ck_f)
            if (wc[AW-1:0] == s) begin bank[s] <= i; epo[s] <= wc; end   // no rs term: rs is a ck-domain net
    end endgenerate
    // ------------------------------------------------------------------ read side (ck)
`ifdef OT_S81_LAND_MUT_SEL
    wire [KW-1:0] expw = rc - k + 1'b1;        // bench mutant: read slot one late
`else
    wire [KW-1:0] expw = rc - k;
`endif
    wire [AW:0] exp_ = expw[AW:0];
    always @(posedge ck or negedge rs)
        if (!rs) begin rc <= {KW{1'b0}}; warm <= 1'b0; fault <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == k - 1'b1) warm <= 1'b1;
            if (warm && epo[exp_[AW-1:0]] != exp_) fault <= 1'b1;
        end
`ifdef OT_S81_LAND_MUT_NAIVE
    // bench mutant: bounded-skew retime register only (no ring): o samples the lane directly on ck
    always @(posedge ck) oc <= warm ? {NO{i}} : {NO{1'b0}};
`else
    always @(posedge ck) oc <= warm ? {NO{bank[exp_[AW-1:0]]}} : {NO{1'b0}};
`endif
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_s81_land_fo: D must be a power of two >= 2");
    initial if (KW < AW + 1) $fatal(1, "ot_s81_land_fo: KW must be >= AW + 1");
    always @(posedge ck) if (warm && (k == 0)) $fatal(1, "ot_s81_land_fo: strap k must be >= 1");
`endif
endmodule
`default_nettype wire
