
// ge = (a >= b), unsigned
module ot_hdc_kge #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hdc_ksadd_k__u1 #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule
