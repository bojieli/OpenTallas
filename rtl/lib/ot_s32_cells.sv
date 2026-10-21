`timescale 1ns/1ps
// KV-CTL3 10-20: hard-boundary select / gate leaves for native-census (<= 32 mapped loads a driver) slicing.
// A shared condition that drives a wide held register is otherwise folded by ABC into every bit (one net, hundreds of
// loads, however the RTL slices it: S32-B dcfg 199 loads).  Each leaf is a KEPT hierarchy boundary, so its select pin
// is the ONLY reader of the per-slice select net in the parent and the leaf's own W select loads (2 a bit for a mux)
// stay behind it.  The parent gives every leaf a DISTINCT select net (the shared condition ANDed with a per-slice kept
// literal), so no two leaves share one driver.  Pure combinational, no state: function = the expression.
(* keep_hierarchy *)
module ot_s32_sel #(parameter integer W = 16) (input wire s, input wire [W-1:0] a, b, output wire [W-1:0] y);
    assign y = s ? a : b;
endmodule
(* keep_hierarchy *)
module ot_s32_and #(parameter integer W = 16) (input wire s, input wire [W-1:0] a, output wire [W-1:0] y);
    assign y = a & {W{s}};
endmodule
