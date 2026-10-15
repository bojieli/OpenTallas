`timescale 1ns/1ps
module tb_train;
parameter integer MUT=0;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,start=0,payload=0;reg[3:0]count=0;reg[31:0]stride=0;
reg[4424:0]rq[0:2];wire[550:0]rb[0:2];wire[2:0]fault;
generate for(genvar b=0;b<3;b=b+1)begin:g
qfd_res_train_static #(.BAND(b),.MAX_TRAIN(8),.D(2))dut(.ck(ck),.ck_bank({24{ck}}),.rst_n(rst_n),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.rq(rq[b]),.rb(rb[b]),.fault(fault[b]));
end endgenerate
integer c,b,i,j,idx,slot,op,nt,ks,checks=0;reg pay;reg[550:0]want;
initial begin
for(b=0;b<3;b=b+1)rq[b]=0;
repeat(4)@(negedge ck);rst_n=1;
// Exact ordered ROM macro shapes: decoder PCs1,12,16,20; headPC3..6.
for(op=0;op<8;op=op+1)begin
case(op)
0:begin nt=1;ks=64;pay=1;end
1:begin nt=3;ks=16;pay=1;end
2:begin nt=1;ks=256;pay=1;end
3:begin nt=3;ks=48;pay=1;end
4,5,6:begin nt=8;ks=64;pay=0;end
7:begin nt=1;ks=64;pay=0;end
endcase
for(c=0;c<nt*192+8;c=c+1)begin
start=(c==0)||(MUT==3&&c==20);
// Once accepted, live config changes must not alter a single calendar slot.
count=c==0?4'(nt):4'd0;stride=c==0?32'(ks):32'hffffffff;payload=c==0?pay:!pay;
for(b=0;b<3;b=b+1)begin
rq[b]=0;
for(i=0;i<8*nt;i=i+1)if(c==(i/8)*ks+(i%8))begin
rq[b][4424]=!(MUT==1&&i==5);rq[b][4423:4416]=pay?8'hff:8'h00;
for(j=0;j<8;j=j+1)rq[b][552*j+:552]={24'(i*8+j),16'hffff,480'd0,32'(op*100000+b*10000+i*100+j+1)};
end
if(MUT==2&&c==100)rq[b][4424]=1;
if(MUT==4&&c==5&&pay)rq[b][548]=1;
if(MUT==5&&c==5&&!pay)rq[b][4416]=1;
end
@(posedge ck);#1;
for(b=0;b<3;b=b+1)begin
want=0;
if(c>=3)begin idx=(c-3)/24;slot=(c-3)%24-8*b;
if(idx<8*nt&&slot>=0&&slot<8)begin
if(pay)want={1'b1,1'(b==2&&slot==7),1'b0,20'(idx*8+slot),16'hffff,480'd0,32'(op*100000+b*10000+idx*100+slot+1)};
else if(b==2&&slot==7)want={3'b111,548'd0};
end end
if(rb[b]!==want)$fatal(1,"DATA op=%0d c=%0d b=%0d got=%h expected=%h",op,c,b,rb[b],want);
checks=checks+1;
end
@(negedge ck);
end
end
if(fault!==(MUT!=0?3'b111:3'b000))$fatal(1,"FAULT mutant=%0d fault=%b",MUT,fault);
$display("PASS mixed8profiles markermax64 databankmax24 mutant=%0d checks=%0d",MUT,checks);$finish;
end
endmodule
