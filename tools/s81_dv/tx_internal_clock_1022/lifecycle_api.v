module lifecycle_api(input ck,output ya,output yb);
wire ca,cb;
BUFx24_ASAP7_75t_R u_ck_a(.A(ck),.Y(ca));
BUFx24_ASAP7_75t_R u_ck_b(.A(ck),.Y(cb));
INVx1_ASAP7_75t_R u_sink_a(.A(ca),.Y(ya));
INVx1_ASAP7_75t_R u_sink_b(.A(cb),.Y(yb));
endmodule
