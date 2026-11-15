module vm_known(input clk, input d, output q1, output q2);
  wire n0, n1a, n1;
  BUFx2_ASAP7_75t_R b0(.A(clk), .Y(n0));
  BUFx2_ASAP7_75t_R b1(.A(n0), .Y(n1a));
  BUFx2_ASAP7_75t_R b2(.A(n1a), .Y(n1));
  DFFHQNx1_ASAP7_75t_R ff_a(.CLK(n0), .D(d), .QN(q1));
  DFFHQNx1_ASAP7_75t_R ff_b(.CLK(n1), .D(d), .QN(q2));
endmodule
