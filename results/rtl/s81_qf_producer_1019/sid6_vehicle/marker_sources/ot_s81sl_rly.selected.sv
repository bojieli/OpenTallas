module ot_s81sl_rly #(parameter integer W = 1, parameter integer D = 1) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (D == 0) begin : g0 assign q = d; end
    else begin : gd
        reg [W-1:0] r [0:D-1];
        integer i;
        always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i - 1]; end
        assign q = r[D-1];
    end endgenerate
endmodule
