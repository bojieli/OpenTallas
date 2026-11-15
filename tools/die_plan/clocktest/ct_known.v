module ct_known(input clk, input clk_t1, input clk_c0, input d, output q1, output q2, output q3);
  wire w1;
  DFFHQNx1_ASAP7_75t_R fa(.CLK(clk), .D(d), .QN(w1));
  DFFHQNx1_ASAP7_75t_R fb(.CLK(clk), .D(w1), .QN(q1));
  DFFHQNx1_ASAP7_75t_R fcore(.CLK(clk), .D(w1), .QN(q2));
  DFFHQNx1_ASAP7_75t_R fc(.CLK(clk), .D(w1), .QN(q3));
endmodule
