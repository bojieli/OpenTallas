module hr_undef_tiny(input [0:0] ck, input [3:0] d, output reg [3:0] q, output reg z);
  always @(posedge ck) begin
    q <= d;
    z <= q[0];
  end
endmodule
