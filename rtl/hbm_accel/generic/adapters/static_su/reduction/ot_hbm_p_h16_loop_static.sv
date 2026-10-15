`timescale 1ns/1ps
`default_nettype none
// One actual compiled programme/start produces all16 heads. Only the rawSC and
// EB head extents, scalar word/bank and transaction tags vary between frames.
// Fixed metadata translates actual native VM return/commit identities; nothing
// waits for a response or adjusts the programme timeline.
// This diagnostic logical map still requires canonical allocator/physical bind.
module ot_hbm_p_h16_loop_static #(parameter integer PAGE_AW=2,AW=10+PAGE_AW)(
 input wire clk,rst_n,
 input wire[15:0]clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire cfg_we,input wire[2:0]cfg_stripe,input wire[AW-1:0]cfg_addr,input wire[255:0]cfg_data,
 input wire[AW:0]start_limit,
 input wire io_cfg_we,input wire[1:0]io_cfg_stripe,input wire[AW-1:0]io_cfg_addr,input wire[255:0]io_cfg_data,
 input wire io_start_v,input wire[AW:0]io_start_limit,input wire[9:0]profile_rows,
 input wire aux_cfg_we,input wire[AW-1:0]aux_cfg_addr,input wire[255:0]aux_cfg_data,
 output reg[135:0]local_rq,input wire[2055:0]local_rr,
 output reg[2247:0]local_wq,input wire[7:0]local_w_done,
 output wire scalar_valid,output wire[31:0]scalar_tag,scalar_fp32,
 output wire programme_done,io_done,output wire fault,output reg[3:0]active_head
);
 wire[135:0]core_rq;wire[2247:0]core_wq;
 reg[2055:0]core_rr;reg[7:0]core_done;
 wire[31:0]core_tag,ordinal;wire cv,core_fault;
 reg[AW:0]frame_row,frame_length;reg[9:0]rows_q;
 reg map_fault;
 wire[15:0]head_offset=rows_q==10'd128 ? (16'(active_head)<<4):((16'(active_head)<<6)+(16'(active_head)<<4));
 wire mb_read=core_rq[16]&&(core_rq[15:0]==16'd7800||core_rq[15:0]==16'd7808||core_rq[15:0]==16'd7840);
 wire scalar_write=core_wq[280]&&(core_wq[279:264]==16'd7800||core_wq[279:264]==16'd7808);
 reg[14:0]mb_v,mb_bank;
 reg[2:0]mb_word[0:14];
 reg[11:0]scalar_v,scalar_bank;
 wire[7:0]rr_valid={local_rr[2055],local_rr[1798],local_rr[1541],local_rr[1284],local_rr[1027],local_rr[770],local_rr[513],local_rr[256]};
 wire[7:0]core_rq_valid={core_rq[135],core_rq[118],core_rq[101],core_rq[84],core_rq[67],core_rq[50],core_rq[33],core_rq[16]};
 wire[7:0]core_wq_valid={core_wq[2247],core_wq[1966],core_wq[1685],core_wq[1404],core_wq[1123],core_wq[842],core_wq[561],core_wq[280]};
 always @*begin
  local_rq=core_rq;local_wq=core_wq;core_rr=local_rr;core_done=local_w_done;
  for(integer b=0;b<8;b=b+1)begin
   if(core_rq[17*b+16]&&core_rq[17*b+:16]<16'd1280)
    local_rq[17*b+:16]=core_rq[17*b+:16]+head_offset;
   if(core_rq[17*b+16]&&core_rq[17*b+:16]>=16'd2304&&core_rq[17*b+:16]<16'd2368)
    local_rq[17*b+:16]=core_rq[17*b+:16]+(16'(active_head)<<6);
   if(core_rq[17*b+16]&&core_rq[17*b+:16]==16'd7904)
    local_rq[17*b+:16]=16'd7904+(16'(active_head)<<3);
   if(core_wq[281*b+280]&&core_wq[281*b+264+:16]>=16'd4608&&core_wq[281*b+264+:16]<16'd4672)
    local_wq[281*b+264+:16]=core_wq[281*b+264+:16]+(16'(active_head)<<6);
   if(core_wq[281*b+280]&&core_wq[281*b+264+:16]==16'd7904)
    local_wq[281*b+264+:16]=16'd7904+(16'(active_head)<<3);
   if(core_wq[281*b+280]&&core_wq[281*b+264+:16]>=16'd6000&&core_wq[281*b+264+:16]<16'd6080)
    local_wq[281*b+264+:16]=core_wq[281*b+264+:16]+head_offset;
  end
  if(mb_read)begin
   local_rq=0;
   local_rq[17*active_head[3]+:17]={1'b1,core_rq[15:0]+16'(active_head[3])};
  end
  if(scalar_write)begin
   local_wq=0;
   local_wq[281*active_head[3]+:281]={1'b1,core_wq[279:264]+16'(active_head[3]),core_wq[263:8],8'b1<<active_head[2:0]};
  end
  if(mb_v[14])begin
   core_rr=0;
   core_rr[256:0]=local_rr[257*mb_bank[14]+:257];
   core_rr[31:0]=local_rr[257*mb_bank[14]+32*mb_word[14]+:32];
  end
  if(scalar_v[11])begin
   core_done=0;core_done[0]=local_w_done[scalar_bank[11]];
  end
 end
 always @(posedge clk)begin
  if(!rst_n)begin
   active_head<=0;frame_row<=0;frame_length<=0;rows_q<=0;
   mb_v<=0;mb_bank<=0;scalar_v<=0;scalar_bank<=0;map_fault<=0;
  end else begin
   if(io_start_v)begin
    active_head<=0;frame_row<=0;frame_length<=io_start_limit;rows_q<=profile_rows;
    if(!(profile_rows==128||profile_rows==640)||io_start_limit==0)map_fault<=1;
   end else if(cv)begin
    if(frame_row+1==frame_length)begin
     frame_row<=0;if(active_head!=15)active_head<=active_head+1;
    end else frame_row<=frame_row+1;
   end
   mb_v<={mb_v[13:0],mb_read};mb_bank<={mb_bank[13:0],active_head[3]};
   scalar_v<={scalar_v[10:0],scalar_write};scalar_bank<={scalar_bank[10:0],active_head[3]};
   if(mb_read&&core_rq_valid!=8'b1)map_fault<=1;
   if(scalar_write&&(core_wq_valid!=8'b1||core_wq[7:0]!=8'b1))map_fault<=1;
   if(mb_v[14]&&rr_valid!=(8'b1<<mb_bank[14]))map_fault<=1;
   if(scalar_v[11]&&local_w_done!=(8'b1<<scalar_bank[11]))map_fault<=1;
  end
  mb_word[0]<=active_head[2:0];
  for(integer j=1;j<15;j=j+1)mb_word[j]<=mb_word[j-1];
 end
 assign scalar_tag={27'd0,active_head,1'b0}|(core_tag&32'b1);
 assign fault=map_fault|core_fault;
 ot_hbm_p_native_producer_static #(.PAGE_AW(PAGE_AW)) u_core(
 .clk(clk),.rst_n(rst_n),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_base({AW{1'b0}}),.start_limit(start_limit),.start_loops(16'd1),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
 .io_start_v(io_start_v),.io_start_base({AW{1'b0}}),.io_start_limit(io_start_limit),.io_start_loops(16'd16),
 .aux_cfg_we(aux_cfg_we),.aux_cfg_addr(aux_cfg_addr),.aux_cfg_data(aux_cfg_data),
 .local_rq(core_rq),.local_rr(core_rr),.local_wq(core_wq),.local_w_done(core_done),
 .scalar_valid(scalar_valid),.scalar_tag(core_tag),.scalar_fp32(scalar_fp32),
 .programme_done(programme_done),.io_done(io_done),.fault(core_fault),.calendar_v(cv),.calendar_ordinal(ordinal));
endmodule
`default_nettype wire
