`timescale 1ns/1ps
// Candidate reset-epoch barrier. released[] must be real producer acknowledgments
// from each required child's final reset conditioner, not operation/slot readiness.
// Any assertion kills admission asynchronously. Release is sampled twice, then
// must remain live for two local edges. No fixed delay guesses a distant child's state.
module ot_s81_startup_barrier #(
    parameter integer N = 1,
    parameter integer MUT_EARLY = 0
) (
    input wire clk,
    input wire reset_n,
    input wire [N-1:0] released,
    output wire ready
);
    wire joined_reset_n = reset_n && (&released);
    (* keep = 1 *) reg [1:0] release_sync;
    reg stable_one, admitted;
    always @(posedge clk or negedge joined_reset_n) begin
        if (!joined_reset_n) begin
            release_sync <= 2'b00;
            stable_one <= 1'b0;
            admitted <= 1'b0;
        end else begin
            release_sync <= {release_sync[0], 1'b1};
            if (release_sync[1]) begin
                stable_one <= 1'b1;
                admitted <= stable_one;
            end
        end
    end
    // Keep cancellation independent of the local clock, including lock loss.
    assign ready = MUT_EARLY ? reset_n : joined_reset_n && admitted;
endmodule
