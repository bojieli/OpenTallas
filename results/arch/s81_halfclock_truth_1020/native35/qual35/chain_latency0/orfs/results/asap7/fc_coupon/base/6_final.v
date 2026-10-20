module fc_coupon (ck,
    ck_o,
    d,
    q);
 input ck;
 output ck_o;
 input d;
 output q;

 wire a;
 wire b;

 BUFx4_ASAP7_75t_R b0 (.A(ck),
    .Y(a));
 BUFx2_ASAP7_75t_R b1 (.A(b),
    .Y(ck_o));
 DFFHQNx1_ASAP7_75t_R ff (.CLK(ck),
    .D(d),
    .QN(q));
 INVx3_ASAP7_75t_R inv (.A(a),
    .Y(b));
endmodule
