module miter(input[15:0]p0,input[15:0]p1,input[15:0]p2,input[15:0]p3,input[15:0]p4,input[15:0]p5,input[15:0]p6,output correct,mutant_correct);wire[31:0]ref={16'd0,p0}+{8'd0,p1,8'd0}+{p2,16'd0}+{p3[7:0],24'd0}+{8'd0,p4,8'd0}+{p5,16'd0}+{p6[7:0],24'd0};wire[31:0]pb,pc,pd;
actual_pb u_pb(p0,p1,p2,p3,p4,p5,p6,pb);
actual_pc u_pc(p0,p1,p2,p3,p4,p5,p6,pc);
actual_pd u_pd(p0,p1,p2,p3,p4,p5,p6,pd);
assign correct=(pb==ref)&&(pc==ref)&&(pd==ref);assign mutant_correct=((pb^32'h10000)==ref)&&(pc==ref)&&(pd==ref);endmodule
