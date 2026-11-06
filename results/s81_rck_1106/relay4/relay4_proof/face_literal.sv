module ot_pl_pad #(
    parameter integer W = 1,
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_reg
        reg [W-1:0] r [0:N-1];
        integer j;
        always @(posedge ck) begin
            r[0] <= d;
            for (j = 1; j < N; j = j + 1) r[j] <= r[j - 1];
        end
        assign q = r[N-1];
    end endgenerate
endmodule
