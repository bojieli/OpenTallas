
// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hdc_kadd #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hdc_ksadd_k__u1 #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule
