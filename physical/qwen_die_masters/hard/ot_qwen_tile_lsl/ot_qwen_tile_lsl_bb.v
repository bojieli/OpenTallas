// blackbox of the hardened lane-slice leaf (qfd_tile_lsl2 route views) for the round-2 qfd_tile parent synthesis
(* blackbox *)
module ot_qwen_tile_lsl (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_d,
    input  wire          first_d,
    input  wire [3:0]    split_d,
    input  wire [255:0]  w_d,
    input  wire [127:0]  x_d,
    output wire [63:0]   t_out,
    output wire [7:0]    lfault,
    output wire          tfault
);
endmodule
