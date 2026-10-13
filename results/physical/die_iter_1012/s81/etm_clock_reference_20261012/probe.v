module probe(input clk); wire [282:0] xa; wire q; dsfd_cfifo cf0 (.cr(clk), .xa(xa), .ri({q,67'b0})); sink r (.ck(clk), .i(xa[86]), .q(q)); endmodule
