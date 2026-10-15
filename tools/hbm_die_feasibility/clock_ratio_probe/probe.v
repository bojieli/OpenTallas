module ratio_probe(input c,input v,output q_c,output q_v,output q_cn,output q_n);
 wire vn;
 INVx1_ASAP7_75t_R u_inv(.A(v),.Y(vn));
 DFFHQNx1_ASAP7_75t_R u_c(.CLK(c),.D(q_v),.QN(q_c));
 DFFHQNx1_ASAP7_75t_R u_v(.CLK(v),.D(q_c),.QN(q_v));
 DFFHQNx1_ASAP7_75t_R u_cn(.CLK(c),.D(q_n),.QN(q_cn));
 DFFHQNx1_ASAP7_75t_R u_n(.CLK(vn),.D(q_cn),.QN(q_n));
endmodule
