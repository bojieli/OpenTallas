`timescale 1ns/1ps
// One PC's real static-port arbitration. Source0 is unchanged landing-strip
// embedding port; source1 is write-only host ingest translated to the identical
// es288 ABI. Four initial credits per source, four scheduler credits overall.
// completion_v/we are ordered physical static-column events delayed WDONE in
// hclk then crossed to ck. Queue-release er259 returns capacity, never ACK.
// Static read returns belong only to embedding (host RMW disabled by QPIPE).
module qkd_host_static_pc #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire[287:0] land_es,output wire[260:0]land_er,
 input wire[287:0]host_es,output reg host_cr,host_ack,
 output wire[287:0]ctrl_es,input wire[260:0]ctrl_er,
 input wire completion_v,completion_we,
 output reg fault
);
 reg[286:0]out_data;reg out_valid;
 reg[257:0]land_data;reg land_valid,land_credit,land_fault;
 assign ctrl_es={out_data,out_valid};
 assign land_er={land_fault,land_credit,land_data,land_valid};
 reg[287:0]a,b;reg[260:0]er;reg ev,ew;
 reg[286:0]q0[0:3],q1[0:3];reg[1:0]w0,r0,w1,r1;reg[2:0]n0,n1,credit;
 reg[63:0]owners,writes;reg[5:0]ow,orr;reg[6:0]on;
 reg rr,selected,pending;reg[286:0]pick;
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
   host_cr<=0;host_ack<=0;fault<=0;
  end else begin
   a<=land_es;b<=host_es;er<=ctrl_er;ev<=completion_v;ew<=completion_we;host_cr<=0;host_ack<=0;land_credit<=0;
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
    end
   end
   case({launch,ev&&!fault&&on!=0&&ew==writes[orr]})2'b10:on<=on+1'b1;2'b01:on<=on-1'b1;default:;endcase
   if(er[260])fault<=1;
  end
 end
endmodule

// Lives inside a separately named controller variant, beside its actual col_v,
// col_we,col_sr signals. Static RD events track ordering; their delayed event
// is not called a read completion. Static WR is acknowledged at the existing
// JEDEC controller WDONE deadline, identical to native KV write completion.
module qkd_ctrl_static_commit #(parameter integer WDONE=17,MUT=0)(
 input wire hclk,hrst_n,ck,rst_n,
 input wire col_v,col_we,col_sr,
 output reg completion_v,completion_we,output wire fault
);
 reg[WDONE-1:0]pv,pw;
 always @(posedge hclk or negedge hrst_n)begin
  if(!hrst_n)begin pv<=0;pw<=0;end
  else begin pv<={pv[WDONE-2:0],col_v&&col_sr};pw<={pw[WDONE-2:0],col_we};end
 end
 wire ready,valid,ov;wire[0:0]data;
 ot_async_fifo #(.WIDTH(1),.DEPTH(8))events(
  .wr_clk(hclk),.wr_rst_n(hrst_n),.wr_valid(pv[WDONE-1]),.wr_ready(ready),.wr_data(pw[WDONE-1]),.wr_overflow(ov),
  .rd_clk(ck),.rd_rst_n(rst_n),.rd_valid(valid),.rd_ready(1'b1),.rd_data(data),.rd_underflow());
 reg hf;(* async_reg="true" *)reg[1:0]fs;
 always @(posedge hclk or negedge hrst_n)if(!hrst_n)hf<=0;else if(pv[WDONE-1]&&!ready)hf<=1;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin completion_v<=0;completion_we<=0;fs<=0;end
  else begin completion_v<=valid;completion_we<=(MUT!=0)?!data[0]:data[0];fs<={fs[0],hf|ov};end
 end
 assign fault=fs[1];
endmodule
