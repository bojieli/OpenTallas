module top(input pll_ref,d,shared_rx,output q,z,z0,z1,z2);
wire core_ck,fdi_ck,rx0_ck,rx1_ck,rx2_ck,c,padding,rx0_unused;
BUFx4_ASAP7_75t_R core_gen(.A(pll_ref),.Y(core_ck));
BUFx4_ASAP7_75t_R fdi_gen(.A(pll_ref),.Y(fdi_ck));
BUFx4_ASAP7_75t_R rx0_gen(.A(pll_ref),.Y(rx0_ck));
BUFx4_ASAP7_75t_R rx1_gen(.A(pll_ref),.Y(rx1_ck));
BUFx4_ASAP7_75t_R rx2_gen(.A(pll_ref),.Y(rx2_ck));
DFFHQNx1_ASAP7_75t_R core_launch(.CLK(core_ck),.D(d),.QN(c));
DFFHQNx1_ASAP7_75t_R fdi_capture(.CLK(fdi_ck),.D(c),.QN(q));
DFFHQNx1_ASAP7_75t_R core_capture(.CLK(core_ck),.D(q),.QN(z));
DFFHQNx1_ASAP7_75t_R rx0_capture(.CLK(rx0_ck),.D(q),.QN(z0));
DFFHQNx1_ASAP7_75t_R rx0_input(.CLK(rx0_ck),.D(shared_rx),.QN(rx0_unused));
DFFHQNx1_ASAP7_75t_R rx1_capture(.CLK(rx1_ck),.D(shared_rx),.QN(z1));
DFFHQNx1_ASAP7_75t_R rx2_capture(.CLK(rx2_ck),.D(shared_rx),.QN(z2));
DFFHQNx1_ASAP7_75t_R padding_fault(.CLK(fdi_ck),.D(shared_rx),.QN(padding));
endmodule
