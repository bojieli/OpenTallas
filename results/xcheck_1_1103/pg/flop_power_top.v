module top(input clk, input d, output q);
  wire n; DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(d), .QN(n)); DLLx1_ASAP7_75t_R l0 (.CLK(clk), .D(n), .Q(q));
endmodule
