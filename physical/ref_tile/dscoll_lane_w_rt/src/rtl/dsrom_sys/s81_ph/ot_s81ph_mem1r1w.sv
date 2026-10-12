`timescale 1ns/1ps
// ot_s81ph_mem1r1w (CLAUDE S81-PH collective, 2026-10-06): a 1R1W array with a REGISTERED read port
// (q <= mem[ra] when re; q holds otherwise; a same-cycle write to ra returns the OLD word -- callers forward).
// SRAM = 0: flops.  SRAM = 1: ceil(W/128) x ot_sram_1r1w_512x128_m4_r2c2 (DEPTH <= 512; the macro's read data is
// registered inside the macro and holds while r_ce is low, so both builds have the same cycle behaviour).
module ot_s81ph_mem1r1w #(
    parameter integer W = 64,
    parameter integer DEPTH = 16,
    parameter integer SRAM = 0,
    parameter integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1
) (
    input  wire          clk,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    input  wire          re,
    input  wire [AW-1:0] ra,
    output wire [W-1:0]  q
);
    generate if (SRAM == 0) begin : g_ff
        reg [W-1:0] mem [0:DEPTH-1];
        reg [W-1:0] q_r;
        always @(posedge clk) begin
            if (we) mem[wa] <= wd;
            if (re) q_r <= mem[ra];
        end
        assign q = q_r;
    end else begin : g_sram
        localparam integer NT = (W + 127) / 128;
        wire [NT*128-1:0] wdp = {{(NT*128-W){1'b0}}, wd};
        wire [NT*128-1:0] qp;
        wire [8:0] wa9 = {{(9-AW){1'b0}}, wa};
        wire [8:0] ra9 = {{(9-AW){1'b0}}, ra};
        genvar t;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            ot_sram_1r1w_512x128_m4_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra9), .rd_out(qp[t*128 +: 128]),
                .w_ce_in(we), .w_addr_in(wa9), .wd_in(wdp[t*128 +: 128]), .w_mask_in({128{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
        end
        assign q = qp[W-1:0];
`ifndef SYNTHESIS
        initial if (DEPTH > 512) $fatal(1, "ot_s81ph_mem1r1w: SRAM depth %0d > 512", DEPTH);
`endif
    end endgenerate
endmodule
