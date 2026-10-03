(* blackbox *)
module ot_chip_v41x_coll_transpose #(
    parameter integer WA = 19,
    parameter integer FW = 512,
    parameter integer WRITE_SEG = 16,
    
    
    parameter integer OUT_PIPE = 0
) (
    input  wire clk, rst_n,
    input  wire start,
    input  wire [WA-1:0] dst, n,
    output wire in_ready,
    input  wire in_valid,
    input  wire [4*FW-1:0] in_data,
    input  wire in_last,
    input  wire out_ready,
    output wire out_valid,
    output wire [3:0] out_we,
    output wire [4*WA-1:0] out_addr,
    output wire [4*FW-1:0] out_data,
    output wire out_last,
    output reg done, fault
);
endmodule
