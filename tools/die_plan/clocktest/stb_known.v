module stb_known(input clk, input d, output q1, output q2, output q3);
  wire n0, ninv;
  BUFx2_ASAP7_75t_R b0(.A(clk), .Y(n0));
  INVx2_ASAP7_75t_R i1(.A(n0), .Y(ninv));
  DFFHQNx1_ASAP7_75t_R ff_a(.CLK(n0), .D(d), .QN(q1));
  DFFHQNx1_ASAP7_75t_R ff_b(.CLK(n0), .D(d), .QN(q2));
  DFFHQNx1_ASAP7_75t_R ff_c(.CLK(ninv), .D(d), .QN(q3));
endmodule
