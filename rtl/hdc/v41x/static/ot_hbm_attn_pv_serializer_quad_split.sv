`timescale 1ns/1ps
`default_nettype none
// Per-quadrant PV drain (H-ATTQ 2026-10-15, coordinator default after H-DIE v15 'D local PV' review).
// The D source keeps quad-local stores (cohort a = {head[3],head[1]} = die quadrant a), but its single serializer output
// gathered all four quadrants into NE's one attention write group: a 2,248 b/edge long return across the die.
// Here every quadrant drains through its OWN registered tile stage and eight bank gathers into its OWN VM slice
// write group, so no PV bit leaves its quadrant. The 4:1 cohort select disappears; its two edges are kept as a
// registered tile stage (same request-to-bank-capture edges as ot_hbm_attn_pv_serializer_quad_local), so the
// static drain calendar is unchanged. One drain per edge (serial calendar); only quadrant cohort(head) writes.

// Two registered edges per (tile, quadrant): source capture and output, as the cohort select it replaces.
module ot_hbm_attn_pv_quad_tile_reg(
 input wire clk,rst_n,capture_v,
 input wire[511:0]quad_data,input wire[15:0]quad_flags,
 output reg output_v,output reg[511:0]tile_data,output reg[15:0]tile_flags
);
 reg[511:0]data_q;reg[15:0]flags_q;reg valid_q;
 always @(posedge clk)begin
  data_q<=quad_data;flags_q<=quad_flags;
  if(valid_q)begin tile_data<=data_q;tile_flags<=flags_q;end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_q<=0;output_v<=0;end
 else begin valid_q<=capture_v;output_v<=valid_q;end
endmodule

module ot_hbm_attn_pv_serializer_quad_split(
 input wire clk,rst_n,input wire[127:0]quad_clk,input wire[31:0]gather_clk,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,
 output reg[3:0]write_v,output wire[4*2048-1:0]write_data,
 output wire[4*64-1:0]write_flags,output reg[15:0]write_base_sector,
 output reg fault
);
 reg[4:0]vp;reg[1:0]cp[0:4];reg[2:0]bp[0:3];
 reg[15:0]sp[0:4];reg cv_commit,ce_commit;reg[3:0]cd_commit;
 reg[15:0]seen[0:1];integer i;genvar t,a,l,b,k;
 wire[1:0]cohort={drain_head[3],drain_head[1]};
 wire[1:0]lane={drain_head[2],drain_head[0]};
 generate for(a=0;a<4;a=a+1)begin:g_q
  wire[511:0]tile_data[0:31];wire[15:0]tile_flags[0:31];
  for(t=0;t<32;t=t+1)begin:g_tile
   wire[127:0]local_data;wire[3:0]local_flags;wire[511:0]qd;wire[15:0]qf;
   for(l=0;l<4;l=l+1)begin:g_lane
    localparam integer H=((a/2)*8)+((l/2)*4)+((a%2)*2)+(l%2);
    assign local_data[l*32+:32]=capture_data[t*512+H*32+:32];
    assign local_flags[l]=capture_flags[t*16+H];
   end
   ot_hbm_attn_pv_quad_store_registered u_store(.clk(quad_clk[t*4+a]),.rst_n(rst_n),
    .capture_v(capture_v),.capture_epoch(capture_epoch),.capture_dim(capture_dim),
    .capture_data(local_data),.capture_flags(local_flags),
    .drain_v(drain_v&&drain_block==3'(t/4)&&cohort==2'(a)),
    .drain_epoch(drain_epoch),.drain_lane(lane),.output_v(),
    .drain_data(qd),.drain_flags(qf));
   ot_hbm_attn_pv_quad_tile_reg u_reg(.clk(quad_clk[t*4+a]),.rst_n(rst_n),
    .capture_v(vp[1]&&cp[1]==2'(a)),.quad_data(qd),.quad_flags(qf),
    .output_v(),.tile_data(tile_data[t]),.tile_flags(tile_flags[t]));
  end
  for(b=0;b<8;b=b+1)begin:g_bank
   wire[2047:0]gd;wire[63:0]gf;
   for(k=0;k<8;k=k+1)begin:g_input
    assign gd[k*256+:256]=tile_data[k*4+b/2][(b%2)*256+:256];
    assign gf[k*8+:8]=tile_flags[k*4+b/2][(b%2)*8+:8];
   end
   ot_hbm_attn_pv_bank_gather_binary u_gather(.clk(gather_clk[a*8+b]),.rst_n(rst_n),
    .capture_v(vp[3]&&cp[3]==2'(a)),.block_select(bp[3]),.tile_data(gd),.tile_flags(gf),
    .output_v(),.bank_data(write_data[a*2048+b*256+:256]),.bank_flags(write_flags[a*64+b*8+:8]));
  end
 end endgenerate
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  vp<=0;write_v<=0;write_base_sector<=0;fault<=0;cv_commit<=0;ce_commit<=0;cd_commit<=0;
  seen[0]<=0;seen[1]<=0;
  for(i=0;i<5;i=i+1)begin sp[i]<=0;cp[i]<=0;end
  for(i=0;i<4;i=i+1)bp[i]<=0;
 end else begin
  vp<={vp[3:0],drain_v};
  write_v<=4'(vp[4])<<cp[4];write_base_sector<=sp[4];
  cp[0]<=cohort;for(i=1;i<5;i=i+1)cp[i]<=cp[i-1];
  bp[0]<=drain_block;for(i=1;i<4;i=i+1)bp[i]<=bp[i-1];
  sp[0]<=drain_base_sector+16'(int'(drain_head)*64+int'(drain_block)*8);
  for(i=1;i<5;i=i+1)sp[i]<=sp[i-1];
  cv_commit<=capture_v;ce_commit<=capture_epoch;cd_commit<=capture_dim;
  if(cv_commit)begin
   if(cd_commit==0)seen[ce_commit]<=16'h0001;
   else begin
    if(seen[ce_commit][cd_commit]||!seen[ce_commit][cd_commit-1])fault<=1;
    seen[ce_commit][cd_commit]<=1;
   end
  end
  if(drain_v)begin
   if(seen[drain_epoch]!=16'hffff||drain_base_sector[2:0]!=0||
    (capture_v&&capture_epoch==drain_epoch)||(cv_commit&&ce_commit==drain_epoch))fault<=1;
  end
 end
endmodule

// Native output: four write groups wq[a] (one per quadrant VM slice attention WG). QSID[2a+:2] is quadrant a's
// slice SID; every committed sector must lie in its own quadrant's slice (no cross-quadrant write is possible).
module ot_hbm_attn_pv_native_output_quad_split #(
 parameter integer ACTIVE_HEADS=16,
 parameter [7:0] QSID=8'b11_10_01_00, // cohort a -> sid (a=0..3); compiler/H-DIE owns the quadrant map
 parameter integer MUT=0              // bench only: 1 sends quadrant 1's write to quadrant 0's group
)(
 input wire clk,rst_n,input wire[127:0]quad_clk,input wire[31:0]gather_clk,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,drain_tag,
 output wire[4*2248-1:0]wq,output wire record_done,record_fault,
 output wire[15:0]record_tag,output wire fault
);
 localparam integer COMMITS=ACTIVE_HEADS*8;
 localparam integer CW=$clog2(COMMITS);
 wire[3:0]sv;wire sf;wire[4*2048-1:0]sd;wire[4*64-1:0]flags;wire[15:0]sector;
 ot_hbm_attn_pv_serializer_quad_split u_store(.clk(clk),.quad_clk(quad_clk),.gather_clk(gather_clk),.rst_n(rst_n),
  .capture_v(capture_v),.capture_epoch(capture_epoch),.capture_dim(capture_dim),
  .capture_data(capture_data),.capture_flags(capture_flags),
  .drain_v(drain_v),.drain_epoch(drain_epoch),.drain_head(drain_head),.drain_block(drain_block),
  .drain_base_sector(drain_base_sector),.write_v(sv),.write_data(sd),
  .write_flags(flags),.write_base_sector(sector),.fault(sf));
 genvar q,b;
 generate for(q=0;q<4;q=q+1)begin:g_q
  localparam integer QS=(MUT==1&&q==0)?1:(MUT==1&&q==1)?0:q;
  for(b=0;b<8;b=b+1)begin:g_wq
   assign wq[q*2248+b*281+:281]={sv[QS],16'(sector+b),sd[QS*2048+b*256+:256],8'hff};
  end
 end endgenerate
 wire any=|sv;
 reg[1:0]sq;
 always @*begin sq=0;for(integer a=0;a<4;a=a+1)if(sv[a])sq=2'(a);end
 reg sticky;reg[CW-1:0]count;
 reg[15:0]tag_pipe[0:5];reg[3:0]retire;reg[15:0]tags[0:3];integer j;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  sticky<=0;count<=0;retire<=0;
  for(j=0;j<6;j=j+1)tag_pipe[j]<=0;
  for(j=0;j<4;j=j+1)tags[j]<=0;
 end else begin
  retire<={retire[2:0],any&&count==CW'(COMMITS-1)};
  if(drain_v)tag_pipe[0]<=drain_tag;
  for(j=1;j<6;j=j+1)tag_pipe[j]<=tag_pipe[j-1];
  tags[0]<=tag_pipe[5];for(j=1;j<4;j=j+1)tags[j]<=tags[j-1];
  if(sf||(any&&|flags)||(drain_v&&int'(drain_head)>=ACTIVE_HEADS))sticky<=1;
  if(any)begin
   // own-quadrant slice, aligned, inside the 8192-sector slice
   if(sector[2:0]!=0||sector[14:13]!=QSID[sq*2+:2]||sector[12:0]>13'(8192-8)||(sv&(sv-4'd1))!=0)sticky<=1;
   count<=count+1'b1;
  end
 end
 assign fault=sticky|sf;
 assign record_done=retire[3]&&!fault;
 assign record_fault=retire[3]&&fault;
 assign record_tag=tags[3];
endmodule
`default_nettype wire
