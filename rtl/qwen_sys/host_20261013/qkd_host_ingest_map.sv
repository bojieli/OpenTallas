`timescale 1ns/1ps
// Production KV and embedding sector map. See original qkd_ctrl_pc wj/wrow
// and ot_qfd_emb_pkg.emb_loc; logical PC is preserved for local lpc strap.
// Eight input word credits initially; returns after registered decode is emitted.
// Output per stack is {data256,row19,col5,bank5,lpc5,v}291, four initial
// downstream credits per logical PC. End marker66 is held until real commit count reaches
// all previously emitted sectors. Host QPIPE is write-only; RMW faults.
module qkd_host_ingest_map #(parameter integer MUT=0,ORDERED=0,BOOT_SCRATCH_ROW=0)(
 input wire ck,rst_n,
 input wire[289:0]ing,output reg ing_cr,
 output reg[1163:0]out,input wire[127:0]out_cr,
 input wire[7:0]ack_n,
 output reg marker_v,output reg[65:0]marker,input wire marker_cr,
 output reg fault,output reg[31:0]issued,landed,
 input wire ord_cr,output reg issue_v,output reg[6:0]issue_pc
);
 reg[289:0]iq;reg[127:0]crq;reg[7:0]aq;reg mcq,ocq;reg[8:0]ord_credit;
 reg[289:0]q[0:7];reg[2:0]wp,rp;reg[3:0]count;
 wire pending=count!=0;wire[289:0]word=q[rp];
 wire[31:0]addr=word[33:2];wire we=word[1];wire[255:0]data=word[289:34];
 reg[2:0]credits[0:127];reg marker_credit;
 reg[1:0]stack;reg[4:0]pc,bank,col;reg[18:0]row;reg good;
 reg[24:0]e,s;reg[17:0]t;reg[9:0]p,j;reg[16:0]sec;
 always @*begin
  e=addr[24:0];s=e-25'd19447808;t=18'(e>>7);p=0;j=0;sec=addr[23:7];
  stack=addr[6:5];pc=addr[4:0];bank=0;col=0;row=0;good=we&&addr!=32'hffffffff;
  if(!addr[31])begin
   // address31=0, local sector17=a23:7; high address bits and dummy t13
   // must be zero at CTX8192. j excludes the map's dummy bit7.
   sec=addr[23:7];j={sec[10:8],sec[6:0]};bank={j[9:7],j[1:0]};col=j[6:2];row=19'd64+{13'd0,sec[16:11]};
   good=good&&addr[30:24]==0&&!sec[7]&&sec[16:11]<36;
  end else begin
   good=good&&addr[30:25]==0&&e<25'd19457304;
   if(e<25'd19447808)begin stack=e[6:5];pc=e[4:0];p=t[9:0];row=19'd24427+{11'd0,t[17:10]};end
   else begin stack=s[6:5];pc=s[4:0];p=10'd384+10'(s[13:7]);row=19'd24575;end
   bank={p[9:7],p[1:0]};col=p[6:2];
  end
  // Cold boot checker owns this scratch row on all PCs. Even a future address
  // map revision must fail closed if a payload aliases its reserved storage.
  good=good&&(row!=BOOT_SCRATCH_ROW);
  if(MUT==1)bank=bank^5'd1;
 end
 wire mark=pending&&addr==32'hffffffff&&we;
 wire emit=pending&&good&&!fault&&credits[{stack,pc}]!=0&&(!ORDERED||ord_credit!=0);
 wire emit_marker=mark&&!fault&&issued==landed&&marker_credit;
 wire[32:0]sum={1'b0,landed}+33'(aq);
 wire[127:0]credit_overflow;
 for(genvar k=0;k<128;k++)begin:g_credit
  wire spend=emit&&{stack,pc}==7'(k);
  assign credit_overflow[k]=crq[k]&&credits[k]==4&&!spend;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)credits[k]<=4;
   else case({crq[k],spend})
    2'b10:if(credits[k]<4)credits[k]<=credits[k]+1'b1;
    2'b01:credits[k]<=credits[k]-1'b1;default:;
   endcase
  end
 end
 always @(posedge ck)if(iq[0]&&count<8)q[wp]<=iq;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   iq<=0;crq<=0;aq<=0;mcq<=0;wp<=0;rp<=0;count<=0;out<=0;ing_cr<=0;marker_v<=0;marker<=0;
   fault<=0;issued<=0;landed<=0;marker_credit<=1;ocq<=0;ord_credit<=256;issue_v<=0;issue_pc<=0;

  end else begin
   iq<=ing;ocq<=ord_cr;issue_v<=emit;issue_pc<={stack,pc};
   if(ORDERED)case({ocq,emit})2'b10:begin if(ord_credit==256)fault<=1;else ord_credit<=ord_credit+1'b1;end 2'b01:ord_credit<=ord_credit-1'b1;default:;endcase
   crq<=out_cr;aq<=ack_n;mcq<=marker_cr;ing_cr<=0;marker_v<=0;
   for(integer k=0;k<4;k++)out[k*291]<=0;
   if(|credit_overflow)fault<=1;
   if(sum[32]||sum[31:0]>issued)fault<=1;else landed<=sum[31:0];
   if(iq[0]&&!fault)begin if(count==8)fault<=1;else wp<=wp+1'b1;end
   if(emit||emit_marker)rp<=rp+1'b1;
   case({iq[0]&&!fault&&count<8,emit||emit_marker})
    2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(pending&&!good&&!mark)fault<=1;
   if(emit)begin
    out[stack*291+:291]<={data,row,col,bank,pc,1'b1};
    issued<=issued+1'b1;if(issued==32'hffffffff)fault<=1;ing_cr<=1;
   end
   if(mcq)begin if(marker_credit)fault<=1;else marker_credit<=1;end
   if(emit_marker)begin marker_v<=1;marker<=word[99:34];ing_cr<=1;marker_credit<=0;end
  end
 end
endmodule
