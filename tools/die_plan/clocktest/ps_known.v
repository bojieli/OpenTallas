module ps_known(input clk, input d, output q1);
  wire n0, n1a, n1, q0;
  BUFx2_ASAP7_75t_R b0(.A(clk), .Y(n0));
  BUFx2_ASAP7_75t_R b1(.A(n0), .Y(n1a));
  BUFx2_ASAP7_75t_R b2(.A(n1a), .Y(n1));
  DFFHQNx1_ASAP7_75t_R ff_l(.CLK(n0), .D(d), .QN(q0));
  DFFHQNx1_ASAP7_75t_R ff_c(.CLK(n1), .D(q0), .QN(q1));
endmodule
