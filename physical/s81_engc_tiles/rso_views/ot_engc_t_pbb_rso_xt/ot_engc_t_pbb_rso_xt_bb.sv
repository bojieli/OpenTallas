// Physical symbol derived from actual matching TT/FF/SS ETM pins.
// Use source RTL for simulation; native slot/source binding remains open.
(* blackbox, keep_hierarchy *) module ot_engc_t_pbb_rso_xt (
    input wire ck,
    input wire [7:0] r_a,
    output wire [255:0] r_d,
    input wire [5:0] r_oh,
    output wire rso,
    input wire rst,
    input wire [7:0] w_a,
    input wire [255:0] w_d,
    input wire [5:0] w_oh,
    output wire [7:0] x_a,
    input wire [319:0] x_d,
    output wire [319:0] x_do,
    output wire [5:0] x_oh
);
endmodule
