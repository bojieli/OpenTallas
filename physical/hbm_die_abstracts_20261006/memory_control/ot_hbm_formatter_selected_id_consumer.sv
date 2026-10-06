`timescale 1ns/1ps
`default_nettype none
// Default-OFF actual numerical consumer: original ordered adapter + original
// global512 merger. No host sort, arithmetic/golden replacement or new owner.
// One finite protected32x512 output landing is reserved BEFORE readyless GO.
module ot_hbm_formatter_selected_id_consumer #(
 parameter integer ENABLE=0,
 parameter [31:0] SINK_BASE=32'h071a3000,SINK_LIMIT=32'h071a3800,
 parameter [32:0] CAPACITY_BYTES=33'h08000000
)(
 input wire clk_sm,por_n,warm_req,
 input wire start_v,output wire start_r,input wire [72:0] start_frame,actual_cp_frame,
 input wire installer_book_v,input wire [72:0] installer_book_frame,
 input wire gather_retained,gather_arena_visible,gather_lease_valid,
 input wire [72:0] gather_lease_frame,input wire formatter_retained,
 input wire result_capacity_reserved,
 output wire caller_pair_v,input wire caller_pair_r,
 output wire [84:0] caller_pair,output wire [16:0] caller_pair_token17,
 input wire consumer_pairs_v,output wire consumer_pairs_r,
 input wire [598:0] consumer_pairs,input wire [72:0] consumer_pairs_frame,
 output wire sink_req_v,input wire sink_req_r,output wire [648:0] sink_req,
 input wire sink_rsp_v,output wire sink_rsp_r,input wire [636:0] sink_rsp,
 output wire consumer_reverse_v,input wire consumer_reverse_r,
 output wire [72:0] consumer_reverse_frame,output wire consumer_sink_ACK_drained,
 output wire retained,output wire [72:0] held_frame,
 output wire [5:0] captured_words,checked_sink_words,
 output wire warm_ack,fault,ce,due
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:off
  assign start_r=0;assign caller_pair_v=0;assign caller_pair=0;assign caller_pair_token17=0;
  assign consumer_pairs_r=0;assign sink_req_v=0;assign sink_req=0;assign sink_rsp_r=0;
  assign consumer_reverse_v=0;assign consumer_reverse_frame=0;assign consumer_sink_ACK_drained=0;
  assign retained=0;assign held_frame=0;assign captured_words=0;assign checked_sink_words=0;
  assign warm_ack=0;assign fault=0;assign ce=0;assign due=0;
 end else begin:on
  initial if(SINK_BASE[5:0]!=0||SINK_LIMIT[5:0]!=0||
   {1'b0,SINK_BASE}+33'd2048!={1'b0,SINK_LIMIT}||{1'b0,SINK_LIMIT}>CAPACITY_BYTES)
   $fatal(1,"Actual512-ID reserved sink must be64B-aligned2048B within provider capacity");
  localparam [3:0] IDLE=0,LOAD=1,MERGE=2,SINK=3,REVERSE=4,ADAPTER_RELEASE=5,RETIRE=6;
  wire [191:0] d;reg [191:0] n;wire control_good,control_ce,control_due;
  wire [3:0] state=d[76:73];wire [5:0] written=d[82:77],acked=d[88:83];
  wire pending=d[89],merge_started=d[106],merge_finished=d[107],reverse_accepted=d[108];
  wire [3:0] read_age=d[113:110];
  assign held_frame=d[72:0];assign captured_words=written;assign checked_sink_words=acked;
  wire active=state!=IDLE;
  // Candidate tuple before enrollment; held tuple throughout accepted lifetime.
  // Never qualify a new frame against stale EMPTY held_frame.
  wire [72:0] qualified_frame=active?held_frame:start_frame;
  wire context_match=installer_book_v&&installer_book_frame==qualified_frame&&
   actual_cp_frame==qualified_frame&&gather_retained&&gather_lease_valid&&
   gather_lease_frame==qualified_frame&&gather_arena_visible&&formatter_retained&&result_capacity_reserved;
  reg [71:0] fatal_code;
  wire [65:0] fatal_dec=decode64(fatal_code);
  wire fatal_bad=fatal_dec[65]||fatal_dec[0];
  wire usable=control_good&&!fatal_bad&&!fatal_dec[64];
  wire ad_start_ready,ad_retained,ad_fault,ad_done,ad_loaded;
  wire ad_read_v,ad_read_r,ad_rsp_r,ad_ld_v,ad_ld_id,ad_release_r;
  wire [6:0] ad_rank,ad_ld_rank;wire [5:0] ad_word;
  wire [15:0] ad_tag;wire [11:0] ad_ld_word;wire [511:0] ad_ld_data;
  wire [31:0] ad_job;wire [3:0] ad_gen;wire [19:0] ad_pos;
  wire core_busy,core_done,core_fault,core_out_v,core_out_last;
  wire core_out_nw;wire [511:0] core_out_data;wire [31:0] core_cycles;
  assign start_r=usable&&state==IDLE&&!warm_req&&context_match&&ad_start_ready;
  wire start_accept=start_v&&start_r;
  assign caller_pair_v=usable&&state==LOAD&&context_match&&ad_read_v;
  assign caller_pair={held_frame[31:0],held_frame[35:32],held_frame[72:53],ad_rank,ad_word,ad_tag};
  assign caller_pair_token17=held_frame[52:36];
  assign ad_read_r=caller_pair_r&&caller_pair_v;
  wire pair_match=consumer_pairs_frame==held_frame&&consumer_pairs[598:567]==held_frame[31:0]&&
   consumer_pairs[566:563]==held_frame[35:32]&&consumer_pairs[562:543]==held_frame[72:53];
  assign consumer_pairs_r=usable&&state==LOAD&&context_match&&pair_match&&ad_rsp_r;
  wire merger_permit=usable&&state==LOAD&&context_match&&!core_busy;
  wire core_go=usable&&state==MERGE&&context_match&&!merge_started&&!core_busy;
  // Original bodies and reduction/order logic remain byte-identical.
  ot_hbm_accel_index_order_adapter #(.ENABLE(1),.N(96),.NPER(512)) u_order(
   .clk(clk_sm),.por_n(por_n),.start(start_accept),.start_ready(ad_start_ready),
   .source_job(qualified_frame[31:0]),.source_gen(qualified_frame[35:32]),.source_pos(qualified_frame[72:53]),
   .gather_exclusive(context_match),.gather_writers_drained(gather_arena_visible),.result_capacity_reserved(result_capacity_reserved),
   .retained(ad_retained),.held_job(ad_job),.held_gen(ad_gen),.held_pos(ad_pos),
   .read_v(ad_read_v),.read_r(ad_read_r),.read_rank(ad_rank),.read_word(ad_word),.read_tag(ad_tag),
   .rsp_v(consumer_pairs_v&&usable&&state==LOAD&&context_match&&pair_match),.rsp_r(ad_rsp_r),
   .rsp_pairs(consumer_pairs[513:2]),.rsp_job(consumer_pairs[598:567]),.rsp_gen(consumer_pairs[566:563]),
   .rsp_pos(consumer_pairs[562:543]),.rsp_rank(consumer_pairs[542:536]),.rsp_word(consumer_pairs[535:530]),
   .rsp_tag(consumer_pairs[529:514]),.rsp_checked(consumer_pairs[1]),.rsp_uncorrectable(consumer_pairs[0]),
   .merger_load_permit(merger_permit),.ld_valid(ad_ld_v),.ld_id(ad_ld_id),.ld_rank(ad_ld_rank),.ld_word(ad_ld_word),.ld_data(ad_ld_data),
   .ordered_loaded(ad_loaded),.merger_done(core_done),
   .release_v(usable&&state==ADAPTER_RELEASE&&context_match),.release_r(ad_release_r),
   .release_job(held_frame[31:0]),.release_gen(held_frame[35:32]),.release_pos(held_frame[72:53]),
   .result_published(acked==32&&!pending&&merge_finished),.source_reverse_done(reverse_accepted),.done(ad_done),.fault(ad_fault));
  ot_coll_topk_merge #(.N(96),.NMAX(512),.LW(16),.LDW(1),.P(64),.PF(16),.DIG(4)) u_merge(
   .clk(clk_sm),.rst_n(por_n),.ld_valid(ad_ld_v),.ld_id(ad_ld_id),.ld_rank(ad_ld_rank),.ld_word(ad_ld_word),.ld_data(ad_ld_data),
   .go(core_go),.n(16'd512),.k(16'd512),.stride(32'd0),.busy(core_busy),.done(core_done),.fault(core_fault),
   .out_valid(core_out_v),.out_nw(core_out_nw),.out_data(core_out_data),.out_last(core_out_last),.stat_cycles(core_cycles));
  reg [71:0] landing[0:31][0:7];
  wire [4:0] sink_word=acked<32?acked[4:0]:5'd31;
  wire [65:0] landing_dec[0:7];wire [511:0] observed_ids;
  wire [7:0] landing_ces,landing_ues;
  for(genvar k=0;k<8;k=k+1)begin:landing_read
   assign landing_dec[k]=decode64(landing[sink_word][k]);
   assign observed_ids[k*64+:64]=landing_dec[k][63:0];
   assign landing_ces[k]=landing_dec[k][64];assign landing_ues[k]=landing_dec[k][65];
  end
  wire landing_good=!(|landing_ces)&&!(|landing_ues);
  wire output_match=state==MERGE&&written<32&&core_out_nw==1&&core_out_last==(written==31);
  wire output_capture=usable&&context_match&&core_out_v&&output_match;
  wire [31:0] sink_address=SINK_BASE+32'(acked)*32'd64;
  wire [15:0] sink_tag=16'hf100+16'(acked);
  assign sink_req={held_frame[72:53],held_frame[52:36],held_frame[35:32],held_frame[31:0],
   observed_ids,{1'b0,sink_word},7'd0,sink_tag,sink_address,3'd4};
  assign sink_req_v=usable&&state==SINK&&acked<32&&!pending&&context_match&&landing_good&&read_age==3;
  wire req_accept=sink_req_v&&sink_req_r;
  wire response_match=pending&&sink_rsp[0]&&sink_rsp[3:1]==4&&sink_rsp[19:4]==sink_tag&&
   sink_rsp[51:20]==sink_address&&sink_rsp[636:564]==held_frame&&sink_rsp[563:52]==observed_ids;
  assign sink_rsp_r=usable&&state==SINK&&context_match&&landing_good&&response_match;
  wire rsp_accept=sink_rsp_v&&sink_rsp_r;
  wire debt_clear=written==32&&acked==32&&!pending&&merge_finished&&!core_busy&&!core_out_v;
  assign consumer_reverse_v=usable&&state==REVERSE&&context_match&&debt_clear;
  assign consumer_reverse_frame=held_frame;
  assign consumer_sink_ACK_drained=consumer_reverse_v;
  assign retained=active||ad_retained||core_busy||fault;
  assign ce=control_ce||fatal_dec[64]||(active&&|landing_ces);
  assign due=control_due||fatal_dec[65]||(active&&|landing_ues);
  assign fault=fatal_bad||due||ad_fault||core_fault;
  assign warm_ack=warm_req&&!active&&!ad_retained&&!core_busy&&!fault;
  wire fatal_event=ad_fault||core_fault||control_due||
   (active&&state<RETIRE&&!context_match)||
   (consumer_pairs_v&&state==LOAD&&!pair_match)||
   (core_out_v&&(!output_match||!usable))||
   (core_done&&(!merge_started||written+(output_capture?6'd1:6'd0)!=32))||
   (active&&|landing_ues)||
   (sink_rsp_v&&state==SINK&&!response_match);
  always @*begin
   n=d;
   if(start_accept)begin n=0;n[72:0]=start_frame;n[76:73]=LOAD;end
   if(state==LOAD&&ad_loaded)n[76:73]=MERGE;
   if(core_go)n[106]=1;
   if(output_capture)n[82:77]=written+1'b1;
   if(core_done)begin n[107]=1;n[76:73]=SINK;n[113:110]=0;end
   // Visibility wait is scheduling only, NOT a physical timing cut/waiver.
   if(state==SINK&&!pending&&landing_good&&read_age<3)n[113:110]=read_age+1'b1;
   if(state==SINK&&!landing_good)n[113:110]=0;
   if(req_accept)n[89]=1;
   if(rsp_accept)begin n[89]=0;n[88:83]=acked+1'b1;n[113:110]=0;if(acked==31)n[76:73]=REVERSE;end
   if(consumer_reverse_v&&consumer_reverse_r)begin n[108]=1;n[76:73]=ADAPTER_RELEASE;end
   if(state==ADAPTER_RELEASE&&ad_release_r)n[76:73]=RETIRE;
   if(state==RETIRE&&!ad_retained&&!gather_retained)n=0;
  end
  ot_hbm_accel_gu_metadata #(.WIDTH(192)) control(
   .clk(clk_sm),.rst_n(por_n),.we(control_good&&!fatal_bad&&n!=d),.next_data(n),
   .data(d),.good(control_good),.ce(control_ce),.due(control_due));
  // A readyless output coinciding with CE must quarantine, not silently drop.
  // Independent protected fatal event retention sets a constant1 even if its
  // previous code has CE; no corrected-data permission or raw shadow owner.
  always @(posedge clk_sm or negedge por_n)begin
   if(!por_n)fatal_code<=encode64(0);
   else if(!fatal_dec[65])begin
    if(fatal_event)fatal_code<=encode64(1);
    else if(fatal_dec[64])fatal_code<=encode64(fatal_dec[63:0]);
   end
  end
  always @(posedge clk_sm or negedge por_n)begin
   if(!por_n)begin
    for(integer w=0;w<32;w=w+1)for(integer k=0;k<8;k=k+1)landing[w][k]<=encode64(0);
   end else begin
    if(output_capture)for(integer k=0;k<8;k=k+1)landing[written[4:0]][k]<=encode64(core_out_data[k*64+:64]);
    if(active&&state>=SINK&&!(|landing_ues))
     for(integer k=0;k<8;k=k+1)if(landing_ces[k])landing[sink_word][k]<=encode64(landing_dec[k][63:0]);
   end
  end
 end endgenerate
endmodule
`default_nettype wire
