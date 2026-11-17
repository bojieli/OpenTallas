`timescale 1ns/1ps
// Static admission invariant: a loaded token/position must reach its first bank consumer
// before a previous-inference argmax result may overwrite it. This only reports a
// compiler error; it never suppresses writes, selects a programme, or stalls execution.
module qfd_mu_context_guard #(
    parameter integer NU = 4, ENABLE = 1, MUT = 0,
    parameter integer UB = (NU > 1) ? $clog2(NU) : 1
) (
    input wire ck, rst_n,
    input wire load,
    input wire [2:0] load_mask,
    input wire consume,
    input wire [UB-1:0] consume_user,
    input wire result_write,
    input wire [UB-1:0] result_user,
    output reg fault
);
    reg [NU-1:0] pending;
    integer u;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pending <= {NU{1'b0}}; fault <= 1'b0; end
        else if (ENABLE) begin
            if (result_write && result_user != 0 && result_user < NU && pending[result_user] && MUT != 1)
                fault <= 1'b1;
            // A same-edge consume still reads the pre-edge bank; strict admission
            // requires the first result write to follow the consume edge.
            if (consume && consume_user < NU) pending[consume_user] <= 1'b0;
            if (load)
                for (u = 1; u < NU; u = u + 1)
                    if (load_mask[u-1]) pending[u] <= 1'b1;
        end
endmodule
