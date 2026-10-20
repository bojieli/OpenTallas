module top(input [3:0] xk, input [3:0] d, output [3:0] xok);
cf u_cf(.C0(xk[0]),.D0(d[0]),.C1(xk[1]),.D1(d[1]),.C2(xk[2]),.D2(d[2]),.C3(xk[3]),.D3(d[3]));
relay u_xo0(.CK(xk[0] ),.D(d[0]),.CKO(xok[0]));
relay u_xo1(.CK(xk[1] ),.D(d[1]),.CKO(xok[1]));
relay u_xo2(.CK(xk[2] ),.D(d[2]),.CKO(xok[2]));
relay u_xo3(.CK(xk[3] ),.D(d[3]),.CKO(xok[3]));
sink s0(.CK(xok[0]),.D(d[0]));
sink s1(.CK(xok[1]),.D(d[1]));
sink s2(.CK(xok[2]),.D(d[2]));
sink s3(.CK(xok[3]),.D(d[3]));
endmodule
