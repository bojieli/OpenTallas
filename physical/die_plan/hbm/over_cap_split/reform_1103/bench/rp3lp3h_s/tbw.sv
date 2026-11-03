`default_nettype none
// DIE-HBM-61/SPLIT rp3lp3h_s bench wrappers: gout split into the leaf-1 lane [49:0] (+7 declared) and the rest (+0).
module tbw_ref_s (input wire ck_s, input wire rst_n, input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2,
    input wire [4:0] xss_g2, input wire [817:0] rin_s, input wire [2068:0] bin, input wire [599:0] sb_bank, input wire [3:0] sb_vld,
    output wire [817:0] rout_s, output wire [49:0] gout_leaf, output wire [149:0] gout_rest);
    wire [199:0] gout;
    hnx_rp3lp3h_s u (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_s(rin_s),
        .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
    assign gout_leaf = gout[49:0]; assign gout_rest = gout[199:50];
endmodule
module tbw_dut_s #(parameter integer MUT = 0) (input wire ck_s, input wire rst_n, input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2,
    input wire [4:0] xss_g2, input wire [817:0] rin_s, input wire [2068:0] bin, input wire [599:0] sb_bank, input wire [3:0] sb_vld,
    output wire [817:0] rout_s, output wire [49:0] gout_leaf, output wire [149:0] gout_rest);
    wire [199:0] gout;
    hnx_rp3lp3h_s__split #(.MUT(MUT)) u (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_s(rin_s),
        .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
    assign gout_leaf = gout[49:0]; assign gout_rest = gout[199:50];
endmodule
`default_nettype wire
