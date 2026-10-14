`ifdef OT_SPVM_RESET_ACK
`ifndef DSFD_VM_RESET_ACK_SVH
`define DSFD_VM_RESET_ACK_SVH
// Source-candidate telemetry only. A request pulse clears the epoch witness even
// when this consumer clock stops. LOW must then be sampled from the actual final
// local reset state; a missed reset remains unacknowledged until a valid reset.
// ACK adds one consumer edge after witnessed local release. No datapath gating.
module dsfd_vm_reset_ack #(parameter integer N = 1) (
    input wire clk, input wire request_n,
    input wire [N-1:0] local_release, input wire consumer_live,
    output wire ack
);
    reg reset_seen, ack_q;
    always @(posedge clk or negedge request_n) begin
        if (!request_n) begin reset_seen <= 1'b0; ack_q <= 1'b0; end
        else begin
            if (!(|local_release)) reset_seen <= 1'b1;
`ifdef OT_VMFE_MUT_ACK_NO_WITNESS
            ack_q <= (&local_release) && consumer_live;
`else
            ack_q <= reset_seen && (&local_release) && consumer_live;
`endif
        end
    end
`ifdef OT_VMFE_MUT_ACK_FORWARD
    assign ack = request_n;
`else
    assign ack = ack_q && (&local_release) && consumer_live;
`endif
endmodule
`endif
`endif
