// DIE-HBM-62/BIG d44v part 7: plan module hnx_rp3lp3h_n = thin parent glue of the split hard core (wires only; each sub-core
// carries its own kit face shell).  Physical sub-core paths: <inst>.u_fcore.u_core.<u_sub>.
`default_nettype none
module hnx_rp3lp3h_n__fcore (
    input wire ck_n, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout, output wire [599:0] sb_bank, output wire [3:0] sb_vld);
    hnx_rp3lp3h_n__p7comp u_core (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld));
endmodule
module hnx_rp3lp3h_n (
    input wire ck_n, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout, output wire [599:0] sb_bank, output wire [3:0] sb_vld);
    hnx_rp3lp3h_n__fcore u_fcore (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld));
endmodule
`default_nettype wire
