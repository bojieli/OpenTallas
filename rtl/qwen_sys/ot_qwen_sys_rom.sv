`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_rom: a die ROM / SRAM read port of the Qwen ROM system top with
// an address-bound check (rom_bridge_gaps DA1: an address past the macro read
// silent zero).  Synchronous read, latency 1.  The content is the macro's
// programmed image: for simulation it is loaded from +DIR=<images>/<NAME><die>.hex
// (tools/hdc_program.py --tp images); an address >= DEPTH latches `oob`
// (sticky) and returns zero.  No parity / ECC (ROM reliability policy,
// AGENTS.md 2026-10-02): the bound is a transaction-validity check.
// ---------------------------------------------------------------------------
module ot_qwen_sys_rom #(
    parameter integer DW    = 64,
    parameter integer DEPTH = 4096,
    parameter integer AW    = 24,
    parameter         NAME  = "rom_d",
    parameter integer DIE   = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          re,
    input  wire [AW-1:0] addr,
    output reg  [DW-1:0] q,
    output reg           oob
);
    reg [DW-1:0] mem [0:DEPTH-1];
    reg [8*512-1:0] dir;
    integer i;
    initial begin
        for (i = 0; i < DEPTH; i = i + 1) mem[i] = {DW{1'b0}};
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/", NAME, 8'h30 + DIE[7:0], ".hex"}, mem);
    end
    always @(posedge clk) if (re) q <= (addr < DEPTH) ? mem[addr] : {DW{1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) oob <= 1'b0;
        else if (re && addr >= DEPTH) oob <= 1'b1;
endmodule
