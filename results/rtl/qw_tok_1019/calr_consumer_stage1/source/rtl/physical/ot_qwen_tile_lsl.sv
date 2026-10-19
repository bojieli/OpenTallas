// el1011-q-tile 2026-10-11: the hardened lane-slice leaf master of the W12 ROM tile (qfd_tile_lsl): ot_qwen_w12_lane_slice
// at the tile's engine parameters (TG 4 groups, 2 lane positions, IL 8, MUL 8 / ACC 7 / TREE 7, LRST 3, ANR 1).  A
// parameter-free top: Yosys 0.68 asserts (rtlil.cc:1231 duplicate module) re-deriving a parameterised top whose children
// arrive late, and the parent instantiates the hardened leaf by this fixed name.
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
    ot_qwen_w12_lane_slice #(.G(4), .NPL(2), .IL(8), .MUL_LAT(8), .ACC_LAT(7), .TREE_LAT(7), .LRST(3), .ANR(1), .TMUT(0)) u_ls (
        .clk(clk), .rst_n(rst_n), .v_d(v_d), .first_d(first_d), .split_d(split_d), .w_d(w_d), .x_d(x_d),
        .t_out(t_out), .lfault(lfault), .tfault(tfault));
endmodule
