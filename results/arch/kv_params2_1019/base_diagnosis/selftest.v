module p(input clk, input rst_n, input [7:0] d, output reg [7:0] q);
  reg [7:0] r0, r1, r2;
  always @(posedge clk) begin r0 <= d; r1 <= r0; r2 <= r1; end
  always @(posedge clk) q <= rst_n ? r2 : 8'd0;
endmodule
