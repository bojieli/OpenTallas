module fc_coupon (clk_in,
    clk_out,
    d,
    q);
 input clk_in;
 output clk_out;
 input d;
 output q;


 BUFx4_ASAP7_75t_R b0 (.A(clk_in),
    .Y(clk_out));
 DFFHQNx1_ASAP7_75t_R ff (.CLK(clk_in),
    .D(d),
    .QN(q));
endmodule
