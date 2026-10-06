`timescale 1ns/1ps
`default_nettype none
// Specific installer/consumer join for the existing N96/NPER512 formatter.
// No allocation authority, arithmetic, payload buffer or second calendar.
// Prebuild: results/physical/.../formatter_install_consumer/prebuild.json.
// Receipt inputs MUST originate in actual positive publication/reverse ACKs.
// Their production producers are external dependencies, not constant enables.
module ot_hbm_formatter_install_consumer #(
 parameter integer ENABLE=0,
 parameter [63:0] ENTRY_PC=0,
 parameter [31:0] SCORE_SOURCE=32'h80000,ID_SOURCE=32'h80800,
 parameter [31:0] ARENA_BASE=32'h10000,ARENA_LIMIT=32'h70000,
 parameter [31:0] SINK_BASE=32'h70000,SINK_LIMIT=32'h70800,
 parameter [32:0] CAPACITY_BYTES=33'h100000,
 parameter integer EXPECTED_PAIRS=6144
)(
 input wire clk_sm,por_n,warm_req,input wire [72:0] actual_cp_frame,
 // Forward ONLY real accepted writes into the existing protected descriptor.
 input wire caller_desc_v,output wire caller_desc_r,
 input wire [2:0] caller_desc_index,input wire [63:0] caller_desc_data,
 output wire parent_desc_v,input wire parent_desc_r,
 output wire [2:0] parent_desc_index,output wire [63:0] parent_desc_data,
 // Real exclusive SOURCE/arena/sink publication receipt, full73 and geometry.
 // Eight descriptor writes are not a substitute for this positive receipt.
 input wire reservation_v,output wire reservation_r,
 input wire reservation_checked,reservation_exclusive,
 input wire [72:0] reservation_frame,input wire [511:0] reservation_descriptor,
 input wire caller_go_v,output wire caller_go_r,
 output wire installer_book_v,output wire [72:0] held_frame,
 output wire gather_start_v,input wire gather_start_r,
 input wire gather_retained,gather_arena_visible,gather_sink_visible,
 input wire [72:0] gather_frame,input wire gather_fault,
 output wire formatter_start_v,input wire formatter_start_r,
 input wire formatter_retained,formatter_fault,
 // One existing formatter query and held reply; no new payload staging.
 input wire caller_pair_v,output wire caller_pair_r,
 input wire [84:0] caller_pair,input wire [16:0] caller_pair_token17,
 output wire parent_pair_v,input wire parent_pair_r,
 output wire [84:0] parent_pair,output wire [16:0] parent_pair_token17,
 input wire parent_pairs_v,output wire parent_pairs_r,
 input wire [598:0] parent_pairs,input wire [72:0] parent_pairs_frame,
 output wire consumer_pairs_v,input wire consumer_pairs_r,
 output wire [598:0] consumer_pairs,output wire [72:0] consumer_pairs_frame,
 output wire consumer_loaded,
 // Actual producer reverse ACK, held until accepted; not last-issued/timeout.
 input wire source_reverse_v,output wire source_reverse_r,
 input wire source_reverse_checked,source_drained,
 input wire [72:0] source_reverse_frame,
 output wire result_published,source_reverse_done,
 output wire formatter_release_v,input wire formatter_release_r,
 output wire gather_release_v,input wire gather_release_r,
 output wire [72:0] release_frame,
 output wire retained,warm_ack,fault,ce,due
);
 function automatic [63:0] descriptor_word(input [2:0] index);
  case(index)
   0:descriptor_word=ENTRY_PC;
   1:descriptor_word={ID_SOURCE,SCORE_SOURCE};
   2:descriptor_word={ARENA_LIMIT,ARENA_BASE};
   3:descriptor_word={SINK_LIMIT,SINK_BASE};
   4:descriptor_word={31'd0,CAPACITY_BYTES};
   5:descriptor_word=64'd96|(64'd512<<16)|(64'd32<<32);
   default:descriptor_word=0;
  endcase
 endfunction
 wire [511:0] selected_descriptor;
 for(genvar w=0;w<8;w=w+1)begin:expected
  assign selected_descriptor[w*64+:64]=descriptor_word(3'(w));
 end
 assign parent_desc_index=caller_desc_index;
 assign parent_desc_data=caller_desc_data;
 assign parent_pair=caller_pair;
 assign parent_pair_token17=caller_pair_token17;
 assign consumer_pairs=parent_pairs;
 assign consumer_pairs_frame=parent_pairs_frame;
 generate if(ENABLE==0)begin:disabled
  assign caller_desc_r=0;assign parent_desc_v=0;assign reservation_r=0;
  assign caller_go_r=0;assign installer_book_v=0;assign held_frame=0;
  assign gather_start_v=0;assign formatter_start_v=0;
  assign caller_pair_r=0;assign parent_pair_v=0;assign parent_pairs_r=0;
  assign consumer_pairs_v=0;assign consumer_loaded=0;
  assign source_reverse_r=0;assign result_published=0;assign source_reverse_done=0;
  assign formatter_release_v=0;assign gather_release_v=0;assign release_frame=0;
  assign retained=0;assign warm_ack=0;assign fault=0;assign ce=0;assign due=0;
 end else begin:enabled
  initial if(EXPECTED_PAIRS!=6144)$fatal(1,"Production N96/512 needs6144 actual pair returns");
  wire [159:0] d;reg [159:0] n;wire good;
  wire active=d[81],book=d[82],go_pending=d[83],started=d[84];
  wire fmt_started=d[85],pending=d[86],reverse_done=d[87];
  wire fmt_released=d[88],gather_released=d[89],failed=d[90];
  wire [12:0] received=d[103:91];
  wire [28:0] query=d[145:117];
  assign held_frame=d[72:0];assign release_frame=held_frame;
  wire cp_match=actual_cp_frame==held_frame;
  wire lease_match=gather_retained&&gather_frame==held_frame;
  wire usable=good&&!failed;
  wire descriptor_match=caller_desc_data==descriptor_word(caller_desc_index);
  wire descriptor_permission=usable&&!started&&!go_pending&&
   ((!active&&!warm_req)||(active&&cp_match));
  assign parent_desc_v=caller_desc_v&&descriptor_permission&&descriptor_match;
  assign caller_desc_r=parent_desc_r&&descriptor_permission&&descriptor_match;
  wire descriptor_accept=parent_desc_v&&parent_desc_r;
  wire receipt_match=reservation_frame==held_frame&&
   reservation_descriptor==selected_descriptor&&reservation_checked&&reservation_exclusive;
  assign reservation_r=usable&&active&&cp_match&&d[80:73]==8'hff&&!book&&receipt_match;
  wire receipt_accept=reservation_v&&reservation_r;
  assign caller_go_r=usable&&active&&cp_match&&d[80:73]==8'hff&&!go_pending&&!started;
  wire go_accept=caller_go_v&&caller_go_r;
  assign installer_book_v=usable&&active&&book&&d[80:73]==8'hff&&cp_match;
  assign gather_start_v=installer_book_v&&go_pending&&!started;
  wire gather_accept=gather_start_v&&gather_start_r;
  assign formatter_start_v=usable&&started&&lease_match&&gather_arena_visible&&!fmt_started;
  wire formatter_accept=formatter_start_v&&formatter_start_r;
  wire [72:0] query_frame={caller_pair[48:29],caller_pair_token17,caller_pair[52:49],caller_pair[84:53]};
  wire query_match=query_frame==held_frame&&caller_pair[28:22]<96;
  wire query_permission=usable&&fmt_started&&!fmt_released&&lease_match&&
   formatter_retained&&!pending&&received<13'(EXPECTED_PAIRS);
  assign parent_pair_v=caller_pair_v&&query_permission&&query_match;
  assign caller_pair_r=parent_pair_r&&query_permission&&query_match;
  wire query_accept=parent_pair_v&&parent_pair_r;
  wire reply_match=parent_pairs_frame==held_frame&&
   parent_pairs[598:567]==held_frame[31:0]&&parent_pairs[566:563]==held_frame[35:32]&&
   parent_pairs[562:543]==held_frame[72:53]&&
   {parent_pairs[542:536],parent_pairs[535:530],parent_pairs[529:514]}==query&&
   parent_pairs[1]&&!parent_pairs[0];
  assign consumer_pairs_v=usable&&pending&&lease_match&&formatter_retained&&parent_pairs_v&&reply_match;
  assign parent_pairs_r=usable&&pending&&lease_match&&formatter_retained&&consumer_pairs_r&&reply_match;
  wire reply_accept=consumer_pairs_v&&consumer_pairs_r;
  assign consumer_loaded=usable&&active&&received==13'(EXPECTED_PAIRS)&&!pending;
  // Actual bridge sink visibility is raised only after32 checked kind4 stores.
  assign result_published=consumer_loaded&&lease_match&&gather_sink_visible;
  wire reverse_match=source_reverse_frame==held_frame&&source_reverse_checked&&source_drained;
  assign source_reverse_r=usable&&started&&lease_match&&!reverse_done&&reverse_match;
  wire reverse_accept=source_reverse_v&&source_reverse_r;
  assign source_reverse_done=usable&&active&&reverse_done;
  assign formatter_release_v=result_published&&source_reverse_done&&fmt_started&&!fmt_released;
  wire formatter_release_accept=formatter_release_v&&formatter_release_r;
  assign gather_release_v=result_published&&source_reverse_done&&fmt_released&&
   !formatter_retained&&!gather_released;
  wire gather_release_accept=gather_release_v&&gather_release_r;
  assign fault=failed||due;
  assign retained=active||failed||!good;
  assign warm_ack=warm_req&&usable&&!active;
  always @*begin
   n=d;
   if(descriptor_accept)begin
    if(!active)begin n=0;n[72:0]=actual_cp_frame;n[81]=1;end
    n[73+integer'(caller_desc_index)]=1;
   end
   if(receipt_accept)n[82]=1;
   if(go_accept)n[83]=1;
   if(gather_accept)begin n[84]=1;n[83]=0;end
   if(formatter_accept)n[85]=1;
   if(query_accept)begin n[86]=1;n[145:117]=caller_pair[28:0];end
   if(reply_accept)begin n[86]=0;n[103:91]=received+1'b1;end
   if(reverse_accept)n[87]=1;
   if(formatter_release_accept)n[88]=1;
   if(gather_release_accept)n[89]=1;
   // Release-ready accepts the request; actual shared reverse ACK/drain makes
   // retained drop later. Never rearm at release-ready alone.
   if(gather_released&&!gather_retained&&!formatter_retained)n=0;
   if((active&&!cp_match)||gather_fault||formatter_fault||
      (caller_desc_v&&descriptor_permission&&!descriptor_match)||
      (reservation_v&&active&&(!receipt_match||book))||
      (caller_pair_v&&query_permission&&!query_match)||
      (parent_pairs_v&&active&&(!pending||!reply_match))||
      (source_reverse_v&&started&&(!reverse_match||reverse_done))||
      (started&&!gather_released&&!lease_match)||
      (fmt_started&&!fmt_released&&!formatter_retained))n[90]=1;
  end
  // One W6 authority for the captured tuple/mask/debt. CE stalls/scrubs;
  // DUE retains damaged evidence. Warm never clears this accepted state.
  ot_hbm_accel_gu_metadata #(.WIDTH(160)) control(
   .clk(clk_sm),.rst_n(por_n),.we(good&&n!=d),.next_data(n),
   .data(d),.good(good),.ce(ce),.due(due));
 end endgenerate
endmodule
`default_nettype wire
