module fc_coupon (ck,
    ck_o,
    d,
    q);
 input ck;
 output ck_o;
 input d;
 output q;


 AND2x2_ASAP7_75t_R b0 (.A(ck),
    .B(d),
    .Y(ck_o));
 DFFHQNx1_ASAP7_75t_R ff (.CLK(ck),
    .D(d),
    .QN(q));
endmodule
