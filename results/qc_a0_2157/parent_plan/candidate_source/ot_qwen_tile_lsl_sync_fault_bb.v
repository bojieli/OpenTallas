// UNSELECTED blackbox declaration for a NEW ABSENT master; not a renamed physical view.
// Planned new hard-child declaration; source is rtl/physical/ot_qwen_tile_lsl_sync_fault.sv.
(* blackbox *)
module ot_qwen_tile_lsl_sync_fault (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_d,
    input  wire          first_d,
    input  wire [3:0]    split_d,
    input  wire [255:0]  w_d,
    input  wire [127:0]  x_d,
    output wire [63:0]   t_out,
    output wire  [7:0]    lfault,
    output wire           tfault
);
endmodule
