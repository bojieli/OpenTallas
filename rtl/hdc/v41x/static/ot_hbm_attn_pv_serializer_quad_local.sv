`timescale 1ns/1ps
`default_nettype none
// Source-only successor: 128 quad-local stores, 32 registered cohort selectors,
// eight registered native-bank gathers. All leaf clocks require the actual
// same-phase physical contract; tying them in a functional bench is not CTS.
module ot_hbm_attn_pv_serializer_quad_local(
 input wire clk,rst_n,input wire[127:0]quad_clk,
 input wire[31:0]select_clk,input wire[7:0]gather_clk,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,
 output reg write_v,output wire[2047:0]write_data,
 output wire[63:0]write_flags,output reg[15:0]write_base_sector,
 output reg fault
);
 wire[511:0]tile_data[0:31];wire[15:0]tile_flags[0:31];
 reg[4:0]vp;reg[1:0]cohort0,cohort1;reg[2:0]bp[0:3];
 reg[15:0]sp[0:4];reg cv_commit,ce_commit;reg[3:0]cd_commit;
 reg[15:0]seen[0:1];integer i;genvar t,a,l,b,k;
 wire[1:0]cohort={drain_head[3],drain_head[1]};
 wire[1:0]lane={drain_head[2],drain_head[0]};
 generate for(t=0;t<32;t=t+1)begin:g_tile
  wire[2047:0]qd;wire[63:0]qf;
  for(a=0;a<4;a=a+1)begin:g_quad
   wire[127:0]local_data;wire[3:0]local_flags;
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
    .drain_data(qd[a*512+:512]),.drain_flags(qf[a*16+:16]));
  end
  ot_hbm_attn_pv_cohort_select_registered u_select(.clk(select_clk[t]),.rst_n(rst_n),
   .capture_v(vp[1]),.cohort_select(cohort1),.quad_data(qd),.quad_flags(qf),
   .output_v(),.tile_data(tile_data[t]),.tile_flags(tile_flags[t]));
 end
 for(b=0;b<8;b=b+1)begin:g_bank
  wire[2047:0]gd;wire[63:0]gf;
  for(k=0;k<8;k=k+1)begin:g_input
   assign gd[k*256+:256]=tile_data[k*4+b/2][(b%2)*256+:256];
   assign gf[k*8+:8]=tile_flags[k*4+b/2][(b%2)*8+:8];
  end
  ot_hbm_attn_pv_bank_gather_binary u_gather(.clk(gather_clk[b]),.rst_n(rst_n),
   .capture_v(vp[3]),.block_select(bp[3]),.tile_data(gd),.tile_flags(gf),
   .output_v(),.bank_data(write_data[b*256+:256]),.bank_flags(write_flags[b*8+:8]));
 end endgenerate
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  vp<=0;write_v<=0;write_base_sector<=0;fault<=0;
  cohort0<=0;cohort1<=0;cv_commit<=0;ce_commit<=0;cd_commit<=0;
  seen[0]<=0;seen[1]<=0;
  for(i=0;i<4;i=i+1)bp[i]<=0;
  for(i=0;i<5;i=i+1)sp[i]<=0;
 end else begin
  vp<={vp[3:0],drain_v};write_v<=vp[4];write_base_sector<=sp[4];
  cohort0<=cohort;cohort1<=cohort0;
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
`default_nettype wire
