`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM signature collar for one compiled via-programmed ROM macro
// (tools/mem_compiler/rom_gen.py).
//
// Functional path: combinational pass-through while t_en is low.
// Test path (driven by ot_mbist_ctrl): t_clear resets the signature to
// 0xFFFFFFFF; every t_req reads one address, and one cycle later the whole
// word is folded into a CRC-32 (polynomial 0x04C11DB7, not reflected, word
// least-significant bit first) -- a multiple-input signature register whose
// result is bit-identical to tools/mem_compiler/ecc.py signature() over the
// macro's words in address order.  The controller sweeps every address of the
// macro, so `sig` is the per-instance content signature that
// rom_gen.py personalise writes beside the via map; sig_match compares it with
// exp_sig (the expected signature: a register, a fuse word or a hard-wired
// constant of the personalisation).  sig_busy is high while a fold is pending.
// ---------------------------------------------------------------------------
// Lint waiver: the test and repair buses are sized for the widest macro on the
// shared controller; each collar reads only its own slice (UNUSED on the rest).
// verilator lint_off UNUSED
module ot_mbist_rom_collar #(
    parameter integer WORDS = 1024,
    parameter integer DW    = 72,
    parameter integer AMAX  = 16,
    parameter integer AW    = (WORDS <= 2) ? 1 : $clog2(WORDS)
) (
    input  wire            clk,
    input  wire            rst_n,
    // functional side
    input  wire            f_ce,
    input  wire [AW-1:0]   f_addr,
    output wire [DW-1:0]   f_rd,
    // macro side
    output wire            m_ce,
    output wire [AW-1:0]   m_addr,
    input  wire [DW-1:0]   m_rd,
    // test bus
    input  wire            t_en,
    input  wire            t_clear,
    input  wire            t_req,
    input  wire [AMAX-1:0] t_addr,
    input  wire [31:0]     exp_sig,
    output reg  [31:0]     sig,
    output wire            sig_match,
    output wire            sig_busy
);
    localparam [31:0] POLY = 32'h04C11DB7;

    function automatic [31:0] crc_fold(input [31:0] s, input [DW-1:0] w);
        integer i;
        reg fb;
        begin
            crc_fold = s;
            for (i = 0; i < DW; i = i + 1) begin
                fb = crc_fold[31] ^ w[i];
                crc_fold = {crc_fold[30:0], 1'b0} ^ (fb ? POLY : 32'h0);
            end
        end
    endfunction

    assign m_ce   = t_en ? t_req : f_ce;
    assign m_addr = t_en ? t_addr[AW-1:0] : f_addr;
    assign f_rd   = m_rd;

    reg pend;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pend <= 1'b0;
            sig <= 32'hFFFFFFFF;
        end else begin
            pend <= t_en & t_req;
            if (t_en & t_clear) sig <= 32'hFFFFFFFF;
            else if (pend) sig <= crc_fold(sig, m_rd);
        end
    end
    assign sig_match = (sig == exp_sig);
    assign sig_busy = pend;
endmodule
// verilator lint_on UNUSED
