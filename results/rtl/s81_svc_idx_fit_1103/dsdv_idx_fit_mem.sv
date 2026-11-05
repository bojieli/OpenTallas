`timescale 1ns/1ps
// S81 svc_lo idx fit (DIE-S81-51/MEM, 2026-11-03): dsdv_idx_rg2_m1k with the master sized to WORDS x BITS.
// Same ports and read/write semantics as dsdv_idx_rg2_m1k (1R1W, registered read on re, write on we). The caller
// guarantees ra / wa < WORDS, or (ring use, WORDS = 128) that every read hits a word written fewer than WORDS writes
// earlier (dsdv_idx_rg3_fit, proof in results/rtl/s81_svc_idx_fit_1103/README.md), and that wd[255:BITS] is
// constant zero, so rd[255:BITS] = 0 equals the 1024x256 form.  Address bits above AW are not used.
module dsdv_idx_fit_mem #(
    parameter bit     SRAM_MACRO = 0,
    parameter integer WORDS = 1024,
    parameter integer BITS = 256
) (
    input  wire         ck,
    input  wire         re,
    input  wire [9:0]   ra,
    output wire [255:0] rd,
    input  wire         we,
    input  wire [9:0]   wa,
    input  wire [255:0] wd
);
    localparam integer AW = WORDS <= 128 ? 7 : WORDS <= 256 ? 8 : 10;
    wire [BITS-1:0] q;
    generate if (BITS < 256) begin : g_pad
        assign rd = {{(256 - BITS){1'b0}}, q};
    end else begin : g_full
        assign rd = q;
    end endgenerate
    generate if (SRAM_MACRO && WORDS == 256 && BITS == 256) begin : g_256x256
        ot_sram_1r1w_256x256_m1_r0c0 u_mem (.clk(ck), .r_ce_in(re), .r_addr_in(ra[7:0]), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa[7:0]), .wd_in(wd[BITS-1:0]), .w_mask_in({BITS{1'b1}}));
    end else if (SRAM_MACRO && WORDS == 768 && BITS == 256) begin : g_768x256
        ot_sram_1r1w_768x256_m2_r0c0 u_mem (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd[BITS-1:0]), .w_mask_in({BITS{1'b1}}));
    end else if (SRAM_MACRO && WORDS == 1024 && BITS == 35) begin : g_1024x35
        ot_sram_1r1w_1024x35_m4_r0c0 u_mem (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd[BITS-1:0]), .w_mask_in({BITS{1'b1}}));
    end else if (SRAM_MACRO && WORDS == 1024 && BITS == 39) begin : g_1024x39
        ot_sram_1r1w_1024x39_m4_r0c0 u_mem (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd[BITS-1:0]), .w_mask_in({BITS{1'b1}}));
    end else if (SRAM_MACRO && WORDS == 128 && BITS == 23) begin : g_128x23
        ot_sram_1r1w_128x23_m1_r0c0 u_mem (.clk(ck), .r_ce_in(re), .r_addr_in(ra[6:0]), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa[6:0]), .wd_in(wd[BITS-1:0]), .w_mask_in({BITS{1'b1}}));
    end else if (SRAM_MACRO) begin : g_1024x256
        // any other size: the original master (wide rd, BITS bits used)
        wire [255:0] q_full;
        ot_sram_1r1w_1024x256_m2_r2c2 u_mem (
            .clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(q_full),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
        assign q = q_full[BITS-1:0];
    end else begin : g_b
        reg [BITS-1:0] mem [0:WORDS-1];
        reg [BITS-1:0] qr;
        always @(posedge ck) begin
            if (we) mem[wa[AW-1:0]] <= wd[BITS-1:0];
            if (re) qr <= mem[ra[AW-1:0]];
        end
        assign q = qr;
    end endgenerate
endmodule
