`timescale 1ps/1fs
`default_nettype none
// Finite full-TP96 merge of actual published ascending native candidate lists.
// Provider reads must come from checked TU publication storage. No sorting of
// host operands, relabelling IDs, implied ACK or delay-derived publication.
// strip-protect 2026-10-09 (REVIEW_20261009 S4/X3): PROTECT=0 (default) removes the rejected flop-level protection;
// PROTECT=1 is the original, bit for bit.  Fault-free behaviour is identical (physical/strip_protect/bench.py).
module ot_hbm_index_global_order #(parameter integer ENABLE=0,STATIC_SCAN=0,PROTECT=0)(
 input wire clk,por_n,start,output wire start_r,
 input wire [72:0] start_frame,input wire publication_complete,
 input wire owner_valid,input wire [72:0] owner_frame,
 output wire read_v,input wire read_r,output wire [72:0] read_frame,
 output wire [6:0] read_rank,output wire [16:0] read_ordinal,
 input wire rsp_v,output wire rsp_r,input wire [72:0] rsp_frame,
 input wire [6:0] rsp_rank,input wire [16:0] rsp_ordinal,
 input wire [33:0] rsp_tuple,input wire rsp_last,rsp_empty,
 output wire out_v,input wire out_r,output wire [33:0] out_tuple,
 output wire [72:0] out_frame,output wire [6:0] out_rank,
 output wire retained,output wire done,output wire fault
);
 localparam [3:0] IDLE=0,INITREQ=1,INITWAIT=2,SETTLE=3,EMIT=4,
                  REFILLREQ=5,REFILLWAIT=6,DONE=7,FAULT=8;
 reg [72:0] frame,frame_n;
 reg [3:0] state,state_n;
 reg [6:0] rank,rank_n;
 reg [3:0] wait_edges,wait_edges_n;
 reg [16:0] previous,previous_n;reg previous_v,previous_v_n;
 reg [17:0] scan_block,scan_block_n;reg [6:0] scan_rank,scan_rank_n;
 reg [33:0] head[0:95],head_n[0:95];
 reg [16:0] ordinal[0:95],ordinal_n[0:95];
 reg [95:0] valid,valid_n,last,last_n;
 // Nodes contain {valid,rank7,id17}. Each level registers its predecessor.
 wire [24:0] tree[0:95],tree_n[0:95];
 function automatic [24:0] lower(input [24:0] a,b);
  begin lower=!a[24]?b:!b[24]?a:
    (a[16:0]<b[16:0]||(a[16:0]==b[16:0]&&a[23:17]<b[23:17]))?a:b;end
 endfunction
 wire [24:0] winner=STATIC_SCAN?{valid[scan_rank],scan_rank,head[scan_rank][33:17]}:tree[95];
 wire [6:0] selected=winner[23:17];
 reg codes_ok;
 integer i;
 always @*begin
  codes_ok=frame_n==~frame&&state_n==~state&&rank_n==~rank&&
   wait_edges_n==~wait_edges&&previous_n==~previous&&previous_v_n==~previous_v&&
   valid_n==~valid&&last_n==~last&&scan_block_n==~scan_block&&scan_rank_n==~scan_rank;
  for(integer c=0;c<96;c=c+1)
   codes_ok=codes_ok&&(head_n[c]==~head[c])&&(ordinal_n[c]==~ordinal[c])&&
                         (tree_n[c]==~tree[c]);
  if(PROTECT==0)codes_ok=1'b1; // complemented head/valid/tree mirrors only when PROTECT
 end
 wire lease_ok=owner_valid&&owner_frame==frame;
 wire enabled=ENABLE&&codes_ok&&state!=FAULT;
 assign start_r=enabled&&state==IDLE&&publication_complete&&owner_valid;
 assign read_v=enabled&&lease_ok&&(state==INITREQ||state==REFILLREQ);
 assign read_frame=frame;assign read_rank=rank;assign read_ordinal=ordinal[rank];
 wire response_match=(state==INITWAIT||state==REFILLWAIT)&&rsp_frame==frame&&
                     rsp_rank==rank&&rsp_ordinal==ordinal[rank];
 assign rsp_r=enabled&&lease_ok&&response_match;
 assign out_v=enabled&&lease_ok&&state==EMIT&&winner[24]&&selected<96;
 assign out_tuple=selected<96?head[selected]:34'd0;
 assign out_frame=frame;assign out_rank=selected;
 assign retained=ENABLE&&state!=IDLE;
 assign done=enabled&&lease_ok&&state==DONE;
 assign fault=ENABLE&&(!codes_ok||state==FAULT);
 generate if(!STATIC_SCAN)begin:g_tournament
 for(genvar l=0;l<7;l=l+1)begin:g_level
  localparam integer NI=(96+(1<<l)-1)>>l;
  localparam integer NO=(NI+1)>>1;
  localparam integer BASE=(l==0)?0:(l==1)?48:(l==2)?72:(l==3)?84:(l==4)?90:(l==5)?93:95;
  localparam integer PRE=(l==1)?0:(l==2)?48:(l==3)?72:(l==4)?84:(l==5)?90:93;
  for(genvar n=0;n<NO;n=n+1)begin:g_node
   reg [24:0] node_q,node_q_n;
   assign tree[BASE+n]=node_q;assign tree_n[BASE+n]=node_q_n;
   wire [24:0] a,b,choice;
   if(l==0)begin:leaves
    assign a={valid[2*n],7'(2*n),head[2*n][33:17]};
    assign b={valid[2*n+1],7'(2*n+1),head[2*n+1][33:17]};
   end else begin:interior
    assign a=tree[PRE+2*n];
    if(2*n+1<NI)assign b=tree[PRE+2*n+1];else assign b=25'd0;
   end
   assign choice=lower(a,b);
   always @(posedge clk or negedge por_n)begin
    if(!por_n)begin node_q<=0;node_q_n<=25'h1ffffff;end
    else begin node_q<=choice;node_q_n<=~choice;end
   end
  end
 end
 end else begin:g_static
  for(genvar n=0;n<96;n=n+1)begin:g_unused_tree
   assign tree[n]=25'd0;assign tree_n[n]=25'h1ffffff;
  end
 end endgenerate
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   frame<=0;frame_n<=~73'd0;state<=IDLE;state_n<=~IDLE;
   rank<=0;rank_n<=~7'd0;wait_edges<=0;wait_edges_n<=~4'd0;
   previous<=0;previous_n<=~17'd0;previous_v<=0;previous_v_n<=1;
   scan_block<=0;scan_block_n<=~18'd0;scan_rank<=0;scan_rank_n<=~7'd0;
   valid<=0;valid_n<=~96'd0;last<=0;last_n<=~96'd0;
   for(i=0;i<96;i=i+1)begin head[i]<=0;head_n[i]<=~34'd0;
    ordinal[i]<=0;ordinal_n[i]<=~17'd0;end
  end else if(ENABLE)begin
   if(!codes_ok||(state!=IDLE&&!lease_ok)||(rsp_v&&!response_match))begin
    state<=FAULT;state_n<=~FAULT;
   end else case(state)
    IDLE:if(start&&start_r)begin
     if(start_frame!=owner_frame)begin state<=FAULT;state_n<=~FAULT;end
     else begin frame<=start_frame;frame_n<=~start_frame;rank<=0;rank_n<=~7'd0;
      valid<=0;valid_n<=~96'd0;previous_v<=0;previous_v_n<=1;
      scan_block<=0;scan_block_n<=~18'd0;scan_rank<=0;scan_rank_n<=~7'd0;
      for(i=0;i<96;i=i+1)begin ordinal[i]<=0;ordinal_n[i]<=~17'd0;end
      state<=INITREQ;state_n<=~INITREQ;end
    end
    INITREQ:if(read_v&&read_r)begin state<=INITWAIT;state_n<=~INITWAIT;end
    REFILLREQ:if(read_v&&read_r)begin state<=REFILLWAIT;state_n<=~REFILLWAIT;end
    INITWAIT,REFILLWAIT:if(rsp_v&&rsp_r)begin
     if((rsp_empty&&!rsp_last)||(!rsp_empty&&rsp_tuple[0]&&(
          (rsp_tuple[15:8]==8'hff&&|rsp_tuple[7:1])||
          (rsp_tuple[33:17]%17'd96!=rank)||
          (rsp_tuple[33:17]>frame[72:56])||
          (previous_v&&rsp_tuple[33:17]<=previous))))begin
      state<=FAULT;state_n<=~FAULT;
     end else if(!rsp_empty&&!rsp_tuple[0]&&!rsp_last)begin
      // Explicit invalid slots (including quarter padding) consume actual
      // storage ordinals. They neither terminate a rank nor become candidates.
      if(ordinal[rank]==1379)begin state<=FAULT;state_n<=~FAULT;end
      else begin ordinal[rank]<=ordinal[rank]+1'b1;ordinal_n[rank]<=~(ordinal[rank]+1'b1);
       state<=(state==INITWAIT)?INITREQ:REFILLREQ;
       state_n<=~((state==INITWAIT)?INITREQ:REFILLREQ);end
     end else begin
      head[rank]<=rsp_tuple;head_n[rank]<=~rsp_tuple;
      valid[rank]<=!rsp_empty&&rsp_tuple[0];valid_n[rank]<=rsp_empty||!rsp_tuple[0];
      last[rank]<=rsp_last;last_n[rank]<=!rsp_last;
      if(state==INITWAIT&&rank!=95)begin rank<=rank+1'b1;rank_n<=~(rank+1'b1);
       state<=INITREQ;state_n<=~INITREQ;end
      else begin wait_edges<=7;wait_edges_n<=~4'd7;state<=SETTLE;state_n<=~SETTLE;end
     end
    end
    SETTLE:if(STATIC_SCAN)begin
      if(scan_block>{1'b0,frame[72:56]})begin state<=DONE;state_n<=~DONE;end
      else if(winner[24]&&{1'b0,winner[16:0]}<scan_block)begin state<=FAULT;state_n<=~FAULT;end
      else if(winner[24]&&{1'b0,winner[16:0]}==scan_block)begin state<=EMIT;state_n<=~EMIT;end
      else begin scan_block<=scan_block+1'b1;scan_block_n<=~(scan_block+1'b1);
       scan_rank<=(scan_rank==95)?7'd0:scan_rank+1'b1;
       scan_rank_n<=~((scan_rank==95)?7'd0:scan_rank+1'b1);end
     end else if(wait_edges!=0)begin wait_edges<=wait_edges-1'b1;
     wait_edges_n<=~(wait_edges-1'b1);end
     else if(!winner[24])begin state<=DONE;state_n<=~DONE;end
     else if(selected>=96||(previous_v&&winner[16:0]<=previous))begin state<=FAULT;state_n<=~FAULT;end
     else begin state<=EMIT;state_n<=~EMIT;end
    EMIT:if(out_v&&out_r)begin
     if(STATIC_SCAN)begin scan_block<=scan_block+1'b1;scan_block_n<=~(scan_block+1'b1);
      scan_rank<=(scan_rank==95)?7'd0:scan_rank+1'b1;
      scan_rank_n<=~((scan_rank==95)?7'd0:scan_rank+1'b1);end
     previous<=winner[16:0];previous_n<=~winner[16:0];previous_v<=1;previous_v_n<=0;
     valid[selected]<=0;valid_n[selected]<=1;
     if(last[selected])begin wait_edges<=7;wait_edges_n<=~4'd7;state<=SETTLE;state_n<=~SETTLE;end
     else if(ordinal[selected]==1379)begin state<=FAULT;state_n<=~FAULT;end
     else begin rank<=selected;rank_n<=~selected;ordinal[selected]<=ordinal[selected]+1'b1;
      ordinal_n[selected]<=~(ordinal[selected]+1'b1);state<=REFILLREQ;state_n<=~REFILLREQ;end
    end
    DONE:begin state<=IDLE;state_n<=~IDLE;end
    FAULT:begin state<=FAULT;state_n<=~FAULT;end
    default:begin state<=FAULT;state_n<=~FAULT;end
   endcase
  end
 end
endmodule
`default_nettype wire
