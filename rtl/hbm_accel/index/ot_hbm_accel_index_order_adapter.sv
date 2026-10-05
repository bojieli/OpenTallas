`timescale 1ns/1ps
// Additive serial canonical-ID adapter, ENABLE=0. No score arithmetic, selector
// change, global candidate mask, backing SRAM, ready tie, or host sorting.
// Model: uarch_model.hbm_index_ordered_adapter_model (e72bb27c1).
// The external exclusive gather port returns eight {literalID32,score32} pairs;
// its checked protection/borrowed owner and response latency are REAL inputs.
// Output logical ranks flatten the ordered stream. They are NOT producer ranks.
module ot_hbm_accel_index_order_adapter #(
 parameter integer ENABLE=0, N=96, NPER=512,
 parameter integer TOTAL=N*NPER, RB=(N>1?$clog2(N):1),
 parameter integer MW=$clog2(TOTAL/16)
)(
 input wire clk,por_n,start, output wire start_ready,
 input wire [31:0] source_job,input wire [3:0] source_gen,
 input wire [19:0] source_pos,
 input wire gather_exclusive,gather_writers_drained,result_capacity_reserved,
 output wire retained, output wire [31:0] held_job,
 output wire [3:0] held_gen, output wire [19:0] held_pos,
 output wire read_v,input wire read_r,
 output wire [6:0] read_rank,output wire [5:0] read_word,
 output wire [15:0] read_tag,
 input wire rsp_v,output wire rsp_r,input wire [511:0] rsp_pairs,
 input wire [31:0] rsp_job,input wire [3:0] rsp_gen,input wire [19:0] rsp_pos,
 input wire [6:0] rsp_rank,input wire [5:0] rsp_word,input wire [15:0] rsp_tag,
 input wire rsp_checked,input wire rsp_uncorrectable,
 // Borrowed W15 loading authority. ld_valid is the actual accepted load edge;
 // the W15 consumer has NO ready pin; permit must come from its enclosing owner.
 input wire merger_load_permit,
 output wire ld_valid,output wire ld_id,output wire [RB-1:0] ld_rank,
 output wire [MW-1:0] ld_word,output wire [511:0] ld_data,
 output reg ordered_loaded,
 // Merger completion is not publication. Matched sink/reverse is separate.
 input wire merger_done,
 input wire release_v,output wire release_r,
 input wire [31:0] release_job,input wire [3:0] release_gen,
 input wire [19:0] release_pos,
 input wire result_published,input wire source_reverse_done,
 output reg done,output reg fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE) begin:disabled
 assign start_ready=0;assign retained=0;assign held_job=0;assign held_gen=0;assign held_pos=0;
 assign read_v=0;assign read_rank=0;assign read_word=0;assign read_tag=0;assign rsp_r=0;
 assign ld_valid=0;assign ld_id=0;assign ld_rank=0;assign ld_word=0;assign ld_data=0;assign release_r=0;
 always @* begin done=0;fault=0;ordered_loaded=0;end
 end else begin:enabled
 initial if(N<1||N>96||NPER<16||NPER>512||NPER%16!=0)
  $fatal(1,"Bounded ordered adapter requires <=96 ranks, 16-aligned <=512 pairs/rank");
 localparam [3:0] IDLE=0,REQ=1,RSP=2,TREE=3,TAKE=4,LOAD_SCORE=5,LOAD_ID=6,WAIT_RELEASE=7,HOLD_FAULT=8;
 reg [3:0] state;
 reg [71:0] frame_code;
 wire [65:0] frame=decode64(frame_code);
 assign held_job=frame[55:24];assign held_gen=frame[23:20];assign held_pos=frame[19:0];
 reg [71:0] heads[0:N-1][0:7];
 // {reserved21,last_id20,has_previous1,consumed10,pad12}; each rank is protected.
 reg [71:0] meta[0:N-1];
 wire [65:0] mdec[0:N-1];
 wire [65:0] hdec[0:N-1];
 wire [9:0] consumed[0:N-1];
 reg [6:0] request_rank;
 reg [15:0] sequence_tag;
 reg [15:0] emitted;
 reg [2:0] tree_wait;
 reg filling_initial,load_then_refill;
 reg [6:0] refill_rank;
 reg [511:0] score_word,id_word;
 reg [3:0] lane;
 reg completed_merger;
 wire active=state!=IDLE;
 assign retained=active;
 wire lease_ok=gather_exclusive&&result_capacity_reserved;
 assign start_ready=!active&&!fault&&gather_exclusive&&gather_writers_drained&&result_capacity_reserved;
 assign read_v=state==REQ&&!fault&&lease_ok&&!frame[65];
 assign read_rank=request_rank;
 assign read_word=consumed[request_rank][8:3];
 assign read_tag=sequence_tag;
 wire response_match=rsp_job==held_job&&rsp_gen==held_gen&&rsp_pos==held_pos&&
  rsp_rank==read_rank&&rsp_word==read_word&&rsp_tag==read_tag;
 assign rsp_r=state==RSP&&!fault&&lease_ok&&response_match&&rsp_checked&&!rsp_uncorrectable;
 assign ld_valid=(state==LOAD_SCORE||state==LOAD_ID)&&merger_load_permit&&!fault&&lease_ok;
 assign ld_id=state==LOAD_ID;
 // emitted already includes this full 16-pair word. Flatten with stride=0.
 assign ld_rank=RB'((emitted-16)/NPER);
 assign ld_word=MW'(((emitted-16)%NPER)/16);
 assign ld_data=ld_id?id_word:score_word;
 wire release_match=release_job==held_job&&release_gen==held_gen&&release_pos==held_pos;
 assign release_r=state==WAIT_RELEASE&&!fault&&completed_merger&&release_match&&
  result_published&&source_reverse_done;
 // All 128 leaves are padded; 127 registered nodes, seven real levels. Choice
 // raw64 = {zero4,valid1,producer_rank7,literal_ID20,score32}; W6 per node.
 wire [71:0] leaf[0:127];
 reg [71:0] tree[1:127];
 wire [65:0] root=decode64(tree[1]);
 wire winner_v=root[59];
 wire [6:0] winner_rank=root[58:52];
 wire [19:0] winner_id=root[51:32];
 wire [31:0] winner_score=root[31:0];
 wire tree_bad[1:127];
 wire meta_bad[0:N-1];
 for(genvar r=0;r<128;r=r+1)begin:leaves
  if(r<N)begin:real_rank
   assign mdec[r]=decode64(meta[r]);assign consumed[r]=mdec[r][21:12];
   assign hdec[r]=decode64(heads[r][consumed[r][2:0]]);
   assign meta_bad[r]=mdec[r][65]||(consumed[r]<NPER&&hdec[r][65]);
   assign leaf[r]=encode64({4'b0,consumed[r]<NPER,7'(r),hdec[r][51:32],hdec[r][31:0]});
  end else begin:pad_rank
   assign leaf[r]=encode64(64'b0);
  end
 end
 function automatic [63:0] earlier(input [63:0] a,input [63:0] b);
  begin
   if(!a[59])earlier=b;
   else if(!b[59])earlier=a;
   else if(a[51:32]<=b[51:32])earlier=a;
   else earlier=b;
  end
 endfunction
 for(genvar t=1;t<128;t=t+1)begin:nodes
  wire [71:0] lcode,rcode;
  if(t>=64)begin
   assign lcode=leaf[2*t-128];assign rcode=leaf[2*t+1-128];
  end else begin
   assign lcode=tree[2*t];assign rcode=tree[2*t+1];
  end
  wire [65:0] l=decode64(lcode),r=decode64(rcode);
  assign tree_bad[t]=l[65]||r[65];
  always @(posedge clk or negedge por_n)
   if(!por_n)tree[t]<=encode64(0);
   else if(state==TREE)tree[t]<=encode64(earlier(l[63:0],r[63:0]));
 end
 integer i,j;
 reg bad,all_bad;
 reg [31:0] check_id,previous_id;
 reg [9:0] next_count;
 reg [63:0] next_meta;
 always @*begin
  all_bad=frame[65];
  for(integer k=0;k<N;k=k+1)all_bad=all_bad||meta_bad[k];
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   state<=IDLE;frame_code<=encode64(0);request_rank<=0;sequence_tag<=0;emitted<=0;
   tree_wait<=0;filling_initial<=0;load_then_refill<=0;refill_rank<=0;
   score_word<=0;id_word<=0;lane<=0;completed_merger<=0;fault<=0;done<=0;ordered_loaded<=0;
   for(i=0;i<N;i=i+1)begin
    meta[i]<=encode64(0);for(j=0;j<8;j=j+1)heads[i][j]<=encode64(0);
   end
  end else begin
   done<=0;ordered_loaded<=0;
   if(active&&merger_done)completed_merger<=1;
   if(active&&state!=HOLD_FAULT&&(all_bad||!lease_ok))begin fault<=1;state<=HOLD_FAULT;end
   else case(state)
    IDLE:if(start&&start_ready)begin
     frame_code<=encode64({8'b0,source_job,source_gen,source_pos});
     request_rank<=0;sequence_tag<=0;emitted<=0;lane<=0;completed_merger<=0;
     filling_initial<=1;load_then_refill<=0;state<=REQ;
     for(i=0;i<N;i=i+1)meta[i]<=encode64(0);
    end
    REQ:if(read_v&&read_r)state<=RSP;
    RSP:if(rsp_v)begin
     if(!response_match||!rsp_checked||rsp_uncorrectable)begin fault<=1;state<=HOLD_FAULT;end
     else if(rsp_r)begin
      bad=0;previous_id=mdec[request_rank][42:23];
      for(j=0;j<8;j=j+1)begin
       check_id=rsp_pairs[64*j+32+:32];
       if(check_id>=1048576||((check_id>>3)%96)!=request_rank||
        ((j!=0||mdec[request_rank][22])&&check_id<=previous_id))bad=1;
       previous_id=check_id;
      end
      if(bad)begin fault<=1;state<=HOLD_FAULT;end
      else begin
       for(j=0;j<8;j=j+1)heads[request_rank][j]<=encode64(rsp_pairs[64*j+:64]);
       next_meta=mdec[request_rank][63:0];next_meta[42:23]=previous_id[19:0];next_meta[22]=1;
       meta[request_rank]<=encode64(next_meta);sequence_tag<=sequence_tag+1;
       if(filling_initial&&request_rank<N-1)begin request_rank<=request_rank+1;state<=REQ;end
       else begin filling_initial<=0;tree_wait<=0;state<=TREE;end
      end
     end
    end
    TREE:begin
     // Early pipeline nodes still reflect OLD heads. Seven sampled edges flush
     // all levels; only the final root is examined in TAKE on the next edge.
     if(tree_wait==6)begin state<=TAKE;tree_wait<=0;end
     else tree_wait<=tree_wait+1;
    end
    TAKE:begin
     if(root[65]||!winner_v||winner_rank>=N)begin fault<=1;state<=HOLD_FAULT;end
     else begin
      bad=0;
      for(i=1;i<128;i=i+1)bad=bad||tree_bad[i];
      if(emitted!=0&&winner_id<=id_word[32*((lane==0)?15:lane-1)+:32])bad=1;
      if(bad)begin fault<=1;state<=HOLD_FAULT;end
      else begin
       score_word[32*lane+:32]<=winner_score;id_word[32*lane+:32]<={12'b0,winner_id};
       next_count=consumed[winner_rank]+1;
       next_meta=mdec[winner_rank][63:0];next_meta[21:12]=next_count;meta[winner_rank]<=encode64(next_meta);
       emitted<=emitted+1;lane<=lane+1;
       load_then_refill<=next_count<NPER&&next_count[2:0]==0;refill_rank<=winner_rank;
       if(lane==15)state<=LOAD_SCORE;
       else if(next_count<NPER&&next_count[2:0]==0)begin request_rank<=winner_rank;state<=REQ;end
       else begin tree_wait<=0;state<=TREE;end
      end
     end
    end
    LOAD_SCORE:if(ld_valid)state<=LOAD_ID;
    LOAD_ID:if(ld_valid)begin
     if(emitted==TOTAL)begin ordered_loaded<=1;state<=WAIT_RELEASE;end
     else if(load_then_refill)begin request_rank<=refill_rank;state<=REQ;end
     else begin tree_wait<=0;state<=TREE;end
    end
    WAIT_RELEASE:if(release_v)begin
     if(!release_match)begin fault<=1;state<=HOLD_FAULT;end
     else if(release_r)begin done<=1;state<=IDLE;end
    end
    default:state<=HOLD_FAULT;
   endcase
  end
 end
 end endgenerate
endmodule
