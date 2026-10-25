`timescale 1ns/1ps
// Opt-in successor to dsfd_rstg: distinct input capture and output launch registers.
// Throughput remains one 66-bit word/edge; latency is two edges (old1, +1 on this control/return bus).
// Only the valid bit is reset; rs is the delivered column reset, with normal timed recovery/removal.
module dsfd_rstg_2stage (
    input wire [0:0] ck,
    input wire [65:0] i,
    output wire [65:0] o,
    input wire [0:0] rs
);
    reg [65:1] capture_data, launch_data;
    reg capture_valid, launch_valid;
    always @(posedge ck[0]) begin
        capture_data <= i[65:1];
        launch_data <= capture_data;
    end
    always @(posedge ck[0] or negedge rs[0]) begin
        if (!rs[0]) begin capture_valid <= 1'b0; launch_valid <= 1'b0; end
        else begin capture_valid <= i[0]; launch_valid <= capture_valid; end
    end
    assign o = {launch_data, launch_valid};
endmodule
