`timescale 1ns/1ps
// Local asynchronous assertion / synchronous release leaf. Every transported reset
// has its own two-flop RDC conditioner. DELAY_CYCLES is compiler-priced padding.
// Calendar starts at the qualified upstream release, never at an asynchronous pad.
module ot_s81_reset_leaf #(
    parameter integer DELAY_CYCLES = 1
) (
    input wire ck,
    input wire upstream_rst_n,
    output wire local_rst_n
);
    (* async_reg = "true" *) reg [1:0] release_sync;
    reg [DELAY_CYCLES-1:0] release_pipe;
    integer k;
    always @(posedge ck or negedge upstream_rst_n) begin
        if (!upstream_rst_n) begin
            release_sync <= 2'b00;
            release_pipe <= {DELAY_CYCLES{1'b0}};
        end else begin
            release_sync <= {release_sync[0], 1'b1};
            release_pipe[0] <= release_sync[1];
            for (k = 1; k < DELAY_CYCLES; k = k + 1)
                release_pipe[k] <= release_pipe[k-1];
        end
    end
    assign local_rst_n = release_pipe[DELAY_CYCLES-1];
`ifndef SYNTHESIS
    initial if (DELAY_CYCLES < 1) $fatal(1, "DELAY_CYCLES must be positive");
`endif
endmodule
