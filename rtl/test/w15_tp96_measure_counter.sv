`timescale 1ns/1ps
// Testbench instrumentation only. Never drives the collective or wire timestamp.
module w15_tp96_measure_counter #(
    parameter integer WIDTH = 64
) (
    input wire clk,
    input wire enabled,
    output reg [WIDTH-1:0] cycles = 0
);
    // 8,000,000 ns campaign timeout / nominal 1.111111 ns: at least 23 bits.
    initial if (WIDTH < 23 || WIDTH > 64) $fatal(1, "measurement width must be 23..64");
    always @(posedge clk) if (enabled) begin
        if (&cycles) $fatal(1, "measurement counter overflow");
        cycles <= cycles + 1'b1;
    end
endmodule
