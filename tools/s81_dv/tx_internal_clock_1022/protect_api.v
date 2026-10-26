module protect_api(input ck,output y);
wire c;
BUFx24_ASAP7_75t_R u_ck(.A(ck),.Y(c));
BUFx2_ASAP7_75t_R u_sink(.A(c),.Y(y));
endmodule
