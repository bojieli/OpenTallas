// bench only: signed master models = core + its seam face flop (ra: cs/cf out face, rb: cs/cf in face)
module ot_hbm_idx_score_hcol_h0_ra (input wire clk, input wire rst_col, input wire qv_b, input wire [567:0] q_b,
    input wire [543:0] key, input wire [15:0] hid2, output reg [31:0] cs_out, output reg cf_out, output wire prdy);
    wire [31:0] c; wire f;
    ot_hbm_idx_score_hcol_h0_ra__core u (.clk(clk), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key), .hid2(hid2), .cs_out(c), .cf_out(f), .prdy(prdy));
    always @(posedge clk) begin cs_out <= c; cf_out <= f; end
endmodule
module ot_hbm_idx_score_hcol_h0_rb (input wire clk, input wire rst_col, input wire qv_b, input wire [567:0] q_b,
    input wire [543:0] key, input wire [15:0] hid2, input wire [31:0] cs_in, input wire cf_in, output wire [31:0] cs_out, output wire cf_out, output wire prdy);
    reg [31:0] c; reg f;
    always @(posedge clk) begin c <= cs_in; f <= cf_in; end
    ot_hbm_idx_score_hcol_h0_rb__core u (.clk(clk), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key), .hid2(hid2), .cs_in(c), .cf_in(f), .cs_out(cs_out), .cf_out(cf_out), .prdy(prdy));
endmodule
