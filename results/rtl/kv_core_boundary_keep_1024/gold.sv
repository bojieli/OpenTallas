module G #(parameter integer W = 1, parameter integer D = 1, parameter integer RST = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    generate if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n)
            if (!rst_n) for (i = 0; i < D; i = i + 1) r[i] <= {W{1'b0}};
            else begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    end else begin : g_n
        always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    end endgenerate
    assign q = r[D-1];
endmodule