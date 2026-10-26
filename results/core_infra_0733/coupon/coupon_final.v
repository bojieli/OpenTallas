module coupon (ck,
    rst_n,
    d,
    q,
    mp_isl0_ck_i,
    mp_isl0_ck_o,
    mp_isl0_rst_i,
    mp_isl0_rst_o);
 input ck;
 input rst_n;
 input [3:0] d;
 output [3:0] q;
 input mp_isl0_ck_i;
 output mp_isl0_ck_o;
 input mp_isl0_rst_i;
 output mp_isl0_rst_o;

 wire ci_root_out;
 wire ci_w_out;
 wire ci_e_out;

 BUFx8_ASAP7_75t_R ci_e (.A(ci_root_out),
    .Y(ci_e_out));
 BUFx16f_ASAP7_75t_R ci_root (.A(ck),
    .Y(ci_root_out));
 BUFx8_ASAP7_75t_R ci_w (.A(ci_root_out),
    .Y(ci_w_out));
 DFFHQNx1_ASAP7_75t_R f0 (.CLK(ci_w_out),
    .D(d[0]),
    .QN(q[0]));
 DFFHQNx1_ASAP7_75t_R f1 (.CLK(ci_w_out),
    .D(d[1]),
    .QN(q[1]));
 DFFHQNx1_ASAP7_75t_R f2 (.CLK(ci_e_out),
    .D(d[2]),
    .QN(q[2]));
 DFFHQNx1_ASAP7_75t_R f3 (.CLK(ci_e_out),
    .D(d[3]),
    .QN(q[3]));
 BUFx16f_ASAP7_75t_R mp_isl0_ck0 (.A(mp_isl0_ck_i),
    .Y(mp_isl0_ck_o));
 BUFx4_ASAP7_75t_R mp_isl0_rst0 (.A(mp_isl0_rst_i),
    .Y(mp_isl0_rst_o));
endmodule
