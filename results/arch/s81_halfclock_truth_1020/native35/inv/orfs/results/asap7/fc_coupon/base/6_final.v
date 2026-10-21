module fc_coupon (ck,
    ck_o,
    d,
    q);
 input ck;
 output ck_o;
 input d;
 output q;


 INVx3_ASAP7_75t_R b0 (.A(ck),
    .Y(ck_o));
 DFFHQNx1_ASAP7_75t_R ff (.CLK(ck),
    .D(d),
    .QN(q));
endmodule
