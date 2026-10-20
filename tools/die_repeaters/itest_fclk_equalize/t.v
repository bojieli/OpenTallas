module t (ck, din);
  input ck, din;
  wire q, d, n_a_fck;
  DFFHQNx1_ASAP7_75t_R src (.CLK(ck), .D(din), .QN(d));
  BUFx8_ASAP7_75t_R fwd (.A(ck), .Y(n_a_fck));
  DFFHQNx1_ASAP7_75t_R cap (.CLK(n_a_fck), .D(d), .QN(q));
endmodule
