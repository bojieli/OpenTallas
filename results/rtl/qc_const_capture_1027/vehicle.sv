module plain(input clk, output reg [23:0] q); always @(posedge clk) q <= 0; endmodule
module wirekeep(input clk, output wire [23:0] q); (* keep=1 *) reg [23:0] r; always @(posedge clk) r <= 0; assign q=r; endmodule
module processkeep(input clk, output reg [23:0] q); (* keep=1 *) always @(posedge clk) q <= 0; endmodule
module bothkeep(input clk, output wire [23:0] q); (* keep=1 *) reg [23:0] r; (* keep=1 *) always @(posedge clk) r <= 0; assign q=r; endmodule
