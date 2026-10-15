`timescale 1ns/1ps
module tb_train;
parameter integer STRIDE=16,MUT=0;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,start=0;reg[4424:0]rq[0:2];wire[550:0]rb[0:2];wire[2:0]fault;
generate for(genvar b=0;b<3;b=b+1)begin:g
qfd_res_train_static #(.BAND(b),.NTRAIN(3),.STRIDE(STRIDE),.D(2))dut(.ck(ck),.ck_bank({24{ck}}),.rst_n(rst_n),.train_start(start),.rq(rq[b]),.rb(rb[b]),.fault(fault[b]));
end endgenerate
integer c,b,i,j,idx,slot,checks=0;reg expected;reg[550:0]want;
initial begin
for(b=0;b<3;b=b+1)rq[b]=0;
repeat(4)@(negedge ck);rst_n=1;
for(c=0;c<585;c=c+1)begin
start=(c==0)||(MUT==3&&c==20);
for(b=0;b<3;b=b+1)begin
rq[b]=0;
for(i=0;i<24;i=i+1)if(c==(i/8)*STRIDE+(i%8))begin
rq[b][4424]=!(MUT==1&&i==13);rq[b][4423:4416]=8'hff;
for(j=0;j<8;j=j+1)rq[b][552*j+:552]={24'(i*8+j),16'hffff,480'd0,32'(b*10000+i*100+j+1)};
end
if(MUT==2&&c==100)rq[b][4424]=1;
if(MUT==4&&c==5)rq[b][548]=1;
end
@(posedge ck);#1;
for(b=0;b<3;b=b+1)begin
want=0;
if(c>=3)begin idx=(c-3)/24;slot=(c-3)%24-8*b;
if(idx<24&&slot>=0&&slot<8)want={1'b1,1'(b==2&&slot==7),1'b0,20'(idx*8+slot),16'hffff,480'd0,32'(b*10000+idx*100+slot+1)};
end
if(rb[b]!==want)$fatal(1,"DATA c=%0d b=%0d got=%h expected=%h",c,b,rb[b],want);
checks=checks+1;
end
@(negedge ck);
end
if(fault!==(MUT!=0?3'b111:3'b000))$fatal(1,"FAULT mutant=%0d fault=%b",MUT,fault);
$display("PASS fixed24bank strain stride=%0d mutant_missing=%0d checks=%0d",STRIDE,MUT,checks);$finish;
end
endmodule
