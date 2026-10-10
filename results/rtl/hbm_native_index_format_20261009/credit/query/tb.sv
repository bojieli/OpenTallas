`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,retained=0,bv=0,qbr=0;reg[72:0]frame=73'h123456;
reg[4:0]head;reg[1:0]bn;reg[1023:0]data;reg[15:0]weight;
wire br,drained,fault;wire[1047:0]qb;
integer sent,got,outstanding,cyc=0,i,round;reg mutant;
ot_hbm_native_index_query_credit #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.retained(retained),.owner_frame(73'h123456),
.block_frame(frame),.owner_rank(7'd17),.block_rank(7'd17),.block_v(bv),.block_r(br),
.block_head(head),.block_number(bn),.block_data(data),.head_weight(weight),.qbr(qbr),
.qb(qb),.drained(drained),.fault(fault));
initial begin
mutant=$test$plusargs("MUT_OWNER");repeat(4)@(negedge clk);por_n=1;
for(round=0;round<2;round=round+1)begin
sent=0;got=0;outstanding=0;@(negedge clk);retained=1;
while((got<128||outstanding!=0)&&cyc<4000)begin
@(negedge clk);cyc=cyc+1;bv=sent<128;head=sent/4;bn=sent%4;weight=sent+31;
for(i=0;i<32;i=i+1)data[32*i+:32]=sent*100+i;
qbr=outstanding!=0&&cyc%7==0;
frame=(mutant&&sent==13)?73'h123457:73'h123456;
@(posedge clk);
if(bv&&br)sent=sent+1;
if(qb[0])begin
if(qb[5:1]!==5'(got/4)||qb[7:6]!==2'(got%4)||qb[1047:1032]!==16'(got+31))$fatal(1,"ORDER");
for(i=0;i<32;i=i+1)if(qb[8+32*i+:32]!==32'(got*100+i))$fatal(1,"DATA");
got=got+1;outstanding=outstanding+1;end
if(qbr)outstanding=outstanding-1;
if(fault)$fatal(1,"OWNER_REJECTED");
end
@(negedge clk);bv=0;qbr=0;repeat(3)@(negedge clk);
if(sent!=128||got!=128||!drained)$fatal(1,"PROTOCOL");
retained=0;repeat(3)@(negedge clk);
end
$display("QUERY_DONE blocks=256 cycles=%0d",cyc);$finish;
end
endmodule
