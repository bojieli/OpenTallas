`timescale 1ns/1ps
// One PC's real static-port arbitration. Source0 is unchanged landing-strip
// embedding port; source1 is write-only host ingest translated to the identical
// es288 ABI. Four initial credits per source, four scheduler credits overall.
// completion_v/we are ordered physical static-column events delayed WDONE in
// hclk then crossed to ck. Queue-release er259 returns capacity, never ACK.
// Static read returns belong only to embedding (host RMW disabled by QPIPE).
module qkd_host_static_pc_emback_debt #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire[287:0] land_es,output wire[260:0]land_er,
 input wire[287:0]host_es,output reg host_cr,host_ack,land_ack,
 output wire[287:0]ctrl_es,input wire[260:0]ctrl_er,
 input wire completion_v,completion_we,
 output reg fault,output reg queue_quiet
);
 reg[286:0]out_data;reg out_valid;
 reg[257:0]land_data;reg land_valid,land_credit,land_fault;
 assign ctrl_es={out_data,out_valid};
 assign land_er={land_fault,land_credit,land_data,land_valid};
 reg[287:0]a,b;reg[260:0]er;reg ev,ew;
 reg[286:0]q0[0:3],q1[0:3];reg[1:0]w0,r0,w1,r1;reg[2:0]n0,n1,credit;
 reg[63:0]owners,writes;reg[5:0]ow,orr;reg[6:0]on;
 reg rr,selected,pending;reg[286:0]pick;
 // Diagnostic debt only: never controls arbitration or issue. A read WDONE
 // retires the owner entry before its payload can return, so count both.
 reg[7:0]read_debt;
 wire read_accept=a[0]&&!a[286]&&n0<4;
 wire read_retire=land_valid;
 wire queues_empty=n0==0&&n1==0&&!pending;
 wire owners_empty=(MUT==3)||(on==0);
 wire reads_empty=(MUT==4)||(read_debt==0);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin read_debt<=0;queue_quiet<=0;end
  else begin
   case({read_accept,read_retire})
    2'b10:read_debt<=read_debt+1'b1;
    2'b01:read_debt<=read_debt-1'b1;
    default:;
   endcase
   queue_quiet<=queues_empty&&owners_empty&&reads_empty&&credit==4&&
    !out_valid&&!a[0]&&!b[0]&&!land_es[0]&&!host_es[0]&&
    !er[0]&&!er[259]&&!er[260]&&!ctrl_er[0]&&!ctrl_er[259]&&!ctrl_er[260]&&
    !ev&&!completion_v&&!land_valid&&!host_cr&&!host_ack&&!land_ack&&!land_credit&&!fault;
  end
 end
 wire eligible=!fault&&credit!=0&&on<64;
 wire choose=!pending&&!fault&&(n0!=0||n1!=0);
 wire sel=n1!=0&&(n0==0||rr);
 wire launch=pending&&eligible;
 wire pop0=launch&&!selected,pop1=launch&&selected;
 always @(posedge ck)begin
  
  if(a[0]&&n0<4)q0[w0]<=a[287:1];
  if(b[0]&&n1<4)q1[w1]<=b[287:1];
  if(choose)pick<=sel?q1[r1]:q0[r0];
  if(launch)begin owners[ow]<=selected;writes[ow]<=pick[285];out_data<=pick;end
  land_data<=er[258:1];
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   a<=0;b<=0;er<=0;ev<=0;ew<=0;w0<=0;r0<=0;w1<=0;r1<=0;n0<=0;n1<=0;credit<=4;
   ow<=0;orr<=0;on<=0;rr<=0;selected<=0;pending<=0;out_valid<=0;land_valid<=0;land_fault<=0;land_credit<=0;
   host_cr<=0;host_ack<=0;land_ack<=0;fault<=0;
  end else begin
   a<=land_es;b<=host_es;er<=ctrl_er;ev<=completion_v;ew<=completion_we;host_cr<=0;host_ack<=0;land_ack<=0;land_credit<=0;
   land_valid<=er[0];land_fault<=er[260]|fault;out_valid<=launch;
   if(choose)begin selected<=sel;pending<=1;end
   if(launch)begin
    pending<=0;rr<=!selected;ow<=ow+1'b1;
    if(selected)begin r1<=r1+1'b1;host_cr<=1;end else begin r0<=r0+1'b1;land_credit<=1;end
   end
   if(a[0])begin if(n0==4)fault<=1;else w0<=w0+1'b1;end
   if(b[0])begin
    if(n1==4||!b[287]||!b[286])fault<=1;else w1<=w1+1'b1;
   end
   case({a[0]&&n0<4,pop0})2'b10:n0<=n0+1'b1;2'b01:n0<=n0-1'b1;default:;endcase
   case({b[0]&&n1<4,pop1})2'b10:n1<=n1+1'b1;2'b01:n1<=n1-1'b1;default:;endcase
   case({er[259],launch})2'b10:begin if(credit==4)fault<=1;else credit<=credit+1'b1;end
    2'b01:credit<=credit-1'b1;default:;endcase
   if(ev&&!fault)begin
    if(on==0||ew!=writes[orr])fault<=1;
    else begin
     orr<=orr+1'b1;
     host_ack<=ew&&((MUT==1)?!owners[orr]:owners[orr]);
     land_ack<=ew&&!owners[orr];
    end
   end
   case({launch,ev&&!fault&&on!=0&&ew==writes[orr]})2'b10:on<=on+1'b1;2'b01:on<=on-1'b1;default:;endcase
   if(er[260])fault<=1;
   if((read_retire&&!read_accept&&read_debt==0)||(read_accept&&!read_retire&&read_debt==255))fault<=1;
  end
 end
endmodule

