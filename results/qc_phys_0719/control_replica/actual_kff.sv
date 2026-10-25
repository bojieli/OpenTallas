`timescale 1ns/1ps
(* keep_hierarchy = "yes" *) module qfd_dv_s8x_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule
