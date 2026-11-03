module t(input clk, input d, output q);
  wire n0, n1, n2;
  DFFHQNx1_ASAP7_75t_R a(.CLK(clk), .D(d), .QN(n0));
  DLLx1_ASAP7_75t_R L(.CLK(clk), .D(n0), .Q(n1));
  DFFHQNx1_ASAP7_75t_R b(.CLK(clk), .D(n1), .QN(q));
endmodule
