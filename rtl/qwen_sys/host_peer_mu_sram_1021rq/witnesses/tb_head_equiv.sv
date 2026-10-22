`timescale 1ns/1ps
module tb;
 reg ck=0,rst_n=0,put=0,pop=0;reg[533:0]data;wire[533:0]ho,hn;
 head_old #(.W(534)) uo(.ck(ck),.rst_n(rst_n),.put(put),.pop(pop),.data(data),.head(ho));
 head_new #(.W(534)) un(.ck(ck),.rst_n(rst_n),.put(put),.pop(pop),.data(data),.head(hn));
 integer i,cnt=0,chk=0,hist[0:4];
 always #1 ck=~ck;
 initial begin
  for(i=0;i<5;i=i+1)hist[i]=0;
  data={17{$urandom}};
  repeat(3)@(posedge ck); #0.1 rst_n=1;
  for(i=0;i<400000;i=i+1)begin
   @(negedge ck);
   if(i%50000==7)rst_n=0; else rst_n=1;
   cnt=uo.count[0];
   hist[cnt]=hist[cnt]+1;
   if(rst_n&&cnt!=0)begin chk=chk+1;if(ho!==hn)begin $display("HEADEQ FAIL i=%0d cnt=%0d",i,cnt);$fatal; end end
   put=($urandom%8)<((i/20000)%8); pop=(cnt!=0)&&(($urandom%8)<(((i/20000)+3)%8)); data={17{$urandom}};
  end
  $display("HEADEQ PASS checks=%0d count_hist=%0d/%0d/%0d/%0d/%0d",chk,hist[0],hist[1],hist[2],hist[3],hist[4]);$finish;
 end
endmodule
