module hfd_barrier (
    input wire [0:0] ck,
    input wire [63:0] f_cmdproc,
    input wire [0:0] rst,
    output wire [63:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_cmdproc, ^rst};
    reg [63:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {64{lint_in}}; assign t_cmdproc[63:0] = r_t_cmdproc_0;
endmodule
