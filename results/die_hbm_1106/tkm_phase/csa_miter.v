module csa_miter(input [7:0]rank,pf,f8,gbpf,output bad);
wire [7:0]a,b;
candidate plain(.rank(rank),.gb(8'd0),.pf(pf),.f8(f8),.gbpf(gbpf),.o(a));
candidate_csa prefix(.rank(rank),.gb(8'd0),.pf(pf),.f8(f8),.gbpf(gbpf),.o(b));
assign bad=| (a^b);
endmodule
