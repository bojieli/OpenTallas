// Physical symbol derived from actual matching TT/FF/SS ETM pins.
// Use source RTL for simulation; native slot/source binding remains open.
(* blackbox, keep_hierarchy *) module ot_engc_t_ws_rso (
    output wire [255:0] b1_d,
    input wire ck,
    input wire [264:0] f_hr,
    input wire [30:0] lk_hqa,
    input wire [2:0] lk_hqt,
    input wire lk_hqv,
    output wire [264:0] lk_hr,
    output wire rso,
    input wire rst,
    output wire [34:0] t_hq,
    output wire [7:0] w_a,
    output wire [5:0] w_oh,
    output wire werr,
    input wire [10:0] wr_addr,
    input wire [511:0] wr_data,
    input wire wr_v,
    output wire [319:0] x_d
);
endmodule
