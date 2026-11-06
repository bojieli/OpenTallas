module off32_old(input clk,input[31:0]iteration,input[15:0]step,output reg[31:0]off32);
reg[31:0]aq;reg[15:0]bq;wire[15:0]p0,p1,p2,p3,p4,p5,p6;reg[15:0]q0,q1,q2,q3,q4,q5,q6;wire[31:0]z;
base2 a(aq,bq,p0,p1,p2,p3,p4,p5,p6);base3 b(q0,q1,q2,q3,q4,q5,q6,z);
always@(posedge clk)begin aq<=iteration;bq<=step;q0<=p0;q1<=p1;q2<=p2;q3<=p3;q4<=p4;q5<=p5;q6<=p6;off32<=z;end
endmodule

module off32_split(input clk,input[31:0]iteration,input[15:0]step,output reg[31:0]off32);
wire[7:0]p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16,p17,p18,p19,p20,p21,p22,p23,p24,p25;reg[7:0]q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22,q23,q24,q25;wire[31:0]z;
new1 a(iteration,step,p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16,p17,p18,p19,p20,p21,p22,p23,p24,p25);always@(posedge clk)begin q0<=p0;q1<=p1;q2<=p2;q3<=p3;q4<=p4;q5<=p5;q6<=p6;q7<=p7;q8<=p8;q9<=p9;q10<=p10;q11<=p11;q12<=p12;q13<=p13;q14<=p14;q15<=p15;q16<=p16;q17<=p17;q18<=p18;q19<=p19;q20<=p20;q21<=p21;q22<=p22;q23<=p23;q24<=p24;q25<=p25;end
wire[15:0]lo,h0,h1;wire carry;reg[15:0]lq,hq0,hq1;reg cq;split2 b(q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22,q23,q24,q25,lo,h0,h1,carry);split3 c(lq,hq0,hq1,cq,z);always@(posedge clk)begin lq<=lo;hq0<=h0;hq1<=h1;cq<=carry;off32<=z;end
endmodule

module off32_pure(input clk,input[31:0]iteration,input[15:0]step,output reg[31:0]off32);
wire[7:0]p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16,p17,p18,p19,p20,p21,p22,p23,p24,p25;reg[7:0]q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22,q23,q24,q25;wire[31:0]z;
new1 a(iteration,step,p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16,p17,p18,p19,p20,p21,p22,p23,p24,p25);always@(posedge clk)begin q0<=p0;q1<=p1;q2<=p2;q3<=p3;q4<=p4;q5<=p5;q6<=p6;q7<=p7;q8<=p8;q9<=p9;q10<=p10;q11<=p11;q12<=p12;q13<=p13;q14<=p14;q15<=p15;q16<=p16;q17<=p17;q18<=p18;q19<=p19;q20<=p20;q21<=p21;q22<=p22;q23<=p23;q24<=p24;q25<=p25;end
wire[31:0]x,y;reg[31:0]xq,yq;pure2 b(q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22,q23,q24,q25,x,y);pure3 c(xq,yq,z);always@(posedge clk)begin xq<=x;yq<=y;off32<=z;end
endmodule
