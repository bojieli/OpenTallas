`timescale 1ns/1ps
module tb_qfd_b2_serializer;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;
 reg [4424:0] rq[0:2];
 wire [550:0] rb[0:2],hb[0:5];
 wire [2:0] fault;wire [5:0] hf;
 generate for(genvar b=0;b<3;b=b+1) begin:g_b
  qfd_res_ser_static #(.BAND(b)) u_old(.ck(ck),.rst_n(rst_n),.me_en(1'b1),.rq(rq[b]),.rb(rb[b]),.fault(fault[b]));
  for(genvar h=0;h<2;h=h+1) begin:g_h
   wire [2212:0] r={rq[b][4424],rq[b][4416+4*h+:4],rq[b][2208*h+:2208]};
   qfd_res_ser_half_b2 #(.HB(2*b+h),.MUT((b==0 && h==0)?MUT:0)) u_new
    (.ck(ck),.rst_n(rst_n),.me_en(1'b1),.rq(r),.rb(hb[2*b+h]),.fault(hf[2*b+h]));
  end
 end endgenerate
 integer n,b,s,beats=0,ends=0,active;reg [550:0] oldword,newword;reg[31:0]v;
 initial begin
  for(b=0;b<3;b=b+1)rq[b]=0;
  repeat(3)@(negedge ck);rst_n=1;
  for(n=0;n<24*64+50;n=n+1)begin
   oldword=0;newword=0;active=0;
   for(b=0;b<3;b=b+1) if(rb[b][550])oldword=oldword|rb[b];
   for(b=0;b<6;b=b+1)if(hb[b][550])begin newword=newword|hb[b];active=active+1;end
   if(active>1 || oldword!==newword)$fatal(1,"calendar edge%0d old%h new%h active%0d",n,oldword,newword,active);
   if(newword[550])beats=beats+1;if(newword[549])ends=ends+1;
   if((|fault)||(|hf))$fatal(1,"unexpected schedule fault");
   for(b=0;b<3;b=b+1)begin
    rq[b]=0;
    if(n<24*64 && n%24==0)begin
     for(s=0;s<8;s=s+1)begin
      v=32'(n*31+b*8+s+1);
      rq[b][552*s+:552]={24'(b*8+s),16'(v),{16{v}}};
      rq[b][4416+s]=(n/24+s)%3!=0;
     end
     rq[b][4424]=1;
    end
   end
   @(negedge ck);
  end
  if(ends!=64 || beats<900)$fatal(1,"vacuous beats%0d ends%0d",beats,ends);
  $display("PASS b2 serializer exact old calendar, 64 bursts, %0d beats, %0d ends, six sources disjoint",beats,ends);$finish;
 end
endmodule
