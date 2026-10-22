module coupon(input CLK,D,RESETN,SETN,output A,Q); DFFASRHQNx1_ASAP7_75t_R a(.CLK(CLK),.D(D),.RESETN(RESETN),.SETN(SETN),.QN(A)); DFFHQNx1_ASAP7_75t_R q(.CLK(CLK),.D(D),.QN(Q)); endmodule
