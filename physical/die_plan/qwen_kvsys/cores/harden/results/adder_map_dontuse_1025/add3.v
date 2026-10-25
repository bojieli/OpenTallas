// tiny adder proof design: 3-operand add (full adders) + increment / constant add (half adders: $fa with a 0 input)
module add3 (input clk, input [15:0] a, b, c, output reg [17:0] y, output reg [15:0] z);
  reg [15:0] ar, br, cr;
  always @(posedge clk) begin ar <= a; br <= b; cr <= c; y <= ar + br + cr; z <= ar + 16'd1 + {br[7:0], 8'd0}; end
endmodule
