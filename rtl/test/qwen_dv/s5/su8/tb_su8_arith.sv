module proof(input wire [23:0] a,b,input wire ci,output wire mismatch);
wire [23:0] y;wire [23:0] scaled [0:7]; wire [7:0] bad;
qfd_dv_su8_add u (.a(a),.b(b),.ci(ci),.y(y));
genvar k;generate for(k=0;k<8;k=k+1)begin:g
qfd_dv_su8_stride #(.K(k)) u (.x(a),.y(scaled[k]));
assign bad[k]=scaled[k]!=(24'(k*a));
end endgenerate
assign mismatch=(y!=24'(a+b+ci))||(|bad);
endmodule
