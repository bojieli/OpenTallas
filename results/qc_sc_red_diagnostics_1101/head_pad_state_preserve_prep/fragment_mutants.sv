// PREP ONLY. All controls must reject under unconstrained initial state.
module head_pad_fragment_mutant #(
    parameter integer MUT = 0
)(input wire ck, start, owe, input wire [13:0] b0, output reg [13:0] o);
    reg [13:0] q;
    generate if (MUT == 1) begin : g_init_zero
        initial q = 14'b0; // NEGATIVE: destroys arbitrary initial padding state.
        always @(posedge ck) if (start | owe) q <= 14'b0;
    end else if (MUT == 2) begin : g_missing_owe
        always @(posedge ck) if (start) q <= 14'b0;
    end else if (MUT == 3) begin : g_clear_one
        always @(posedge ck) if (start | owe) q <= 14'h3fff;
    end else begin : g_wrong_polarity
        always @(posedge ck) if (start | owe) q <= 14'b0;
    end endgenerate
    always @(posedge ck)
        if (start) o <= b0;
        else if (MUT == 0) o <= ~q;
        else o <= q;
endmodule
