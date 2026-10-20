// ot_v41_kand: a W-bit AND that synthesis keeps as its own instance (S81-QXPQ4 / TILES-C 10-20).  Two instances of
// the same AND are NOT merged (ABC cannot cross the kept hierarchy), so a wide enable fan-out becomes a two-level
// tree of kept copies (each copy driving <= 32 loads) with no added cycle.
(* keep_hierarchy *)
module ot_v41_kand #(
    parameter integer W = 1
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] y
);
    assign y = a & b;
endmodule
