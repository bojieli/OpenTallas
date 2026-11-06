module tiny(input clk,input d,input t,output o);
wire q;
DFFHQNx1_ASAP7_75t_R ff0(.CLK(clk),.D(d),.QN(q));
DFFHQNx1_ASAP7_75t_R ff1(.CLK(clk),.D(q),.QN(o));
endmodule
