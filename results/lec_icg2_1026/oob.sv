module oob(input clk, input [7:0] a0, a1, a2, a3, a4, input [2:0] s_in, input we, input [2:0] wa, output reg [7:0] y);
  reg [7:0] rg [0:4];
  reg [2:0] s;
  always @(posedge clk) begin
    rg[0] <= a0; rg[1] <= a1; rg[2] <= a2; rg[3] <= a3; rg[4] <= a4;
    s <= s_in;
    y <= rg[s];
  end
endmodule
