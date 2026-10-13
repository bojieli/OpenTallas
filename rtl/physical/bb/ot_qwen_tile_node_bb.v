// blackbox of the hardened tree-node leaf ot_qwen_tile_node (views physical/ref_tile/ot_qwen_tile_node/views) for the r5
// qfd_tile_nk parent synthesis (tile parameter NDH = 1)
(* blackbox *)
module ot_qwen_tile_node (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  a,
    input  wire [511:0]  b,
    input  wire          va,
    output wire [511:0]  y,
    output wire          vy,
    output wire          fault,
    input  wire [511:0]  t_d,
    input  wire          t_vd,
    output wire [511:0]  t_out,
    output wire          t_vout
);
endmodule
