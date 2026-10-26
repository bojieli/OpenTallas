`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
integer cycle=0,mut=0,checks=0;
initial begin if($value$plusargs("MUT=%d",mut))begin end end
reg [513:0] din0=0; wire [513:0] q0;reg [513:0] h0[0:1];reg [63:0] rng0=64'h123456789abcdef0;
genvar g0; generate for(g0=0;g0<514;g0=g0+1)begin : field0
ot_dp_dly #(.W(1),.D(2)) u(.clk(clk),.d(din0[g0]),.q(q0[g0]));end endgenerate
wire [513:0] check0;
assign check0=q0;
always @(posedge clk) begin : replay0
integer j,b;if(cycle>64)begin
if(check0!==h0[1])begin $display("CB16_FLOW_MISMATCH class=0 W=514 D=2 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=1;j>0;j=j-1)h0[j]=h0[j-1];h0[0]=din0;
for(b=0;b<514;b=b+1)begin rng0=rng0^(rng0<<13);rng0=rng0^(rng0>>7);rng0=rng0^(rng0<<17);din0[b]<=rng0[0];end
din0[512]<=((cycle%11)<7);din0[513]<=((cycle%251)==0);end
reg [513:0] din1=0; wire [513:0] q1;reg [513:0] h1[0:2];reg [63:0] rng1=64'h123456789abcdef1;
genvar g1; generate for(g1=0;g1<514;g1=g1+1)begin : field1
ot_dp_dly #(.W(1),.D(3)) u(.clk(clk),.d(din1[g1]),.q(q1[g1]));end endgenerate
wire [513:0] check1;
assign check1=q1;
always @(posedge clk) begin : replay1
integer j,b;if(cycle>64)begin
if(check1!==h1[2])begin $display("CB16_FLOW_MISMATCH class=1 W=514 D=3 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=2;j>0;j=j-1)h1[j]=h1[j-1];h1[0]=din1;
for(b=0;b<514;b=b+1)begin rng1=rng1^(rng1<<13);rng1=rng1^(rng1>>7);rng1=rng1^(rng1<<17);din1[b]<=rng1[0];end
din1[512]<=((cycle%11)<7);din1[513]<=((cycle%251)==0);end
reg [513:0] din2=0; wire [513:0] q2;reg [513:0] h2[0:9];reg [63:0] rng2=64'h123456789abcdef2;
genvar g2; generate for(g2=0;g2<514;g2=g2+1)begin : field2
ot_dp_dly #(.W(1),.D(10)) u(.clk(clk),.d(din2[g2]),.q(q2[g2]));end endgenerate
wire [513:0] check2;
assign check2=q2;
always @(posedge clk) begin : replay2
integer j,b;if(cycle>64)begin
if(check2!==h2[9])begin $display("CB16_FLOW_MISMATCH class=2 W=514 D=10 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=9;j>0;j=j-1)h2[j]=h2[j-1];h2[0]=din2;
for(b=0;b<514;b=b+1)begin rng2=rng2^(rng2<<13);rng2=rng2^(rng2>>7);rng2=rng2^(rng2<<17);din2[b]<=rng2[0];end
din2[512]<=((cycle%11)<7);din2[513]<=((cycle%251)==0);end
reg [513:0] din3=0; wire [513:0] q3;reg [513:0] h3[0:10];reg [63:0] rng3=64'h123456789abcdef3;
genvar g3; generate for(g3=0;g3<514;g3=g3+1)begin : field3
ot_dp_dly #(.W(1),.D(11)) u(.clk(clk),.d(din3[g3]),.q(q3[g3]));end endgenerate
wire [513:0] check3;
assign check3=q3;
always @(posedge clk) begin : replay3
integer j,b;if(cycle>64)begin
if(check3!==h3[10])begin $display("CB16_FLOW_MISMATCH class=3 W=514 D=11 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=10;j>0;j=j-1)h3[j]=h3[j-1];h3[0]=din3;
for(b=0;b<514;b=b+1)begin rng3=rng3^(rng3<<13);rng3=rng3^(rng3>>7);rng3=rng3^(rng3<<17);din3[b]<=rng3[0];end
din3[512]<=((cycle%11)<7);din3[513]<=((cycle%251)==0);end
reg [513:0] din4=0; wire [513:0] q4;reg [513:0] h4[0:14];reg [63:0] rng4=64'h123456789abcdef4;
genvar g4; generate for(g4=0;g4<514;g4=g4+1)begin : field4
ot_dp_dly #(.W(1),.D(15)) u(.clk(clk),.d(din4[g4]),.q(q4[g4]));end endgenerate
wire [513:0] check4;
assign check4=q4;
always @(posedge clk) begin : replay4
integer j,b;if(cycle>64)begin
if(check4!==h4[14])begin $display("CB16_FLOW_MISMATCH class=4 W=514 D=15 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=14;j>0;j=j-1)h4[j]=h4[j-1];h4[0]=din4;
for(b=0;b<514;b=b+1)begin rng4=rng4^(rng4<<13);rng4=rng4^(rng4>>7);rng4=rng4^(rng4<<17);din4[b]<=rng4[0];end
din4[512]<=((cycle%11)<7);din4[513]<=((cycle%251)==0);end
reg [513:0] din5=0; wire [513:0] q5;reg [513:0] h5[0:15];reg [63:0] rng5=64'h123456789abcdef5;
genvar g5; generate for(g5=0;g5<514;g5=g5+1)begin : field5
ot_dp_dly #(.W(1),.D(16)) u(.clk(clk),.d(din5[g5]),.q(q5[g5]));end endgenerate
wire [513:0] check5;
wire early5;ot_dp_dly #(.W(1),.D(15)) early(.clk(clk),.d(din5[512]),.q(early5));
assign check5={q5[513],(mut==2?early5:q5[512]),q5[511:0]};
always @(posedge clk) begin : replay5
integer j,b;if(cycle>64)begin
if(check5!==h5[15])begin $display("CB16_FLOW_MISMATCH class=5 W=514 D=16 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=15;j>0;j=j-1)h5[j]=h5[j-1];h5[0]=din5;
for(b=0;b<514;b=b+1)begin rng5=rng5^(rng5<<13);rng5=rng5^(rng5>>7);rng5=rng5^(rng5<<17);din5[b]<=rng5[0];end
din5[512]<=((cycle%11)<7);din5[513]<=((cycle%251)==0);end
reg [515:0] din6=0; wire [515:0] q6;reg [515:0] h6[0:0];reg [63:0] rng6=64'h123456789abcdef6;
genvar g6; generate for(g6=0;g6<516;g6=g6+1)begin : field6
ot_dp_dly #(.W(1),.D(1)) u(.clk(clk),.d(din6[g6]),.q(q6[g6]));end endgenerate
wire [515:0] check6;
assign check6=(mut==1)?din6:q6;
always @(posedge clk) begin : replay6
integer j,b;if(cycle>64)begin
if(check6!==h6[0])begin $display("CB16_FLOW_MISMATCH class=6 W=516 D=1 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=0;j>0;j=j-1)h6[j]=h6[j-1];h6[0]=din6;
for(b=0;b<516;b=b+1)begin rng6=rng6^(rng6<<13);rng6=rng6^(rng6>>7);rng6=rng6^(rng6<<17);din6[b]<=rng6[0];end
din6[0]<=((cycle%11)<7);din6[513]<=((cycle%251)==0);end
reg [515:0] din7=0; wire [515:0] q7;reg [515:0] h7[0:1];reg [63:0] rng7=64'h123456789abcdef7;
genvar g7; generate for(g7=0;g7<516;g7=g7+1)begin : field7
ot_dp_dly #(.W(1),.D(2)) u(.clk(clk),.d(din7[g7]),.q(q7[g7]));end endgenerate
wire [515:0] check7;
assign check7=q7;
always @(posedge clk) begin : replay7
integer j,b;if(cycle>64)begin
if(check7!==h7[1])begin $display("CB16_FLOW_MISMATCH class=7 W=516 D=2 cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end
end for(j=1;j>0;j=j-1)h7[j]=h7[j-1];h7[0]=din7;
for(b=0;b<516;b=b+1)begin rng7=rng7^(rng7<<13);rng7=rng7^(rng7>>7);rng7=rng7^(rng7<<17);din7[b]<=rng7[0];end
din7[0]<=((cycle%11)<7);din7[513]<=((cycle%251)==0);end
always @(posedge clk) begin cycle<=cycle+1;if(cycle==4096)begin $display("CB16_PAD_FLOW_PASS cycles=%0d classes=8",cycle);$finish;end end
endmodule
