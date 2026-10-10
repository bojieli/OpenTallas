`timescale 1ns/1ps
// Opt-in transaction engine. Four windows overlap native-PC latency. This
// central controller exactness vehicle prices SRAM3commit/5publication/II2.
// It is not a qualified distributed physical view; physical cache banks and
// relays must replace the reference data store before adoption.
module ot_hbm_svc_dma_stream_wide #(
 parameter integer ENABLE=0, INITIAL_CREDITS=256, WINDOW=16384,
 parameter integer NC=32, LANES=32, TAGW=6, WRITE_COMMIT=3, READ_PUBLICATION=5, INGRESS_DEPTH=0,
 parameter integer MUT_DROP=0,MUT_DATA=0,MUT_PC_MAP=0
)(
 input wire clk,rst,
 input wire [TAGW+46:0] dq, output wire dq_rdy,
 output reg [LANES*(TAGW+266)-1:0] dd,input wire [LANES-1:0] dd_cr,
 output reg [31:0] pc_req_v,input wire[31:0] pc_req_ready,
 output reg [1183:0] pc_req_addr,output reg[127:0] pc_req_len,
 output reg[543:0] pc_req_tag,input wire[543:0] pc_rsp_tag,
 input wire[31:0] pc_rsp_v,output wire[31:0] pc_rsp_ready,
 input wire[8191:0] pc_rsp_data,input wire[127:0] pc_rsp_beat,
 input wire[31:0] pc_rsp_fault
);
 localparam integer SLOTS=WINDOW/256, SLOTW=$clog2(SLOTS), DDB=TAGW+266;
 reg[36:0] addr[0:SLOTS-1];reg[8:0] count[0:SLOTS-1];reg[TAGW-1:0] tag[0:SLOTS-1];
 reg[255:0] data[0:WINDOW-1];reg fault[0:WINDOW-1];reg present[0:WINDOW-1];
 reg[SLOTW:0] used;reg[SLOTW-1:0] alloc_slot,emit_slot,issue_slot;
 reg[SLOTW:0] pending_issue;
 reg[8:0] issue_idx;
 reg[8:0] emit_idx[0:LANES-1];reg[$clog2(INITIAL_CREDITS+1)-1:0] credits[0:LANES-1];
 wire[31:0] lease_ready,lease_capacity,cam_capacity,return_valid;wire[32*SLOTW-1:0] return_slot;wire[255:0] return_idx;
 wire[31:0] write_valid;wire[32*SLOTW-1:0] write_slot;wire[255:0] write_idx;
 wire[8191:0] write_data;wire[31:0] write_fault;wire[63:0] write_bank;
 wire[31:0] bank_ready;
 reg write_busy[0:31][0:3];
 reg read_busy[0:31][0:3];reg read_taken[0:31][0:3];
 integer read_sector,read_pc,read_bank;
 reg[31:0] commit_v[0:WRITE_COMMIT-1];
 reg[32*SLOTW-1:0] commit_slot[0:WRITE_COMMIT-1];
 reg[255:0] commit_idx[0:WRITE_COMMIT-1];
 reg[8191:0] commit_data[0:WRITE_COMMIT-1];
 reg[31:0] commit_fault[0:WRITE_COMMIT-1];
 reg[LANES*DDB-1:0] publication[0:READ_PUBLICATION-1];
 generate for(genvar ready_pc=0;ready_pc<32;ready_pc=ready_pc+1)begin:ingress
   wire[1:0] bank=pc_rsp_tag[ready_pc*17+14+:2]+pc_rsp_beat[ready_pc*4+:2];
   if(INGRESS_DEPTH==0)begin
     assign bank_ready[ready_pc]=!write_busy[ready_pc][bank];
     assign lease_capacity[ready_pc]=cam_capacity[ready_pc];
     assign write_valid[ready_pc]=return_valid[ready_pc];
     assign write_slot[ready_pc*SLOTW+:SLOTW]=return_slot[ready_pc*SLOTW+:SLOTW];
     assign write_idx[ready_pc*8+:8]=return_idx[ready_pc*8+:8];
     assign write_data[ready_pc*256+:256]=pc_rsp_data[ready_pc*256+:256];
     assign write_fault[ready_pc]=pc_rsp_fault[ready_pc];assign write_bank[ready_pc*2+:2]=bank;
   end else begin
     wire reservation_ready,control_fault;
     wire[3:0] wr_ready={ !write_busy[ready_pc][3],!write_busy[ready_pc][2],!write_busy[ready_pc][1],!write_busy[ready_pc][0] };
     assign bank_ready[ready_pc]=1'b1;
     assign lease_capacity[ready_pc]=cam_capacity[ready_pc] && reservation_ready;
     ot_hbm_svc_dma_pc_ingress #(.DEPTH(INGRESS_DEPTH),.SLOT_BITS(SLOTW)) q(
       .clk(clk),.rst(rst),.reserve_ready(reservation_ready),
       .reserve_take(pc_req_v[ready_pc] && lease_ready[ready_pc]),
       .reserve_bank(pc_req_tag[ready_pc*17+14+:2]),.reserve_len(pc_req_len[ready_pc*4+:4]),
       .in_v(return_valid[ready_pc]),.in_bank(bank),.in_slot(return_slot[ready_pc*SLOTW+:SLOTW]),
       .in_idx(return_idx[ready_pc*8+:8]),.in_data(pc_rsp_data[ready_pc*256+:256]),.in_fault(pc_rsp_fault[ready_pc]),
       .write_ready(wr_ready),.out_v(write_valid[ready_pc]),.out_bank(write_bank[ready_pc*2+:2]),
       .out_slot(write_slot[ready_pc*SLOTW+:SLOTW]),.out_idx(write_idx[ready_pc*8+:8]),
       .out_data(write_data[ready_pc*256+:256]),.out_fault(write_fault[ready_pc]),.control_fault(control_fault));
   end
 end endgenerate
 genvar tile;generate for(tile=0;tile<32;tile=tile+1)begin:pc_tiles
 ot_hbm_svc_dma_pc_tile_wide #(.DEPTH(32),.SLOT_BITS(SLOTW)) u(.clk(clk),.rst(rst),
  .capacity(cam_capacity[tile]),.rq_v(pc_req_v[tile]),.rq_rdy(lease_ready[tile]),.rq_tag(pc_req_tag[tile*17+:17]),.rq_len(pc_req_len[tile*4+:4]),
  .consumer_ready(bank_ready[tile]),.phy_ready(pc_req_ready[tile]),.phy_v(),.rs_v(pc_rsp_v[tile]),.rs_rdy(pc_rsp_ready[tile]),
  .rs_tag(pc_rsp_tag[tile*17+:17]),.rs_beat(pc_rsp_beat[tile*4+:4]),
  .out_v(return_valid[tile]),.out_slot(return_slot[tile*SLOTW+:SLOTW]),.out_idx(return_idx[tile*8+:8]));
 end endgenerate
 integer l,p,j,k,cp,cl,bk,delaystage,idx,n,sector,sel,consumed,advance,remain,pos;
 integer proposal_slot[0:31],proposal_idx[0:31],proposal_len[0:31];
 reg[36:0] next_address;
 reg emit_complete,issue_complete;
 initial begin
   if(NC!=32 || LANES!=32 || TAGW!=6 || WINDOW!=16384 || WRITE_COMMIT!=3 || READ_PUBLICATION!=5 || INITIAL_CREDITS<1 || INITIAL_CREDITS>256)
     $fatal(1,"DMA stream shape must32PCx32lanes64x256window and measuredSRAM3commit/5publication; credits1..256");
 end
 wire accept=ENABLE && dq[TAGW+46] && dq_rdy;
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
   for(j=0;j<LANES;j=j+1)begin
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
         pc_req_tag[sel*17+:17]={1'b1,next_address[6:5],6'(issue_slot),8'(idx)};
         proposal_slot[sel]=issue_slot;proposal_idx[sel]=idx;proposal_len[sel]=n;
         if(lease_ready[sel])consumed=consumed+n;else advance=0;
       end else advance=0;
     end
   end
   issue_complete=pending_issue!=0 && issue_idx+consumed>=count[issue_slot];
   emit_complete=used!=0;
   for(cl=0;cl<LANES;cl=cl+1)if(emit_idx[cl]<count[emit_slot])emit_complete=0;
 end
 always @(posedge clk)begin
   if(rst)begin
     used<=0;alloc_slot<=0;emit_slot<=0;issue_slot<=0;pending_issue<=0;issue_idx<=0;dd<=0;
     for(l=0;l<LANES;l=l+1)begin emit_idx[l]<=l;credits[l]<=INITIAL_CREDITS;end
     for(delaystage=0;delaystage<WRITE_COMMIT;delaystage=delaystage+1)begin commit_v[delaystage]<=0;commit_slot[delaystage]<=0;commit_idx[delaystage]<=0;commit_data[delaystage]<=0;commit_fault[delaystage]<=0;end
     for(delaystage=0;delaystage<READ_PUBLICATION;delaystage=delaystage+1)publication[delaystage]<=0;
     for(p=0;p<32;p=p+1)for(bk=0;bk<4;bk=bk+1)begin write_busy[p][bk]<=0;read_busy[p][bk]<=0;read_taken[p][bk]=0;end
     for(k=0;k<WINDOW;k=k+1)begin present[k]<=0;fault[k]<=0;data[k]<=0;end
     for(k=0;k<SLOTS;k=k+1)begin addr[k]<=0;count[k]<=0;tag[k]<=0;end
   end else begin
     dd<=publication[READ_PUBLICATION-1];
     for(delaystage=READ_PUBLICATION-1;delaystage>0;delaystage=delaystage-1)publication[delaystage]<=publication[delaystage-1];
     publication[0]<=0;
     case({accept,emit_complete})2'b10:used<=used+1;2'b01:used<=used-1;default:begin end endcase
     case({accept,issue_complete})2'b10:pending_issue<=pending_issue+1;2'b01:pending_issue<=pending_issue-1;default:begin end endcase
     if(accept)begin
       addr[alloc_slot]<=dq[36:0];count[alloc_slot]<=dq[45:37];tag[alloc_slot]<=dq[46+:TAGW];alloc_slot<=alloc_slot+1;
     end
     if(issue_complete)begin issue_idx<=0;issue_slot<=issue_slot+1;end
     else if(pending_issue!=0)issue_idx<=issue_idx+consumed;
     if(emit_complete)begin emit_slot<=emit_slot+1;for(l=0;l<LANES;l=l+1)emit_idx[l]<=l;end
     for(p=0;p<32;p=p+1)for(bk=0;bk<4;bk=bk+1)begin read_busy[p][bk]<=0;read_taken[p][bk]=0;end
     for(l=0;l<LANES;l=l+1)begin
       read_sector=(addr[emit_slot][34:5]+emit_idx[l]);
       read_pc=((read_sector>>2)^(read_sector>>7)^(read_sector>>12))&31;read_bank=read_sector&3;
       pos=emit_slot*256+emit_idx[l];
       if(ENABLE && used!=0 && !emit_complete && emit_idx[l]<count[emit_slot] && present[pos] && credits[l]!=0 && !read_busy[read_pc][read_bank] && !read_taken[read_pc][read_bank])begin
         read_taken[read_pc][read_bank]=1;read_busy[read_pc][read_bank]<=1;
         publication[0][l*DDB+:DDB]<={1'b1,fault[pos],tag[emit_slot],emit_idx[l][7:0],data[pos] ^ (MUT_DATA?256'd1:256'd0)};
         if(MUT_DROP && emit_idx[l]==0)publication[0][l*DDB+DDB-1]<=0;
         present[pos]<=0;emit_idx[l]<=emit_idx[l]+LANES;
         if(!dd_cr[l])credits[l]<=credits[l]-1;
       end else if(dd_cr[l])credits[l]<=credits[l]+1;
     end
     for(delaystage=WRITE_COMMIT-1;delaystage>0;delaystage=delaystage-1)begin
       commit_v[delaystage]<=commit_v[delaystage-1];commit_slot[delaystage]<=commit_slot[delaystage-1];
       commit_idx[delaystage]<=commit_idx[delaystage-1];commit_data[delaystage]<=commit_data[delaystage-1];commit_fault[delaystage]<=commit_fault[delaystage-1];
     end
     commit_v[0]<=write_valid;commit_slot[0]<=write_slot;commit_idx[0]<=write_idx;
     commit_data[0]<=write_data;commit_fault[0]<=write_fault;
     for(p=0;p<32;p=p+1)begin
       for(bk=0;bk<4;bk=bk+1)write_busy[p][bk]<=0;
       if(write_valid[p])write_busy[p][write_bank[p*2+:2]]<=1;
       if(commit_v[WRITE_COMMIT-1][p])begin
         pos=commit_slot[WRITE_COMMIT-1][p*SLOTW+:SLOTW]*256+commit_idx[WRITE_COMMIT-1][p*8+:8];
         data[pos]<=commit_data[WRITE_COMMIT-1][p*256+:256];fault[pos]<=commit_fault[WRITE_COMMIT-1][p];present[pos]<=1;
       end
     end
   end
 end
endmodule
