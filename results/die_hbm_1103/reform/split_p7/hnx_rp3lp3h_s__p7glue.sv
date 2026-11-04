// DIE-HBM-62/BIG d44v part 7: plan module hnx_rp3lp3h_s = thin parent glue of the split hard core (wires only; each sub-core
// carries its own kit face shell).  Physical sub-core paths: <inst>.u_fcore.u_core.<u_sub>.
`default_nettype none
module hnx_rp3lp3h_s__fcore (
    input wire ck_s, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_s, input wire [2068:0] bin, input wire [599:0] sb_bank, input wire [3:0] sb_vld,
    output wire [817:0] rout_s, output wire [199:0] gout);
    hnx_rp3lp3h_s__p7comp u_core (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_s(rin_s), .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
endmodule
module hnx_rp3lp3h_s (
    input wire ck_s, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_s, input wire [2068:0] bin, input wire [599:0] sb_bank, input wire [3:0] sb_vld,
    output wire [817:0] rout_s, output wire [199:0] gout);
    hnx_rp3lp3h_s__fcore u_fcore (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_s(rin_s), .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld), .rout_s(rout_s), .gout(gout));
endmodule
`default_nettype wire
