`timescale 1ns/1ps
// Opt-in transaction engine. Four windows overlap native-PC latency. This
// central exactness vehicle is not a qualified distributed physical view.
module ot_hbm_svc_dma_stream #(
 parameter integer ENABLE=0, INITIAL_CREDITS=256, WINDOW=2048,
 parameter integer NC=32, LANES=8,
 parameter integer MUT_DROP=0,MUT_DATA=0,MUT_PC_MAP=0
)(
 input wire clk,rst,
 input wire [50:0] dq, output wire dq_rdy,
 output reg [2159:0] dd,input wire [7:0] dd_cr,
 output reg [31:0] pc_req_v,input wire[31:0] pc_req_ready,
 output reg [1183:0] pc_req_addr,output reg[127:0] pc_req_len,
 output reg[543:0] pc_req_tag,input wire[543:0] pc_rsp_tag,
 input wire[31:0] pc_rsp_v,output wire[31:0] pc_rsp_ready,
 input wire[8191:0] pc_rsp_data,input wire[127:0] pc_rsp_beat,
 input wire[31:0] pc_rsp_fault
);
 localparam integer SLOTS=WINDOW/256, SLOTW=$clog2(SLOTS);
 reg[36:0] addr[0:SLOTS-1];reg[8:0] count[0:SLOTS-1];reg[3:0] tag[0:SLOTS-1];
 reg[255:0] data[0:WINDOW-1];reg fault[0:WINDOW-1];reg present[0:WINDOW-1];
 reg[SLOTW:0] used;reg[SLOTW-1:0] alloc_slot,emit_slot,issue_slot;
 reg[SLOTW:0] pending_issue;
 reg[8:0] issue_idx;
 reg[8:0] emit_idx[0:7];reg[$clog2(INITIAL_CREDITS+1)-1:0] credits[0:7];
 wire[31:0] lease_ready,lease_capacity,return_valid;wire[95:0] return_slot;wire[255:0] return_idx;
 genvar tile;generate for(tile=0;tile<32;tile=tile+1)begin:pc_tiles
 ot_hbm_svc_dma_pc_tile u(.clk(clk),.rst(rst),
  .capacity(lease_capacity[tile]),.rq_v(pc_req_v[tile]),.rq_rdy(lease_ready[tile]),.rq_tag(pc_req_tag[tile*17+:17]),.rq_len(pc_req_len[tile*4+:4]),
  .phy_ready(pc_req_ready[tile]),.phy_v(),.rs_v(pc_rsp_v[tile]),.rs_rdy(pc_rsp_ready[tile]),
  .rs_tag(pc_rsp_tag[tile*17+:17]),.rs_beat(pc_rsp_beat[tile*4+:4]),
  .out_v(return_valid[tile]),.out_slot(return_slot[tile*3+:3]),.out_idx(return_idx[tile*8+:8]));
 end endgenerate
 integer l,p,j,k,cp,cl,idx,n,sector,sel,consumed,advance,remain,pos;
 integer proposal_slot[0:31],proposal_idx[0:31],proposal_len[0:31];
 reg[36:0] next_address;
 reg emit_complete,issue_complete;
 initial begin
   if(NC!=32 || LANES!=8 || (WINDOW!=1024 && WINDOW!=2048) || INITIAL_CREDITS<1 || INITIAL_CREDITS>256)
     $fatal(1,"DMA stream shape must32PCx8lanes and4or8x256window; credits1..256");
 end
 wire accept=ENABLE && dq[50] && dq_rdy;
 assign dq_rdy=ENABLE && used<SLOTS && dq[45:37]!=0 && dq[45:37]<=256 && dq[4:0]==0;
 always @* begin
   pc_req_v=0;pc_req_addr=0;pc_req_len=0;pc_req_tag=0;
   next_address=0;idx=0;sector=0;sel=0;n=0;remain=0;
   for(cp=0;cp<32;cp=cp+1)begin
     proposal_slot[cp]=0;proposal_idx[cp]=0;proposal_len[cp]=0;

   end
   consumed=0;advance=1;
   // Eight independent PC groups can be issued each edge. At most one group
   // is leased per PC; a blocked PC stops subsequent ordered issue groups.
   for(j=0;j<8;j=j+1)begin
     idx=issue_idx+consumed;
     if(ENABLE && pending_issue!=0 && idx<count[issue_slot] && advance!=0)begin
       next_address=addr[issue_slot]+idx*32;
       sector=next_address[34:5];
       sel=((sector>>2)^(sector>>7)^(sector>>12))&31;
       if(MUT_PC_MAP)sel=sector&31;
       n=4-(sector&3);remain=count[issue_slot]-idx;if(n>remain)n=remain;
       if(lease_capacity[sel] && !pc_req_v[sel])begin
         pc_req_v[sel]=1;pc_req_addr[sel*37+:37]=next_address;
         pc_req_len[sel*4+:4]=n;
         pc_req_tag[sel*17+:17]={6'h2d,3'(issue_slot),8'(idx)};
         proposal_slot[sel]=issue_slot;proposal_idx[sel]=idx;proposal_len[sel]=n;
         if(lease_ready[sel])consumed=consumed+n;else advance=0;
       end else advance=0;
     end
   end
   issue_complete=pending_issue!=0 && issue_idx+consumed>=count[issue_slot];
   emit_complete=used!=0;
   for(cl=0;cl<8;cl=cl+1)if(emit_idx[cl]<count[emit_slot])emit_complete=0;
 end
 always @(posedge clk)begin
   if(rst)begin
     used<=0;alloc_slot<=0;emit_slot<=0;issue_slot<=0;pending_issue<=0;issue_idx<=0;dd<=0;
     for(l=0;l<8;l=l+1)begin emit_idx[l]<=l;credits[l]<=INITIAL_CREDITS;end
     for(k=0;k<WINDOW;k=k+1)begin present[k]<=0;fault[k]<=0;data[k]<=0;end
     for(k=0;k<SLOTS;k=k+1)begin addr[k]<=0;count[k]<=0;tag[k]<=0;end
   end else begin
     dd<=0;
     case({accept,emit_complete})2'b10:used<=used+1;2'b01:used<=used-1;default:begin end endcase
     case({accept,issue_complete})2'b10:pending_issue<=pending_issue+1;2'b01:pending_issue<=pending_issue-1;default:begin end endcase
     if(accept)begin
       addr[alloc_slot]<=dq[36:0];count[alloc_slot]<=dq[45:37];tag[alloc_slot]<=dq[49:46];alloc_slot<=alloc_slot+1;
     end
     if(issue_complete)begin issue_idx<=0;issue_slot<=issue_slot+1;end
     else if(pending_issue!=0)issue_idx<=issue_idx+consumed;
     if(emit_complete)begin emit_slot<=emit_slot+1;for(l=0;l<8;l=l+1)emit_idx[l]<=l;end
     for(l=0;l<8;l=l+1)begin
       pos=emit_slot*256+emit_idx[l];
       if(ENABLE && used!=0 && !emit_complete && emit_idx[l]<count[emit_slot] && present[pos] && credits[l]!=0)begin
         dd[l*270+:270]<={1'b1,fault[pos],tag[emit_slot],emit_idx[l][7:0],data[pos] ^ (MUT_DATA?256'd1:256'd0)};
         if(MUT_DROP && emit_idx[l]==0)dd[l*270+269]<=0;
         present[pos]<=0;emit_idx[l]<=emit_idx[l]+8;
         if(!dd_cr[l])credits[l]<=credits[l]-1;
       end else if(dd_cr[l])credits[l]<=credits[l]+1;
     end
     for(p=0;p<32;p=p+1)begin
       if(return_valid[p])begin
         pos=return_slot[p*3+:3]*256+return_idx[p*8+:8];
         data[pos]<=pc_rsp_data[p*256+:256];fault[pos]<=pc_rsp_fault[p];present[pos]<=1;
       end
     end
   end
 end
endmodule
