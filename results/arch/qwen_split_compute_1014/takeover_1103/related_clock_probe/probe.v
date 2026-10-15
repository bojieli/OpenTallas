module probe(input ck,output q); wire a,b,c; A a0(.ck(ck),.d(c),.q(a)); B b0(.ck(ck),.d(a),.q(b)); C c0(.ck(ck),.d(b),.q(c)); assign q=c; endmodule
