`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-CAPC5 (2026-10-20): opt-in regional reset COPY flop for tools/landed_parent/lp.py spec "regional_reset_copies": true.
// A region whose reset run lpr_<r> would drive > 32 registered loads (landing chunk rq flops + child reset pads) gets its
// LAST regional stage as N parallel kept copies (each <= 32 loads), all fed by the same previous stage: same reset age
// (no added edge, no schedule change), mapped native32 census safe.  Distinct ID per copy = separate hierarchies, so
// Yosys never merges the copies back (keep_hierarchy on the module, keep on the flop).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy = "yes" *)
module ot_pl_land_rst_copy #(parameter integer ID = 0) (
    input  wire ck, d,
    output wire q
);
    (* keep *) reg r;
    always @(posedge ck) r <= d;
    assign q = r;
endmodule
`default_nettype wire
