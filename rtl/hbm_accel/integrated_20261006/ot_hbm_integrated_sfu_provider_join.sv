`timescale 1ns/1ps
`default_nettype none
// One protected 1024-bit landing seat; existing SU CAP1 provider, no new RAM.
// Model: hbm_integrated_sfu_provider_join_model. Single operation, not four-op SU.
module ot_hbm_integrated_sfu_provider_join #(parameter integer ENABLE=0,NATIVE_VM_PUBLICATION=0)(
 input wire clk,por_n,warm_req,output wire warm_ack,
 input wire enroll_v,output wire enroll_r,input wire [72:0] enroll_frame,
 input wire [31:0] enroll_pc,enroll_op,input wire [15:0] enroll_source,
 input wire [8:0] enroll_expert,input wire enroll_matrix,
 input wire [11:0] enroll_row,input wire [8:0] enroll_count,
 // Actual accepted allocation is supplied by caller; never derive an allocation
 // from payload addresses. All addresses BYTE units, both vectors exactly256B.
 input wire allocation_valid,input wire [72:0] allocation_frame,
 input wire [31:0] source_addr,dest_addr,source_base,source_limit,dest_base,dest_limit,
 input wire [2:0] fn,input wire [31:0] local_tag,
 input wire owner_valid,input wire [72:0] owner_frame,
 input wire grant,output wire lease_v,quiet,release_v,input wire release_r,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp,
 // Native mode replaces CP result writes with the existing VM publisher.
 output wire native_enroll_v,input wire native_enroll_r,
 output wire native_tx_v,input wire native_tx_r,output wire [1023:0] native_tx_d,
 output wire [72:0] native_tx_owner,output wire [3:0] native_tx_index,output wire native_tx_last,
 input wire native_publication_done,native_complete_v,native_fault,
 input wire [72:0] native_complete_frame,input wire [31:0] native_complete_tag,
 output wire native_complete_r,native_producer_drained,
 output wire publication_v,input wire publication_r,input wire [72:0] publication_owner,
 output wire [72:0] held_frame,output wire retained,fault,ce,due
);
 generate if(!ENABLE)begin:g_off
 assign native_enroll_v=0;assign native_tx_v=0;assign native_tx_d=0;
 assign native_tx_owner=0;assign native_tx_index=0;assign native_tx_last=0;
 assign native_complete_r=0;assign native_producer_drained=1;
 assign warm_ack=0;assign enroll_r=0;assign lease_v=0;assign quiet=1;assign release_v=0;
 assign req_v=0;assign req=0;assign rsp_r=0;assign publication_v=0;
 assign held_frame=0;assign retained=0;assign fault=0;assign ce=0;assign due=0;
 end else begin:g_on
 localparam [3:0] EMPTY=0,LEASE=1,RREQ=2,RRSP=3,RX=4,TX=5,
                   WREQ=6,WRSP=7,VREQ=8,VRSP=9,DRAIN=10;
 // Layout payload1024,addresses192,tag32,fn3,phase4,sector2,beat2,bad1 =1260 bits.
 wire [1259:0] q;reg [1259:0] n;wire good,io_ce,io_due;
 wire [3:0] phase=q[1254:1251];wire [1:0] sector=q[1256:1255],beat=q[1258:1257];
 wire [31:0] src=q[1055:1024],dst=q[1087:1056],tag=q[1247:1216];
 wire [2:0] op_fn=q[1250:1248];
 wire stage_enroll_r,stage_retained,stage_fault,stage_ce,stage_due,stage_issued;
 wire rx_r,tx_v,tx_last,complete_v;wire [1023:0] tx_d;wire [72:0] tx_owner;
 wire [3:0] tx_index;wire [31:0] held_pc,held_op;
 wire [31:0] address=(phase==RREQ||phase==RRSP)?src+32'(beat)*128+32'(sector)*32:
                             dst+32'(beat)*128+32'(sector)*32;
 wire [15:0] request_tag={12'hcf0,beat,sector};
 wire live_owner=owner_valid&&owner_frame==held_frame;
 wire checked_allocation=allocation_valid&&allocation_frame==enroll_frame&&
   source_addr[4:0]==0&&dest_addr[4:0]==0&&source_addr>=source_base&&dest_addr>=dest_base&&
   ({1'b0,source_addr}+33'd256)<={1'b0,source_limit}&&
   ({1'b0,dest_addr}+33'd256)<={1'b0,dest_limit};
 wire native_match=native_complete_frame==held_frame&&native_complete_tag==tag;
 wire io_bad=q[1259]||io_due||(NATIVE_VM_PUBLICATION&&native_fault);
 assign fault=io_bad||stage_fault||(retained&&!live_owner);
 assign ce=io_ce||stage_ce;assign due=io_due||stage_due;
 assign retained=stage_retained||phase!=EMPTY||!good;
 assign enroll_r=stage_enroll_r&&good&&phase==EMPTY&&checked_allocation&&!warm_req&&(!NATIVE_VM_PUBLICATION||(native_enroll_r&&dest_addr[6:0]==0));
 wire accept=enroll_v&&enroll_r;
 assign lease_v=stage_retained;
 // Safe-before-grant; ongoing operation owns this one borrower slot.
 assign quiet=good&&(phase==EMPTY||phase==LEASE);
 wire allowed=good&&!stage_ce&&!stage_due&&!fault&&grant;
 assign req_v=allowed&&(phase==RREQ||phase==WREQ||phase==VREQ);
 assign req={phase==WREQ,address,q[sector*256+:256],phase==WREQ?32'hffffffff:32'd0,request_tag};
 assign rsp_r=allowed&&(phase==RRSP||phase==WRSP||phase==VRSP);
 wire match_rsp=rsp[272:257]==request_tag&&rsp[256]==(phase==WRSP);
 wire readback_match=rsp[255:0]==q[sector*256+:256];
 wire rx_v=allowed&&phase==RX;
 wire [1023:0] rx_d=beat==2?1024'({tag,op_fn}):q[1023:0];
 wire tx_r=allowed&&phase==TX&&(!NATIVE_VM_PUBLICATION||native_tx_r);
 assign native_enroll_v=NATIVE_VM_PUBLICATION&&accept;
 assign native_tx_v=NATIVE_VM_PUBLICATION&&allowed&&phase==TX&&tx_v;
 assign native_tx_d=tx_d;assign native_tx_owner=tx_owner;
 assign native_tx_index=tx_index;assign native_tx_last=tx_last;
 assign native_producer_drained=good&&(phase==EMPTY||phase==TX||phase==DRAIN);
 assign native_complete_r=NATIVE_VM_PUBLICATION&&complete_r;
 wire result_verified=!NATIVE_VM_PUBLICATION||(native_publication_done&&native_complete_v&&native_match);
 assign publication_v=complete_v&&good&&!fault&&release_r&&result_verified;
 // Caller consumes real verified publication and simultaneously requests the
 // original borrower's reverse ACK. Wrong full73 never releases the seat.
 assign release_v=complete_v&&good&&!fault&&publication_r&&publication_owner==held_frame&&result_verified;
 wire complete_r=release_v&&release_r;
 ot_hbm_integrated_sfu_c12_stage #(.ENABLE(1)) u_stage(
  .clk(clk),.por_n(por_n),.warm_req(warm_req&&(stage_issued||phase==EMPTY)),.warm_ack(warm_ack),
  .enroll_v(accept),.enroll_r(stage_enroll_r),.enroll_frame(enroll_frame),
  .enroll_pc(enroll_pc),.enroll_op(enroll_op),.enroll_source(enroll_source),
  .enroll_expert(enroll_expert),.enroll_matrix(enroll_matrix),.enroll_row(enroll_row),.enroll_count(enroll_count),
  .owner_valid(owner_valid),.owner_frame(owner_frame),.source_permit(allowed),
  .producer_drained(phase==EMPTY||phase==DRAIN),.consumer_drained(phase==EMPTY||(NATIVE_VM_PUBLICATION?native_publication_done:phase==DRAIN)),
  .rx_v(rx_v),.rx_r(rx_r),.rx_d(rx_d),.rx_owner(held_frame),.rx_first(beat==0),.rx_last(beat==2),
  .tx_v(tx_v),.tx_r(tx_r),.tx_d(tx_d),.tx_owner(tx_owner),.tx_index(tx_index),.tx_last(tx_last),
  .complete_v(complete_v),.complete_r(complete_r),.complete_owner(publication_owner),
  .retained(stage_retained),.issued(stage_issued),.ce(stage_ce),.due(stage_due),.fault(stage_fault),
  .held_frame(held_frame),.held_pc(held_pc),.held_op(held_op),.held_source(),.held_expert(),.held_matrix(),.held_row(),.held_count());
 always @*begin
  n=q;
  if(accept)begin
   n[1215:1024]={dest_limit,dest_base,source_limit,source_base,dest_addr,source_addr};
   n[1247:1216]=local_tag;n[1250:1248]=fn;n[1254:1251]=LEASE;
   n[1258:1255]=0;
  end
  if(retained&&!live_owner)n[1259]=1;
  if(NATIVE_VM_PUBLICATION&&native_complete_v&&!native_match)n[1259]=1;
  if(publication_v&&publication_r&&publication_owner!=held_frame)n[1259]=1;
  if(allowed)begin
   if(phase==LEASE)n[1254:1251]=RREQ;
   if(req_v&&req_r)n[1254:1251]=phase==RREQ?RRSP:phase==WREQ?WRSP:VRSP;
   if(rsp_v&&rsp_r)begin
    if(!match_rsp||(phase==VRSP&&!readback_match))n[1259]=1;
    else if(phase==RRSP)begin
     n[sector*256+:256]=rsp[255:0];
     if(sector==3)begin n[1256:1255]=0;n[1254:1251]=RX;end
     else begin n[1256:1255]=sector+1'b1;n[1254:1251]=RREQ;end
    end else if(phase==WRSP)n[1254:1251]=VREQ;
    else if(sector==3)begin
     n[1256:1255]=0;n[1258:1257]=beat+1'b1;n[1254:1251]=TX;
    end else begin n[1256:1255]=sector+1'b1;n[1254:1251]=WREQ;end
   end
   if(rx_v&&rx_r)begin
    n[1258:1257]=beat==2?0:beat+1'b1;
    n[1254:1251]=beat==2?TX:RREQ;
    if(beat==1)n[1254:1251]=RX;
   end
   if(tx_v&&tx_r)begin
    if(tx_owner!=held_frame||tx_index!=4'(beat)||tx_last!=(beat==2))n[1259]=1;
    else if(beat==2)begin
     if(tx_d[32:0]!={tag,1'b0}||tx_d[1023:33]!=0)n[1259]=1;
     else n[1254:1251]=DRAIN;
    end else if(NATIVE_VM_PUBLICATION)begin n[1258:1257]=beat+1'b1;end
    else begin n[1023:0]=tx_d;n[1254:1251]=WREQ;n[1256:1255]=0;end
   end
   if(complete_r&&complete_v)begin n[1254:1251]=EMPTY;n[1258:1255]=0;end
  end
 end
 ot_hbm_accel_gu_metadata #(.WIDTH(1260)) io_state(
  .clk(clk),.rst_n(por_n),.we(good&&n!=q),.next_data(n),.data(q),.good(good),.ce(io_ce),.due(io_due));
 end endgenerate
endmodule
`default_nettype wire
