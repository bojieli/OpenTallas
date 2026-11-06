`default_nettype none
// HBM-FORM-SPLIT-13-OPSB 11-06: narrow-macro bank for ot_hgi_sfu_opsb_output (opt-in, define OT_OPSB_N32 in
// ot_hgi_su_lgroup2_lf).  Same ports and the same one-edge read contract as ot_hgi_su_lbank RB = 11 (MACRO = 1), but the
// 2,048 x 32-bit words sit in ONE 32-bit-wide macro (ot_sram_1r1w_2048x32_m8_r0c0_g32, 92.664 x 43.752, 92 pins) instead of
// 256 rows x 256 bits (ot_sram_1r1w_256x256_m2_r2c2, 172.824 x 41.064, 823 pins: wd {8{wd}}, a 256-bit lane mask and an
// 8:1 read mux on ks).  Word wa / ra is the same word in both forms; the read port holds rd while re = 0 and reads the old
// word on a same-edge write, exactly like the row form (whose ks register only moves on re).  LAT is the behavioural
// bench mutant of ot_hgi_su_lbank, kept so the instance line is identical.
module ot_hgi_su_lbank_n32 #(
    parameter integer RB = 11,
    parameter integer MACRO = 1,
    parameter integer LAT = 0
) (
    input  wire          clk,
    input  wire          re,
    input  wire [RB-1:0] ra,
    output wire [31:0]   rd,
    input  wire          we,
    input  wire [RB-1:0] wa,
    input  wire [31:0]   wd
);
    generate if (MACRO && RB == 11) begin : g_m11n
        ot_sram_1r1w_2048x32_m8_r0c0_g32 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in(1'b1));
    end else begin : g_lb
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(re), .ra(ra), .rd(rd),
            .we(we), .wa(wa), .wd(wd));
    end endgenerate
endmodule
`default_nettype wire
