module shared_d_proof(input wire ck,input wire d0,input wire d1,output wire equal);
wire q0_0;
DFFHQNx1_ASAP7_75t_R ff0_0(.CLK(ck),.D(d0),.QN(q0_0));
wire q0_1;
DFFHQNx1_ASAP7_75t_R ff0_1(.CLK(ck),.D(d0),.QN(q0_1));
wire q1_0;
DFFHQNx1_ASAP7_75t_R ff1_0(.CLK(ck),.D(d1),.QN(q1_0));
wire q1_1;
DFFHQNx1_ASAP7_75t_R ff1_1(.CLK(ck),.D(d1),.QN(q1_1));
assign equal=(q0_0==q0_1) & (q1_0==q1_1);
endmodule
