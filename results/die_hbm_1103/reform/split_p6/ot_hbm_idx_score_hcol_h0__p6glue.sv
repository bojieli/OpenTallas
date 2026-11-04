// DIE-HBM-61/SPLIT d44v part 6 (u_core -> ot_hbm_idx_score_hcol_h0__split); from gen_core_kit_hbm.py (ELEM-HBM): pass-through wrapper, plan pins -> RTL top; wires only.
`default_nettype none
module ot_hbm_idx_score_hcol_h0__fcore (
    input wire cf_in,
    output wire cf_out,
    input wire [1:0] clk_pair,
    input wire [31:0] cs_in,
    output wire [31:0] cs_out,
    input wire [31:0] hid4,
    input wire [543:0] key,
    output wire [1:0] prdy,
    input wire [567:0] q_b,
    input wire qv_b,
    input wire rst_col
);
    ot_hbm_idx_score_hcol_h0__split #(.MUT(0)) u_core (
        .cf_out(cf_out),
        .clk_pair(clk_pair),
        .cs_out(cs_out),
        .hid4(hid4),
        .key(key),
        .prdy(prdy),
        .q_b(q_b),
        .qv_b(qv_b),
        .rst_col(rst_col));
endmodule
`default_nettype wire

// DIE-HBM-61/SPLIT d44v part 6: plan module ot_hbm_idx_score_hcol_h0 = thin parent glue of the split hard core (wires only; the
// sub-cores of ot_hbm_idx_score_hcol_h0__split are the hard cores, each with its own kit face shell).  Ports open in the composition: cf_in, cs_in.
`default_nettype none
module ot_hbm_idx_score_hcol_h0 (
    input wire cf_in,
    output wire cf_out,
    input wire [1:0] clk_pair,
    input wire [31:0] cs_in,
    output wire [31:0] cs_out,
    input wire [31:0] hid4,
    input wire [543:0] key,
    output wire [1:0] prdy,
    input wire [567:0] q_b,
    input wire qv_b,
    input wire rst_col
);
    ot_hbm_idx_score_hcol_h0__fcore u_fcore (.cf_in(cf_in), .cf_out(cf_out), .clk_pair(clk_pair), .cs_in(cs_in), .cs_out(cs_out), .hid4(hid4), .key(key), .prdy(prdy), .q_b(q_b), .qv_b(qv_b), .rst_col(rst_col));
endmodule
`default_nettype wire
