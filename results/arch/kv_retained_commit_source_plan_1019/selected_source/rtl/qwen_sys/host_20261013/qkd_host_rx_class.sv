`timescale 1ns/1ps
// Full board transport W528: {class4,reserved12,data512}. Independent logical
// receive windows HOST4,CTRL4,INGEST16, alongside physical adapter credits.
// Classes0HOST,1CTRL,2ingCSR,3ingDESC,4ingPAY,7peer TX-credit counts.
// Receiver forwards complete512b ingress beats; no payload bit is sacrificed.
module qkd_host_rx_class #(parameter integer MUT=0,STRAPPED=0)(
 input wire ck,rst_n,input wire[2:0]die_id,input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg host_v,output reg[511:0]host_d,input wire host_cr,
 output reg ctrl_v,output reg[511:0]ctrl_d,input wire ctrl_cr,
 output reg ing_v,output reg[1:0]ing_cls,output reg[511:0]ing_d,input wire[4:0]ing_crn,
 output reg[23:0]credit_return, // [7:0]HOST,[15:8]CTRL,[23:16]INGEST receive capacity freed
 output reg[23:0]peer_credit, // counts returned by board for outgoing HOST/CTRL/INGEST-DONE
 output reg fault
);
 reg[2:0]role;reg rv;reg[527:0]rd;reg hc,cc;reg[4:0]ic;
 reg[5:0]hb,cb,ib;
 wire[3:0]cls=rd[527:524];wire header=rd[523:512]==0;
 wire htake=rv&&header&&cls==0&&!fault&&(!STRAPPED||role==0),ctake=rv&&header&&cls==1&&!fault;
 wire itake=rv&&header&&cls>=2&&cls<=4&&!fault;
 always @(posedge ck)begin rd<=rx_d;host_d<=(MUT==1)?rd[511:0]^512'd1:rd[511:0];ctrl_d<=rd[511:0];ing_d<=rd[511:0];end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin role<=0;rv<=0;hc<=0;cc<=0;ic<=0;hb<=4;cb<=4;ib<=16;
   rx_cr<=0;host_v<=0;ctrl_v<=0;ing_v<=0;ing_cls<=0;credit_return<=0;peer_credit<=0;fault<=0;
  end else begin
   role<=die_id;rv<=rx_v;hc<=host_cr;cc<=ctrl_cr;ic<=ing_crn;rx_cr<=rv;
   host_v<=htake&&hb!=0;ctrl_v<=ctake&&cb!=0;ing_v<=itake&&ib!=0;ing_cls<=(cls[1:0]-2'd2);
   credit_return<={3'd0,ic,7'd0,cc,7'd0,hc};peer_credit<=0;
   hb<=hb+6'(hc)-6'(htake);cb<=cb+6'(cc)-6'(ctake);ib<=ib+6'(ic)-6'(itake);
   if((htake&&hb==0)||(ctake&&cb==0)||(itake&&ib==0)||
      (hc&&!htake&&hb==4)||(cc&&!ctake&&cb==4)||
      ({1'b0,ib}+7'(ic)-7'(itake)>16))fault<=1;
   if(rv&&!fault)begin
    if(!header||(STRAPPED&&cls==0&&role!=0))fault<=1;
    else if(cls==7)begin
     if(rd[511:24]!=0||rd[7:0]>4||rd[15:8]>4||rd[23:16]>4)fault<=1;
     else peer_credit<=rd[23:0];
    end else if(cls>4)fault<=1;
   end
  end
 end
endmodule
