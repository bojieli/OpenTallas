module hfd_gath_r8 (
    output wire [539:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^rst, ^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule
