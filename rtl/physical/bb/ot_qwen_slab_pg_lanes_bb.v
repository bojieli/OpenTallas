// Synthesis blackbox of the CLOSED hard child ot_qwen_slab_pg_lanes (view physical/ref_tile/qfd_slab_pg_lanes); ports
// exactly as rtl/physical/ot_qwen_slab_port_group.sv (LN 4).  Parents bind the view (LEF/LIB) through SYNTH_BLACKBOXES.
(* blackbox *)
module ot_qwen_slab_pg_lanes (
    input  wire         clk,
    input  wire         rs0,
    input  wire [3:0]   l_v,
    input  wire [3:0]   l_ws,
    input  wire [127:0] a,
    input  wire [63:0]  s,
    output wire [127:0] y,
    output wire [3:0]   vo,
    output wire [7:0]   err
);
endmodule
