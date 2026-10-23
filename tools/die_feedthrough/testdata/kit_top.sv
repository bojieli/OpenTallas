// synthetic kit top for pushdown tests (ANSI header with a parameter list)
module blk_m #(
    parameter INSTANCE = "blk",
    parameter integer MUT = 0
) (
    input wire rst_n,
    input wire [15:0] x, xk2,  // continuation item
    input wire ck_r0,
    output wire [15:0] xo,
    output wire [3:0] xok
);
    reg [15:0] r;
    always @(posedge ck_r0 or negedge rst_n) if (!rst_n) r <= 16'd0; else r <= x ^ xk2;
    assign xo = r;
    assign xok = r[3:0];
endmodule
