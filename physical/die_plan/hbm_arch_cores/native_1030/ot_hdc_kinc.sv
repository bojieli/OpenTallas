
// y = a + inc (mod 2^W)
module ot_hdc_kinc #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hdc_inc_k #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule
