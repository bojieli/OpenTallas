`timescale 1ns/1ps
module tb_s81ph_gather_strip;
 reg ck=0;always #3 ck=~ck;reg ckv=0;always #4 ckv=~ckv;
 reg rst=0;reg [23:0] ts=0;reg [15:0] cs=0;reg [7:0] rc=0;reg [162:0] tc=0;reg [11:0] fc=0;
 wire [23:0] tso;wire [15:0] cso;wire [7:0] rco;wire [162:0] tco;wire [11:0] fco;
 dsfd_gth_strip u(.ck_r({ckv,{132{ck}}}),.rst(rst),.rsv(rst),.tst_i(ts),.cs_i(cs),.rc_i(rc),.tc_i(tc),.fcd_i(fc),.tst_o(tso),.cs_o(cso),.rc_o(rco),.tc_o(tco),.fcd_o(fco));
 reg [23:0] hts[0:3];reg [15:0] hcs[0:3];reg [7:0] hrc[0:5];reg [162:0] htc;reg [11:0] hfc;
 integer j,errors=0,n=0;
 always @(posedge ckv or negedge rst)if(!rst)hfc<=0;else hfc<=fc;
 always @(posedge ck or negedge rst) begin
  if(!rst)begin for(j=0;j<4;j=j+1)begin hts[j]<=0;hcs[j]<=0;end for(j=0;j<6;j=j+1)hrc[j]<=0;htc<=0;end
  else begin
   hts[0]<=ts;hcs[0]<=cs;hrc[0]<=rc;htc<=tc;
   for(j=1;j<4;j=j+1)begin hts[j]<=hts[j-1];hcs[j]<=hcs[j-1];end
   for(j=1;j<6;j=j+1)hrc[j]<=hrc[j-1];
  end
 end
 always @(posedge ck)begin
  #1;if({tso,cso,rco,tco,fco} !== {hts[3],hcs[3],hrc[5],htc,hfc})begin errors=errors+1;if(errors<5)$display("DELAY MISMATCH sample %0d",n);end
  n=n+1;
 end
 initial begin
  repeat(2)@(negedge ck);rst=1;
  repeat(20000)begin
   @(negedge ck);ts=$random;cs=$random;rc=$random;tc={$random,$random,$random,$random,$random,$random};fc=$random;
   if(n%193==0)rst=0;else rst=1;
  end
  repeat(8)@(negedge ck);
  if(errors==0)$display("STRIP_EXACT PASS %0d samples, tst/cs4 rc6 tc1stream f_cd1serial, async reset",n);
  else begin $display("STRIP_EXACT FAIL %0d errors",errors);$fatal(1,"strip timing mismatch");end
  $finish;
 end
endmodule
