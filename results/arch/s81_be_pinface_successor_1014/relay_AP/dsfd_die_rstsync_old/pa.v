module pa_top();
  wire n0_0;
  wire n0_1;
  wire n0_2;
  dsfd_die_rstsync u0 (.ck(n0_0), .rn(n0_1), .rst(n0_2));
  wire n1_0;
  wire n1_1;
  wire n1_2;
  dsfd_die_rstsync u1 (.ck(n1_0), .rn(n1_1), .rst(n1_2));
  wire n2_0;
  wire n2_1;
  wire n2_2;
  dsfd_die_rstsync u2 (.ck(n2_0), .rn(n2_1), .rst(n2_2));
  wire n3_0;
  wire n3_1;
  wire n3_2;
  dsfd_die_rstsync u3 (.ck(n3_0), .rn(n3_1), .rst(n3_2));
endmodule
