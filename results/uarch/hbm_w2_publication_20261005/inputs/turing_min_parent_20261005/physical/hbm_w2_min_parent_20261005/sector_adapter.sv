`timescale 1ns/1ps
// Default-off seam only: no lease, grant, release, result publication or CP reset.
// Rawls supplies the actual held owner/frame and reserved result-seat permits.
// The installed 81f map supplies BYTE addresses and FULL provider tags; neither
// native address*136 nor truncation of native/provider tags is a valid mapping.
// cfg entries are the original {SM8, local A8-line8}; the one-lane tail stores
// 16 code bytes + 1 scale byte, expanded back into native bits [1031:1024].
module ot_hbm_w2_parent_sector_adapter #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,input wire [72:0] owner_frame,
 input wire source_accept_permit,result_seat_permit,
 input wire native_req_v,output wire native_req_r,
 input wire [31:0] native_req_addr,input wire [9:0] native_req_tag,
 // Source-compiled lookup belongs to this EXACT frame and native line.
 input wire map_valid,input wire [72:0] map_frame,
 input wire [31:0] map_native_addr,input wire [2:0] map_sm,
 input wire [15:0] map_compact_offset,input wire [3:0] map_lanes,
 input wire [2:0] map_count,
 input wire [191:0] map_byte_addresses,input wire [95:0] map_tags,map_cfg,
 output wire sector_req_v,input wire sector_req_r,output wire [336:0] sector_req,
 input wire sector_rsp_v,output wire sector_rsp_r,input wire [272:0] sector_rsp,
 // Readyless native caller: rsp_v is ONE delivery edge, not a held repeated
// valid. pending/tag/data hold until its real delivery permit. Caller connects
// rsp_v directly; never feed pending to the readyless native engine.
 input wire native_delivery_permit,
 output wire native_rsp_pending,native_rsp_v,
 output wire [9:0] native_rsp_tag,output wire [1087:0] native_rsp_data,
 output wire busy,drained,fault,foreign_rsp
);
 generate if(ENABLE==0)begin:g_off
  assign native_req_r=0;assign sector_req_v=0;assign sector_req=0;
  assign sector_rsp_r=0;assign native_rsp_pending=0;assign native_rsp_v=0;
  assign native_rsp_tag=0;assign native_rsp_data=0;
  assign busy=0;assign drained=1;assign fault=0;assign foreign_rsp=0;
 end else begin:g_on
  localparam [2:0] IDLE=0,ISSUE=1,WAIT_RSP=2,BUILD=3,HOLD=4;
  wire [2:0] state,part,count;
  reg [2:0] state_next,part_next,count_next;
  wire failed;
  reg failed_next;
  wire [72:0] held_frame;
  reg [72:0] held_frame_next;
  wire [31:0] held_native_addr;
  reg [31:0] held_native_addr_next;
  wire [9:0] held_native_tag;
  reg [9:0] held_native_tag_next;
  wire [4:0] first_byte;
  reg [4:0] first_byte_next;
  wire [3:0] lanes;
  reg [3:0] lanes_next;
  wire [191:0] addresses;
  reg [191:0] addresses_next;
  wire [95:0] tags;
  reg [95:0] tags_next;
  wire [1535:0] bytes_hold;
  reg [1535:0] bytes_hold_next;
  wire [1087:0] line_hold;
  reg [1087:0] line_hold_next;
  wire same_owner=owner_valid && owner_frame==held_frame;
  wire [15:0] expected_tag=tags[part*16+:16];
  wire match_rsp=state==WAIT_RSP && same_owner &&
                 sector_rsp[272:257]==expected_tag && !sector_rsp[256];
  reg valid_map;
  integer length,span,first_sector,expected_local;
  always @* begin
   expected_local=0;
   length=map_lanes==8?136:17;
   span=integer'(map_compact_offset[4:0])+length;
   first_sector=integer'(map_compact_offset)>>5;
   valid_map=map_frame==owner_frame && map_native_addr==native_req_addr &&
             (map_lanes==8 || map_lanes==1) && map_count>=1 && map_count<=6 &&
             integer'(map_count)==((span+31)>>5);
   for(integer i=0;i<6;i=i+1)if(i<map_count)begin
    expected_local=(first_sector+i)>>2;
    if(map_byte_addresses[i*32+:5]!=0 || map_cfg[i*16+8+:8]!={5'd0,map_sm} ||
       expected_local>255 || integer'(map_cfg[i*16+:8])!=expected_local)
     valid_map=0;
    for(integer j=0;j<i;j=j+1)
     if(map_tags[i*16+:16]==map_tags[j*16+:16] ||
        map_byte_addresses[i*32+:32]==map_byte_addresses[j*32+:32])valid_map=0;
   end
  end
  assign fault=failed||view_fault;
  assign busy=state!=IDLE;
  assign drained=state==IDLE && (!failed && !view_fault);
  assign native_req_r=state==IDLE && (!failed && !view_fault) && owner_valid &&
                      source_accept_permit && result_seat_permit && map_valid && valid_map;
  assign sector_req_v=state==ISSUE && same_owner && (!failed && !view_fault);
  assign sector_req={1'b0,addresses[part*32+:32],256'd0,32'd0,expected_tag};
  assign sector_rsp_r=match_rsp && (!failed && !view_fault);
  assign foreign_rsp=sector_rsp_v && !match_rsp;
  assign native_rsp_pending=state==HOLD && same_owner && (!failed && !view_fault);
  assign native_rsp_v=native_rsp_pending && native_delivery_permit;
  assign native_rsp_tag=held_native_tag;
  assign native_rsp_data=line_hold;
  reg [1087:0] assembled;
  always @* begin
   assembled=0;
   if(lanes==8)begin
    for(integer b=0;b<136;b=b+1)
     assembled[b*8+:8]=bytes_hold[(integer'(first_byte)+b)*8+:8];
   end else begin
    for(integer b=0;b<16;b=b+1)
     assembled[b*8+:8]=bytes_hold[(integer'(first_byte)+b)*8+:8];
    assembled[1024+:8]=bytes_hold[(integer'(first_byte)+16)*8+:8];
   end
  end
  // por_n is common cold reset ONLY. Local CP reset has no path into the seam.
  wire view_fault;wire [3045:0] state_view;
  assign {state,part,count,failed,held_frame,held_native_addr,held_native_tag,first_byte,lanes,addresses,tags,bytes_hold,line_hold}=state_view;
  (* keep_hierarchy = 1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(3046)) u_state(
   .clk(clk),.por_n(por_n),.we(1'b1),.next_data({state_next,part_next,count_next,failed_next,held_frame_next,held_native_addr_next,held_native_tag_next,first_byte_next,lanes_next,addresses_next,tags_next,bytes_hold_next,line_hold_next}),.data(state_view),.fault(view_fault));
  always @* begin
   state_next=state;
   part_next=part;
   count_next=count;
   failed_next=failed;
   held_frame_next=held_frame;
   held_native_addr_next=held_native_addr;
   held_native_tag_next=held_native_tag;
   first_byte_next=first_byte;
   lanes_next=lanes;
   addresses_next=addresses;
   tags_next=tags;
   bytes_hold_next=bytes_hold;
   line_hold_next=line_hold;

    if(state!=IDLE && !same_owner)failed_next=1;
    if(state==IDLE && native_req_v && owner_valid && source_accept_permit &&
       result_seat_permit && map_valid && !valid_map)failed_next=1;
    if((!failed && !view_fault))case(state)
     IDLE:if(native_req_v && native_req_r)begin
      held_frame_next=owner_frame;held_native_addr_next=native_req_addr;
      held_native_tag_next=native_req_tag;first_byte_next=map_compact_offset[4:0];
      lanes_next=map_lanes;count_next=map_count;addresses_next=map_byte_addresses;
      tags_next=map_tags;part_next=0;bytes_hold_next=0;state_next=ISSUE;
     end
     ISSUE:if(sector_req_v && sector_req_r)state_next=WAIT_RSP;
     WAIT_RSP:if(sector_rsp_v && sector_rsp_r)begin
      bytes_hold_next[part*256+:256]=sector_rsp[255:0];
      if(part+3'd1==count)state_next=BUILD;
      else begin part_next=part+3'd1;state_next=ISSUE;end
     end
     BUILD:if(same_owner)begin line_hold_next=assembled;state_next=HOLD;end
     HOLD:if(native_rsp_v)state_next=IDLE;
     default:failed_next=1;
    endcase

  end
 end endgenerate
endmodule
