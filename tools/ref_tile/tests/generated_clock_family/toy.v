module top(input ck,input other,input d,output q0,output q1,output qo);
 wire trunk,bank,bankleaf;
 BUF b0(.A(ck),.Y(trunk)); BUF b1(.A(trunk),.Y(bank)); BUF b2(.A(bank),.Y(bankleaf));
 FF f0(.CK(trunk),.D(d),.Q(q0)); FF f1(.CK(bankleaf),.D(d),.Q(q1)); FF fo(.CK(other),.D(d),.Q(qo));
endmodule
