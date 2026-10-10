`timescale 1ns/1ps
module tb_hbm_index_lines;
reg clk=0,rst_n=0,start=0;always #5 clk=~clk;
reg[8:0]blocks=342;reg[31:0]v=0;reg[383:0]sj=0;reg[8191:0]sd=0;reg[7:0]credit=0;
wire[8791:0]lines;wire[63:0]pop;wire done,fault;
integer nextj[0:31],avail[0:31];integer p,j,b,g,l,got=0,cyc=0,MUT=0;reg endseen=0;
ot_hbm_index_lines #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.start(start),.blocks(blocks),.sector_v(v),.sector_j(sj),.sector_data(sd),.credit(credit),.lines(lines),.pop(pop),.done(done),.fault(fault));
initial begin
if($value$plusargs("mut=%d",MUT))begin end
for(p=0;p<32;p=p+1)begin nextj[p]=0;avail[p]=64;end
repeat(3)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
while(!endseen)begin
 credit=0;v=0;
 for(l=0;l<8;l=l+1)if(lines[l*1099])begin
  if(lines[l*1099+1+:10]!==10'(got+l))$fatal(1,"tag");
  for(b=0;b<136;b=b+1)if(lines[l*1099+11+b*8+:8]!==8'((got+l)*136+b))$fatal(1,"byte line=%0d byte=%0d",got+l,b);
  credit[l]=1;
 end
 if(lines[0])got=got+8;
 for(p=0;p<32;p=p+1)begin
  avail[p]=avail[p]+pop[p*2+:2];
  if(nextj[p]*32+p<5814&&avail[p]>0&&((cyc+p)%7!=0))begin
   j=nextj[p]^1;if(j*32+p>=5814)j=nextj[p];
   v[p]=1;sj[p*12+:12]=j;
   for(b=0;b<32;b=b+1)sd[p*256+b*8+:8]=8'((j*32+p)*32+b);
   if(MUT==1&&p==5&&nextj[p]==2)begin sd[p*256]=~sd[p*256];$display("INJECT");end
   nextj[p]=nextj[p]+1;avail[p]=avail[p]-1;
  end
 end
 if(fault)$fatal(1,"fault");
 endseen=done;cyc=cyc+1;if(cyc>10000)$fatal(1,"timeout got=%0d",got);
 @(negedge clk);
end
if(got!=1368)$fatal(1,"line count got=%0d",got);
$display("PASS_HBM_INDEX_LINES lines=%0d cycles=%0d",got,cyc);$finish;
end
endmodule
