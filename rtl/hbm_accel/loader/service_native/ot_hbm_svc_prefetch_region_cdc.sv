`default_nettype none
// Eight resident 512-sector regions in the original 4096-sector SRAM capacity.
// Epoch low bits select storage only; full16-bit epoch and unique17-bit tag
// remain in the owner table and every response/landing/drain identity check.
// Variable waits are entirely on the HBM side. Delivery begins only after a
// whole block is resident and then emits ceil(total/8) fixed stream cycles.
// Performance, routing, and physical CDC timing remain unqualified.
module ot_hbm_svc_prefetch_region_cdc #(parameter [1:0] STACK=0, parameter integer DELIVERY_II=1, parameter integer ISSUE_INTERLEAVE=0, parameter integer MAX_OUTSTANDING=1, parameter integer ISSUE_WIDTH=1)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire [2:0] reserve_bank,input wire [15:0] reserve_epoch,
 output wire [7:0] block_ready,output reg block_ready_v,output reg [2:0] block_ready_bank,
 output reg [15:0] block_ready_epoch,
 input wire start_v,input wire [2:0] start_bank,input wire [15:0] start_epoch,
 output reg out_v,output reg [7:0] out_mask,output wire [2047:0] out_data,
 output reg [10:0] out_ordinal,output reg [2:0] out_bank,output reg [15:0] out_epoch,
 output reg out_last,output wire fault,
 output reg [31:0] k_v,input wire [31:0] k_rdy,output reg [959:0] k_addr,
 output wire [127:0] k_len,output wire [543:0] k_tag,output wire [31:0] k_we,
 output wire [8191:0] k_wdata,output wire [1023:0] k_wstrb,input wire [31:0] k_wr_done,
 input wire [31:0] kr_v,output reg [31:0] kr_rdy,input wire [543:0] kr_tag,
 input wire [127:0] kr_beat,input wire [8191:0] kr_data
);
 initial if(ISSUE_WIDTH<1||ISSUE_WIDTH>4||(ISSUE_WIDTH>1&&!ISSUE_INTERLEAVE))$fatal(1,"widePHYissue requiresinterleave andwidth1..4");
 initial if(MAX_OUTSTANDING<2||MAX_OUTSTANDING>16)$fatal(1,"region owner requires MAX_OUTSTANDING2..16");
 initial if(DELIVERY_II<1)$fatal(1,"DELIVERY_II must be positive");
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 function automatic [4:0] pc_of(input [29:0] s);
  pc_of=s[6:2]^s[11:7]^s[16:12];
 endfunction
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 wire descriptor_ok=(ISSUE_WIDTH==1||reserve_base[5:0]==0)&&(!ISSUE_INTERLEAVE || reserve_total[5:0]==0)&&reserve_total!=0&&reserve_total<=512&&reserve_base[31:30]==STACK&&reserve_end<=33'h040000000;
 reg [7:0] allocated,ready_q,announced;
 reg [15:0] bank_epoch[0:7];reg [11:0] bank_total[0:7],received[0:7];
 reg [511:0] seen[0:7];reg stream_fault,hbm_fault;
 (* async_reg="true" *)reg hbf1,hbf2;
 (* async_reg="true" *)reg stf1,stf2;
 wire desc_wr_ready,desc_rd_valid,desc_rd_ready,desc_ov,desc_un;
 wire [62:0] desc_data;
 assign reserve_ready=srst&&!allocated[reserve_bank]&&desc_wr_ready&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 ot_async_fifo #(.WIDTH(63),.DEPTH(4)) u_descriptor(
 .wr_clk(stream_clk),.wr_rst_n(srst),.wr_valid(reserve_fire),.wr_ready(desc_wr_ready),
 .wr_data({reserve_base,reserve_total,reserve_bank,reserve_epoch}),.wr_overflow(desc_ov),
 .rd_clk(hbm_clk),.rd_rst_n(hrst),.rd_valid(desc_rd_valid),.rd_ready(desc_rd_ready),.rd_data(desc_data),.rd_underflow(desc_un));
 assign fault=stream_fault||hbf2||desc_ov;
 assign block_ready=ready_q;
 reg h_active;reg [2:0] h_bank;reg [15:0] h_epoch;reg [29:0] h_base;
 reg [11:0] h_total,h_next,h_received;
 reg [MAX_OUTSTANDING-1:0] outstanding[0:31];
 reg [10:0] owner_ordinal[0:31][0:MAX_OUTSTANDING-1];
 reg [16:0] owner_tag[0:31][0:MAX_OUTSTANDING-1];
 reg [15:0] owner_epoch[0:31][0:MAX_OUTSTANDING-1];
 reg [2:0] owner_bank[0:31][0:MAX_OUTSTANDING-1];
 reg [16:0] next_tag;
 integer request_slot[0:ISSUE_WIDTH-1];reg tag_collision[0:ISSUE_WIDTH-1],request_duplicate[0:ISSUE_WIDTH-1];
 reg [11:0] request_sequence[0:ISSUE_WIDTH-1],request_ordinal[0:ISSUE_WIDTH-1];
 reg [29:0] request_sector[0:ISSUE_WIDTH-1];reg [4:0] request_pc[0:ISSUE_WIDTH-1];
 reg [16:0] request_tag[0:ISSUE_WIDTH-1];
 reg [543:0] request_tags;integer issue_count,bundle_count;
 reg [ISSUE_WIDTH-1:0] accepted_q,accepted_now,request_valid;
 reg bundle_complete,distinct_prefix;
 integer response_slot[0:31];
 assign desc_rd_ready=!h_active&&!hbm_fault&&hrst&&desc_rd_valid;
 // Reorder requests only within the variable-latency PHY boundary. A tile of
 //64 sectors visits16 distinct PCs before revisiting any PC, rather than
 //four requests to one PC. Owner ordinals remain true source-relative offsets.
 always @*begin
  for(integer rq=0;rq<ISSUE_WIDTH;rq=rq+1)begin
   request_sequence[rq]=h_next+12'(rq);
   request_ordinal[rq]=ISSUE_INTERLEAVE?{request_sequence[rq][11:6],request_sequence[rq][3:0],request_sequence[rq][5:4]}:request_sequence[rq];
   request_sector[rq]=h_base+request_ordinal[rq];request_pc[rq]=pc_of(request_sector[rq]);
   request_duplicate[rq]=0;
   for(integer prev=0;prev<ISSUE_WIDTH;prev=prev+1)
    if(prev<rq&&request_pc[prev]==request_pc[rq])request_duplicate[rq]=1;
   request_tag[rq]=next_tag+17'(rq);
   request_slot[rq]=-1;tag_collision[rq]=0;
   for(integer os=0;os<MAX_OUTSTANDING;os=os+1)begin
    if(!outstanding[request_pc[rq]][os]&&request_slot[rq]<0)request_slot[rq]=os;
    if(outstanding[request_pc[rq]][os]&&owner_tag[request_pc[rq]][os]==request_tag[rq])tag_collision[rq]=1;
   end
  end
 end
 assign k_len={32{4'd1}};assign k_tag=request_tags;
 assign k_we=0;assign k_wdata=0;assign k_wstrb=0;
 wire [7:0] fifo_wr_ready,fifo_rd_valid,fifo_rd_ready,fifo_ov,fifo_un;
 reg [7:0] fifo_wr_valid;reg [285:0] fifo_wr_data[0:7];
 wire [285:0] fifo_rd_data[0:7];
 reg [31:0] response_accepted;integer h_take;
 integer p,l;
 always @*begin
  k_v=0;k_addr=0;request_tags=0;bundle_count=0;
  request_valid=0;distinct_prefix=1;
  // A persistent accepted mask permits independent PHY ready stalls without
  //any combinational ready->valid/address path. A bundle ends before a repeated
  //PC and advances only once all its distinct requests have been accepted.
  for(integer rq=0;rq<ISSUE_WIDTH;rq=rq+1)begin
   if(request_sequence[rq]<h_total&&!request_duplicate[rq]&&distinct_prefix)bundle_count=bundle_count+1;
   else distinct_prefix=0;
  end
  for(integer rq=0;rq<ISSUE_WIDTH;rq=rq+1)begin
   if(h_active&&rq<bundle_count&&!hbm_fault)begin
    k_addr[30*request_pc[rq]+:30]=request_sector[rq];
    request_tags[17*request_pc[rq]+:17]=request_tag[rq];
    if(!accepted_q[rq]&&request_slot[rq]>=0&&!tag_collision[rq])begin
     k_v[request_pc[rq]]=1;
     request_valid[rq]=1;
    end
   end
  end
  kr_rdy=0;fifo_wr_valid=0;response_accepted=0;h_take=0;
  for(p=0;p<32;p=p+1)begin
   response_slot[p]=-1;
   for(integer os=0;os<MAX_OUTSTANDING;os=os+1)
    if(outstanding[p][os]&&kr_tag[17*p+:17]==owner_tag[p][os])response_slot[p]=os;
  end
  for(l=0;l<8;l=l+1)begin
   fifo_wr_data[l]=0;
   for(p=0;p<32;p=p+1)begin
    if(kr_v[p]&&response_slot[p]>=0&&owner_ordinal[p][response_slot[p]][2:0]==l&&
       owner_epoch[p][response_slot[p]]==h_epoch&&owner_bank[p][response_slot[p]]==h_bank&&kr_beat[4*p+:4]==0&&
       !fifo_wr_valid[l]&&!hbm_fault)begin
     // wr_valid is a transfer pulse, never a speculative FIFO overflow.
     if(fifo_wr_ready[l])begin
      kr_rdy[p]=1;fifo_wr_valid[l]=1;response_accepted[p]=1;h_take=h_take+1;
      fifo_wr_data[l]={owner_ordinal[p][response_slot[p]],owner_bank[p][response_slot[p]],owner_epoch[p][response_slot[p]],kr_data[256*p+:256]};
     end
    end
   end
  end
 end
 // Keep acceptance bookkeeping separate from request construction. Addresses
 //and valid depend only on registered ownership, never on combinational ready.
 always @*begin
  accepted_now=0;bundle_complete=1;issue_count=0;
  for(integer rq=0;rq<ISSUE_WIDTH;rq=rq+1)begin
   if(request_valid[rq]&&k_rdy[request_pc[rq]])accepted_now[rq]=1;
   if(rq<bundle_count&&!accepted_q[rq]&&!accepted_now[rq])bundle_complete=0;
  end
  if(h_active&&bundle_count>0&&bundle_complete&&!hbm_fault)issue_count=bundle_count;
 end
 integer hp;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   h_active<=0;h_bank<=0;h_epoch<=0;h_base<=0;h_total<=0;h_next<=0;h_received<=0;accepted_q<=0;
   next_tag<=0;accepted_q<=0;hbm_fault<=0;stf1<=0;stf2<=0;
   for(hp=0;hp<32;hp=hp+1)begin
    outstanding[hp]<=0;
    for(integer os=0;os<MAX_OUTSTANDING;os=os+1)begin
     owner_ordinal[hp][os]<=0;owner_tag[hp][os]<=0;owner_epoch[hp][os]<=0;owner_bank[hp][os]<=0;
    end
   end
  end else begin
   stf1<=stream_fault;stf2<=stf1;
   if(stf2||desc_un||(|fifo_ov)||(|k_wr_done))hbm_fault<=1;
   if(desc_rd_valid&&desc_rd_ready)begin
    if(desc_data[62:61]!=STACK||desc_data[30:19]==0||desc_data[30:19]>512||
       {3'b0,desc_data[60:31]}+desc_data[30:19]>33'h040000000)hbm_fault<=1;
    else begin
     h_active<=1;h_base<=desc_data[60:31];h_total<=desc_data[30:19];h_bank<=desc_data[18:16];h_epoch<=desc_data[15:0];
     h_next<=0;h_received<=0;accepted_q<=0;
     for(hp=0;hp<32;hp=hp+1)outstanding[hp]<=0;
    end
   end
   if(h_active)begin
    accepted_q<=accepted_q|accepted_now;
    if(issue_count>0)begin
     accepted_q<=0;
     h_next<=h_next+12'(issue_count);next_tag<=next_tag+17'(issue_count);
     end
    for(integer rq=0;rq<ISSUE_WIDTH;rq=rq+1)if(accepted_now[rq])begin
      outstanding[request_pc[rq]][request_slot[rq]]<=1;
      owner_ordinal[request_pc[rq]][request_slot[rq]]<=request_ordinal[rq][10:0];
      owner_tag[request_pc[rq]][request_slot[rq]]<=request_tag[rq];
      owner_epoch[request_pc[rq]][request_slot[rq]]<=h_epoch;owner_bank[request_pc[rq]][request_slot[rq]]<=h_bank;
    end
    for(hp=0;hp<32;hp=hp+1)begin
     if(kr_v[hp]&&(response_slot[hp]<0||owner_epoch[hp][response_slot[hp]]!=h_epoch||owner_bank[hp][response_slot[hp]]!=h_bank||kr_beat[4*hp+:4]!=0))hbm_fault<=1;
     if(response_accepted[hp])outstanding[hp][response_slot[hp]]<=0;
    end
    h_received<=h_received+h_take;
    if(h_received+h_take==h_total)h_active<=0;
   end else if(|kr_v)hbm_fault<=1;
  end
 end
 genvar g,c;
 generate for(g=0;g<8;g=g+1)begin:lanes
  ot_async_fifo #(.WIDTH(286),.DEPTH(4)) u_response(
   .wr_clk(hbm_clk),.wr_rst_n(hrst),.wr_valid(fifo_wr_valid[g]),.wr_ready(fifo_wr_ready[g]),
   .wr_data(fifo_wr_data[g]),.wr_overflow(fifo_ov[g]),
   .rd_clk(stream_clk),.rd_rst_n(srst),.rd_valid(fifo_rd_valid[g]),.rd_ready(fifo_rd_ready[g]),
   .rd_data(fifo_rd_data[g]),.rd_underflow(fifo_un[g]));
 end endgenerate
 reg [7:0] landing_write;reg [11:0] landed[0:7];
 integer sl;reg [10:0] ordinal;reg [2:0] bank;reg [15:0] epoch_in;
 always @*begin
  landing_write=0;for(integer r=0;r<8;r=r+1)landed[r]=0;
  for(sl=0;sl<8;sl=sl+1)begin
   ordinal=fifo_rd_data[sl][285:275];bank=fifo_rd_data[sl][274:272];epoch_in=fifo_rd_data[sl][271:256];
   if(fifo_rd_valid[sl]&&!fault&&allocated[bank]&&epoch_in==bank_epoch[bank]&&
      ordinal<bank_total[bank]&&ordinal[2:0]==sl&&!seen[bank][ordinal])begin
    landing_write[sl]=1;landed[bank]=landed[bank]+1'b1;
   end
  end
 end
 assign fifo_rd_ready={8{srst&&!fault}}&fifo_rd_valid;
 reg draining;reg [2:0] drain_bank;integer drain_gap;
 wire drain_issue=draining && drain_gap==0;reg [7:0] drain_row;reg [1:0] read_chip_q;
 wire [255:0] macro_data[0:7][0:3];
 wire [8:0] drain_storage_row={drain_bank[0],drain_bank[2:1],drain_row[5:0]};
 generate for(g=0;g<8;g=g+1)begin:payload_lane
  wire [10:0] ordinal_w=fifo_rd_data[g][285:275];
  wire [2:0] bank_w=fifo_rd_data[g][274:272];
  wire [8:0] write_storage_row={bank_w[0],bank_w[2:1],ordinal_w[8:3]};
  for(c=0;c<4;c=c+1)begin:chip
   ot_sram_1r1w_128x256_m1_r2c2 u_payload(
    .clk(stream_clk),.r_ce_in(drain_issue&&!fault&&drain_storage_row[8:7]==c),
    .r_addr_in(drain_storage_row[6:0]),.rd_out(macro_data[g][c]),
    .w_ce_in(landing_write[g]&&write_storage_row[8:7]==c),
    .w_addr_in(write_storage_row[6:0]),.wd_in(fifo_rd_data[g][255:0]),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  assign out_data[256*g+:256]=macro_data[g][read_chip_q];
 end endgenerate
 integer si,sb;reg [10:0] ordinal_s;reg [2:0] bank_s;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;ready_q<=0;announced<=0;stream_fault<=0;hbf1<=0;hbf2<=0;
   block_ready_v<=0;block_ready_bank<=0;block_ready_epoch<=0;
   draining<=0;drain_gap<=0;drain_bank<=0;drain_row<=0;read_chip_q<=0;
   out_v<=0;out_mask<=0;out_ordinal<=0;out_bank<=0;out_epoch<=0;out_last<=0;
   for(sb=0;sb<8;sb=sb+1)begin bank_epoch[sb]<=0;bank_total[sb]<=0;received[sb]<=0;seen[sb]<=0;end
  end else begin
   hbf1<=hbm_fault;hbf2<=hbf1;block_ready_v<=0;out_v<=0;out_last<=0;out_mask<=0;
   if(|fifo_un)stream_fault<=1;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin
     allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
     received[reserve_bank]<=0;seen[reserve_bank]<=0;ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
    end
   end
   for(si=0;si<8;si=si+1)if(fifo_rd_valid[si]&&fifo_rd_ready[si])begin
    ordinal_s=fifo_rd_data[si][285:275];bank_s=fifo_rd_data[si][274:272];
    if(!landing_write[si])stream_fault<=1;
    else seen[bank_s][ordinal_s]<=1;
   end
   for(sb=0;sb<8;sb=sb+1)if(landed[sb]!=0)begin
    received[sb]<=received[sb]+landed[sb];
    if(received[sb]+landed[sb]==bank_total[sb])begin ready_q[sb]<=1;end
   end
   // Announce the lowest resident region once per completion.
   begin:announce
    reg found;
    found=0;
    for(integer r=0;r<8;r=r+1)if(ready_q[r]&&!announced[r]&&!found)begin
     block_ready_v<=1;block_ready_bank<=3'(r);block_ready_epoch<=bank_epoch[r];announced[r]<=1;found=1;
    end
   end
   if(start_v)begin
    if(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault)stream_fault<=1;
    else begin draining<=1;drain_gap<=0;drain_bank<=start_bank;drain_row<=0;ready_q[start_bank]<=0;end
   end
   if(draining && drain_gap>0)drain_gap<=drain_gap-1;
   if(drain_issue&&!fault)begin
    drain_gap<=DELIVERY_II-1;
    out_v<=1;out_bank<=drain_bank;out_epoch<=bank_epoch[drain_bank];out_ordinal<={drain_row,3'b0};
    read_chip_q<=drain_storage_row[8:7];
    for(si=0;si<8;si=si+1)if({drain_row,3'b0}+si<bank_total[drain_bank])out_mask[si]<=1;
    if({drain_row,3'b0}+8>=bank_total[drain_bank])begin
     out_last<=1;draining<=0;allocated[drain_bank]<=0;
    end else drain_row<=drain_row+1'b1;
   end
  end
 end
endmodule
`default_nettype wire
