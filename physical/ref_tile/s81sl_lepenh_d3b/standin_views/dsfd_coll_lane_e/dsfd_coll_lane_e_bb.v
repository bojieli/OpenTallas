// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind
(* blackbox *) module dsfd_coll_lane_e (
    input wire ck,
    input wire rs,
    input wire chb,
    input wire [514:0] rx,
    output wire [511:0] tx,
    output wire tf,
    input wire lo_v,
    output wire lo_r,
    input wire [552:0] lo_d,
    output wire li_v,
    input wire li_r,
    output wire [552:0] li_d,
    output wire [2:0] flt
);
endmodule
