// Smallest context containing a real source launch register, the actual ring,
// and the original receiving partition boundary register. This checks the
// additional three cycles rather than just the isolated ring's write latency.
module tb_dp_clk_landing #(parameter bit WNEG = 0) (
    input wire fclk, clk, rst_n,
    input wire [31:0] d,
    output reg [31:0] q,
    output wire ready, fault
);
    reg [31:0] source_q;
    wire [31:0] landed;
    always @(posedge fclk) source_q <= d;
    ot_dp_clk_landing #(.W(32), .WNEG(WNEG)) u_landing (
        .fclk(fclk), .clk(clk), .rst_n(rst_n), .d(source_q), .q(landed),
        .ready(ready), .fault(fault));
    always @(posedge clk) q <= landed;
endmodule
