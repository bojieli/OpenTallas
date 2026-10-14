// ot_qfd_vm_xrelay_w (VM4 2026-10-13): the x-lane relay with MIRRORED PINS (d on the E face, q on the W face) for the
// westward lanes.  Function = ot_qfd_vm_xrelay_t, bit for bit: its hard view IS the closed route of kit qfd_vm_xrelay_w
// (job qfd_vm_xrelay_w-xw1-5a0fc3266, module ot_qfd_vm_xrelay_t), re-published under this cell name because a netlist
// cannot hold two views of one module name (tools/qwen_tp8/vm_bay_cluster.py --alias; alias.json in the view).
module ot_qfd_vm_xrelay_w #(
    parameter integer W = 512,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    ot_qfd_vm_xrelay_t #(.W(W), .MEREG(MEREG), .MUT(MUT)) u (.clk(clk), .me_e(me_e), .d(d), .q(q));
endmodule
