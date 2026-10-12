`timescale 1ns/1ps
// dsfd_mtp_hrow_bank: the hardened bank sub-tile of the DSpark main-hidden row store (dsfd_mtp_hrow rev 3, el1011-ds-mtp
// 2026-10-11, owner textbook audit: one clock tree over the 3 mm store -> hardened sub-tiles with local trees and
// registered seams).  One bank = one macro row of a part: 4 x ot_sram_1r1w_1024x256 side by side in bits (1024 rows x
// 1024 b), placed 2 x 2 around a register channel.
//   seam in : every input lands in a pin flop (write {data, addr, enable}, read {addr, enable}); no logic before them
//   macros  : driven only from the pin flops
//   capture : every macro output lands in a capture flop with no logic in front
//   seam out: t_d = {data & valid, valid} from a flop (one AND of the capture flop and its valid, then the out flop)
// Latency: f_r sampled at edge e0 -> macro read at e1 -> capture at e2 -> t_d at e3 (3 cycles); a write sampled at e0
// lands at e1, so a read sampled on the same edge as (or after) a write to the same row returns the written data when
// the macro is write-first, as the flat store (same relative order on both ports).
// Reset: only the two enable flops and the valid pipe (5 flops), from a local reset synchroniser.
module dsfd_mtp_hrow_bank (
    input  wire [0:0]    ck, rst,
    input  wire [1034:0] f_w,               // {wd 1024, wa 10, we}
    input  wire [10:0]   f_r,               // {ra 10, re}
    output wire [1024:0] t_d                // {rd 1024, valid}
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    reg we, re; reg [9:0] wa, ra; reg [1023:0] wd;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin we <= 1'b0; re <= 1'b0; end
        else begin we <= f_w[0]; re <= f_r[0]; end
    always @(posedge ck[0]) begin wa <= f_w[10:1]; wd <= f_w[1034:11]; ra <= f_r[10:1]; end
    wire [1023:0] rdo;
    genvar gc;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck[0]),
            .r_ce_in(re), .r_addr_in(ra), .rd_out(rdo[256*gc +: 256]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd[256*gc +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end endgenerate
    reg [1023:0] cap; reg s1, s2;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin s1 <= 1'b0; s2 <= 1'b0; end
        else begin s1 <= re; s2 <= s1; end
    always @(posedge ck[0]) cap <= rdo;
    reg [1024:0] o;
    always @(posedge ck[0] or negedge rn) if (!rn) o[0] <= 1'b0; else o[0] <= s2;
    always @(posedge ck[0]) o[1024:1] <= cap & {1024{s2}};
    assign t_d = o;
endmodule
