`timescale 1ns/1ps
// Asynchronous-assert, synchronous-deassert reset conditioner.  ASYNC_STAGES
// includes the output stage and must be at least two for a CDC/RDC boundary.
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end

    assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (ASYNC_STAGES < 2)
            $error("ot_reset_sync requires at least two stages");
    end
`endif
endmodule
