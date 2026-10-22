module fc_coupon(input ck,input d,output ck_o,output q); wire a,b; AND2x2_ASAP7_75t_R b0(.A(ck),.B(d),.Y(ck_o)); DFFHQNx1_ASAP7_75t_R ff(.CLK(ck),.D(d),.QN(q)); endmodule
