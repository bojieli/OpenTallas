// Conditional adapter: adopt only with a current native B2 clock-contract receipt.
// No data/reset/boot cycle change; HALF and MUT pass through unchanged.
module ot_hidx_score_hcol__oneclk #(parameter integer HALF=0, MUT=0)(
    input wire clk,
    input wire rst_col,
    input wire qv_b,
    input wire [567:0] q_b,
    input wire [543:0] key,
    input wire [31:0] hid4,
    input wire [31:0] cs_in,
    input wire cf_in,
    output wire [31:0] cs_out,
    output wire cf_out,
    output wire [1:0] prdy);
    ot_hidx_score_hcol #(.HALF(HALF),.MUT(MUT)) u_core(
        .clk_pair({2{clk}}),
        .rst_col(rst_col),
        .qv_b(qv_b),
        .q_b(q_b),
        .key(key),
        .hid4(hid4),
        .cs_in(cs_in),
        .cf_in(cf_in),
        .cs_out(cs_out),
        .cf_out(cf_out),
        .prdy(prdy));
endmodule
