`timescale 1ns/1ps
// ot_sram_dline (el1011-s81su, 2026-10-12): a fixed D-cycle delay line of W-bit words held in 1R1W SRAM macros
// (ot_sram_1r1w_64x512_m1_r2c2, ceil(W / 512) side by side) instead of W x D flops: q(t) = d(t - D), cycle-exact,
// for every cycle (a pure delay; validity travels on the caller's own reset line).  The macro is written every cycle
// at wp and read at rp = wp - (D - 2) (the read is registered in the macro), then the read word is captured in a
// flop right at the macro output (no logic before it) -> D = (D - 2) array cycles + macro read + capture.
// D in [3, 64].  Pointers are the only reset state; the data path has none.
module ot_sram_dline #(
    parameter integer W = 1024,
    parameter integer D = 11
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer NM = (W + 511) / 512;
`ifndef SYNTHESIS
    initial if (D < 3 || D > 64) $fatal(1, "ot_sram_dline: D must be in [3, 64]");
`endif
    reg [5:0] wp, rp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 6'd0; rp <= 6'd0 - (D - 2); end
        else begin wp <= wp + 6'd1; rp <= rp + 6'd1; end
    wire [NM*512-1:0] wd = {{(NM*512-W){1'b0}}, d};
    wire [NM*512-1:0] rq;
    reg  [NM*512-1:0] cq;                                  // capture flops at the macro outputs
    always @(posedge clk) cq <= rq;
    assign q = cq[W-1:0];
    genvar m;
    generate for (m = 0; m < NM; m = m + 1) begin : g_m
        ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rp), .rd_out(rq[512*m +: 512]),
            .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(wd[512*m +: 512]), .w_mask_in({512{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate
endmodule
