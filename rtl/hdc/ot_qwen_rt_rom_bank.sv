`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// A depth-banked ROM of NB ASAP7 ot_rom_4096x266_m8 macros (physical/asap7_memory_macros:
// SS clk->q 739 ps + setup 40 ps inside the 833 ps cycle, the only ROM macro depth that does),
// for the REAL_MEM runtime's die-level ROMs (scale ROM ports; default-off, used only by
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_rm.sv).
//   word a lives in macro a >> 12, row a mod 4096; bits DW-1:0 of the macro word (the rest are
//   unused, no ECC: ROM reliability policy 2026-10-02).  The read is the macro's own synchronous
//   read; the bank select is registered with the address (held when not read) and ORs the
//   selected macro output, so q is valid the cycle after re (and held), exactly the
//   registered-response contract of the core's ROM ports.  An address past NB*4096 enables no
//   macro and raises addr_fault (sticky) instead of reading silent zero.
// The macro contents (its via mask) are preloaded by the simulation host: arr is public.
// ---------------------------------------------------------------------------
module ot_qwen_rt_rom_bank #(
    parameter integer NB = 13,
    parameter integer AW = 24,
    parameter integer DW = 256
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          re,
    input  wire [AW-1:0] addr,
    output wire [DW-1:0] q,
    output reg           addr_fault
);
    wire [AW-13:0] bsel = addr[AW-1:12];
    reg  [NB-1:0]  sel_q;
    wire [266*NB-1:0] rd;
    genvar b;
    generate
        for (b = 0; b < NB; b = b + 1) begin : g_m
            ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(re && bsel == b), .addr_in(addr[11:0]), .rd_out(rd[266*b +: 266]));
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sel_q <= 0; addr_fault <= 1'b0; end
        else if (re) begin
            sel_q <= (bsel < NB) ? (NB'(1) << bsel) : {NB{1'b0}};
            if (bsel >= NB) addr_fault <= 1'b1;
        end
    end
    reg [DW-1:0] orq;
    integer i;
    always @(*) begin
        orq = 0;
        for (i = 0; i < NB; i = i + 1) if (sel_q[i]) orq = orq | rd[266*i +: DW];
    end
    assign q = orq;
endmodule
