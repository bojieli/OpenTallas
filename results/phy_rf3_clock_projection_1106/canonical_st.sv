module ot_dp_st #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output reg  [W-1:0] q,
    output reg          eq
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
