`timescale 1ns/1ps
// Timed HOST reset-command receiver. Both inputs are synchronous control
// signals: delivered neighbour-wavefront reset and the plan-routed HOST
// command. This is not a CDC synchronizer or a second asynchronous reset root.
// Private latency from an input change after edge N: assert at N+1; release
// after two high samples, at N+2. Transport stages are priced separately.
module qkd_host_reset_command_rx (
    input wire clk,
    input wire wavefront_rst_n,
    input wire command_rst_n,
    output wire local_rst_n
);
    (* keep = "true" *) reg [1:0] release_q;
    always @(posedge clk)
        if (!wavefront_rst_n || !command_rst_n)
            release_q <= 2'b00;
        else
            release_q <= {release_q[0], 1'b1};
    assign local_rst_n = release_q[1];
endmodule
