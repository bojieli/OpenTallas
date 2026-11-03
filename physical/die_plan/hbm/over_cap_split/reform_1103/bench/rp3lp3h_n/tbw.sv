`default_nettype none
// DIE-HBM-61/SPLIT rp3lp3h_n bench wrappers: the slot pair N + S (as hnx_rp3lp3x_halves: bin + rst_n to both halves,
// N seam ring -> S landing read).  ref = the two kit cores, dut = the two split compositions.  gout leaf lanes [99:0]
// (leaf 1 local, leaf 0 through the seam) +7 declared; pass lanes gout[199:100], rout_n, rout_s, bout +0.
module tbw_ref_nx (input wire ck_n, input wire ck_s, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    output wire [99:0] gout_leaf, output wire [99:0] gout_pass);
    wire [599:0] sb_bank; wire [3:0] sb_vld; wire [199:0] gout;
    hnx_rp3lp3h_n u_hn (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld));
    hnx_rp3lp3h_s u_hs (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2),
        .rin_s(rin_s), .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
    assign gout_leaf = gout[99:0]; assign gout_pass = gout[199:100];
endmodule
module tbw_dut_nx #(parameter integer MUT = 0) (input wire ck_n, input wire ck_s, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    output wire [99:0] gout_leaf, output wire [99:0] gout_pass);
    wire [599:0] sb_bank; wire [3:0] sb_vld; wire [199:0] gout;
    // MUT applies to the N half only (the S half of the pair stays exact): proves the n split is observed at gout
    hnx_rp3lp3h_n__split #(.MUT(MUT)) u_hn (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld));
    hnx_rp3lp3h_s__split u_hs (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2),
        .rin_s(rin_s), .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
    assign gout_leaf = gout[99:0]; assign gout_pass = gout[199:100];
endmodule
`default_nettype wire
