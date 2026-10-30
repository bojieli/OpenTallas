module bridge_top(input wire clk,input wire[255:0]d,d2,output wire[255:0]q,q2);
genvar t;generate for(t=0;t<8;t=t+1)begin:g
 ot_s81sl_ve_dly #(.W(32),.D(4*t),.MUT(0)) u(clk,d[32*t+:32],d2[32*t+:32],q[32*t+:32],q2[32*t+:32]);
end endgenerate
endmodule
