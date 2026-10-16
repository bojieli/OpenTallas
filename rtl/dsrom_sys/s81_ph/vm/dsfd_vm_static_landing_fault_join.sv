`timescale 1ns/1ps
`default_nettype none
// A real hardened diagnostic join. Input pins and output pins terminate in independent register stages.
// Lane flags are sticky upstream; this leaf is exactly a two-edge delayed OR, including reset propagation.
// There is no local reset or startup protocol: the lane reset zeros traverse these two plain stages.
module dsfd_vm_static_landing_fault_join (
    input wire ck, input wire [11:0] i_fault, output reg [2:0] o_fault
);
    reg [11:0] q_fault;
    always @(posedge ck) begin
        q_fault <= i_fault;
`ifdef OT_VM_LANDING_JOIN_MUT_DROP
        o_fault <= q_fault[2:0] | q_fault[5:3] | q_fault[8:6];
`else
        o_fault <= q_fault[2:0] | q_fault[5:3] | q_fault[8:6] | q_fault[11:9];
`endif
    end
endmodule
`default_nettype wire
