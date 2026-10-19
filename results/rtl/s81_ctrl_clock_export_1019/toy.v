module top(input clk,input ckh,input d,output ck_o,output q,output qo);
wire trunk; BUF b0(.A(clk),.Y(trunk)); BUF b1(.A(trunk),.Y(ck_o)); FF f0(.CK(trunk),.D(d),.Q(q)); FF fo(.CK(ckh),.D(d),.Q(qo)); endmodule
