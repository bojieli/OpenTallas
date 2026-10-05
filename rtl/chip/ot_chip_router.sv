`timescale 1ns/1ps
// The mesh node router as hardened: 5 ports (local + N, E, S, W) of 512-bit
// flits, 4-flit buffers, 32 routing-table entries written at run time.
module ot_chip_router (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    in_valid,
    output wire [4:0]    in_ready,
    output wire [4:0]    in_credit,
    input  wire [5*512-1:0] in_data,
    input  wire [4:0]    in_last,
    output wire [4:0]    out_valid,
    input  wire [4:0]    out_ready,
    output wire [5*512-1:0] out_data,
    output wire [4:0]    out_last,
    input  wire          cfg_we,
    input  wire [7:0]    cfg_dest,
    input  wire [4:0]    cfg_mask,
    output wire [31:0]   drops,
    output wire          overflow
);
    ot_rom_fabric_router #(.NP(5), .FW(512), .BUF(4), .DESTS(32)) u (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_ready(in_ready), .in_credit(in_credit), .in_data(in_data),
        .in_last(in_last), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data),
        .out_last(out_last), .cfg_we(cfg_we), .cfg_dest(cfg_dest), .cfg_mask(cfg_mask),
        .drops(drops), .overflow(overflow));
endmodule
