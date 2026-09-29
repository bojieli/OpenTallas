`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One BANK of a VM_DIST lane group (rtl/chip/ot_v41_vm_dist.sv): the storage of
// ROWS rows of RW 32-bit elements, the shape of one ot_sram_1r1w_256x256 macro
// (RW = 8, ROWS = 256 at full shape).
//
// Physically the bank is NRC read replicas of that macro (one per read class:
// operand streams A, B, C, D, the gather index G and the tree read X), all
// written together through the macro's single masked row-write port.  This
// behavioural model keeps ONE copy of the rows and serves:
//   * NP row-read ports (registered, one-cycle read: an address in cycle t is
//     answered in t+1).  Ports 0 .. NRC-1 are the replicas; ports NRC .. NP-1
//     are OVERFLOW ports the group uses only when a class asks for a second row
//     in the same cycle (a read-rule violation the group counts);
//   * NWP masked row writes a cycle, applied in port order after the reads
//     (read-during-write returns the old row, as the flat VM and the macro do).
//     One row a cycle is the macro's port; more are the write buffer's traffic,
//     which the group counts (ot_v41_vm_dist_group mon_* outputs).
// Replacing the storage by NRC ot_sram_1r1w macros and the write list by the
// group's arbiter is the hardening step; the ports here are the macro's.
// ---------------------------------------------------------------------------
module ot_v41_vm_dist_bank #(
    parameter integer ROWS = 256,
    parameter integer RA   = 8,          // row address bits
    parameter integer RW   = 8,          // elements a row
    parameter integer NP   = 6,          // read ports
    parameter integer NWP  = 8           // row writes a cycle
) (
    input  wire                 clk,
    input  wire [NP-1:0]        re,
    input  wire [NP*RA-1:0]     raddr,
    output reg  [NP*RW*32-1:0]  q,
    input  wire [NWP-1:0]       we,
    input  wire [NWP*RA-1:0]    waddr,
    input  wire [NWP*RW*32-1:0] wdata,
    input  wire [NWP*RW-1:0]    wmask         // element mask
);
    reg [RW*32-1:0] mem [0:ROWS-1];
    integer p, e;
    reg [RW*32-1:0] row;
    always @(posedge clk) begin
        for (p = 0; p < NP; p = p + 1)
            if (re[p]) q[p*RW*32 +: RW*32] <= mem[raddr[p*RA +: RA]];
        for (p = 0; p < NWP; p = p + 1)
            if (we[p]) begin
                row = mem[waddr[p*RA +: RA]];
                for (e = 0; e < RW; e = e + 1)
                    if (wmask[p*RW + e]) row[32*e +: 32] = wdata[p*RW*32 + 32*e +: 32];
                mem[waddr[p*RA +: RA]] = row;
            end
    end
endmodule
