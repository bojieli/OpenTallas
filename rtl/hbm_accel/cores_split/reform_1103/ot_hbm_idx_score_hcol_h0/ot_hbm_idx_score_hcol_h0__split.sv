`default_nettype none
// DIE-HBM-61/SPLIT 11-03: split composition of ot_hbm_idx_score_hcol_h0 (same ports as the kit core, face-shelled
// form): ra (region 0, clk_pair[0]) + rb (region 1, clk_pair[1]); the sub-blocks are instantiated in their face-shelled
// form (<sub>__fs = facewrap.py model of the kit face shell), so this module is cycle-exact with the hardened
// composition.  cs_in / cf_in of the uncut HALF-0 core were tied 0 by its shell (not pins).
module ot_hbm_idx_score_hcol_h0__split #(parameter integer MUT = 0) (
    output wire cf_out, input wire [1:0] clk_pair, output wire [31:0] cs_out, input wire [31:0] hid4,
    input wire [543:0] key, output wire [1:0] prdy, input wire [567:0] q_b, input wire qv_b, input wire rst_col);
    wire [31:0] cs2; wire cf2;
    ot_hbm_idx_score_hcol_h0_ra__fs #(.MUT(MUT)) u_ra (.clk(clk_pair[0]), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b),
        .key(key), .hid2(hid4[15:0]), .cs_out(cs2), .cf_out(cf2), .prdy(prdy[0]));
    ot_hbm_idx_score_hcol_h0_rb__fs #(.MUT(MUT)) u_rb (.clk(clk_pair[1]), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b),
        .key(key), .hid2(hid4[31:16]), .cs_in(cs2), .cf_in(cf2), .cs_out(cs_out), .cf_out(cf_out), .prdy(prdy[1]));
endmodule
`default_nettype wire
