`timescale 1ns/1ps
`default_nettype none
// Fixed selected L20/TP96 installation, default OFF. Existing provider only.
// A begin/record is metadata, never a publication ACK. Every source word is
// captured in W6 state and positively acknowledged after two real writes and
// both real readbacks. Original bridge owns descriptor rows and final sinks.
module ot_hbm_formatter_preinstall #(
 parameter integer ENABLE=0,
 parameter [63:0] ENTRY_PC=0,
 parameter [31:0] SCORE_SOURCE=32'h80000,ID_SOURCE=32'h80800,
 parameter [31:0] ARENA_BASE=32'h10000,ARENA_LIMIT=32'h70000,
 parameter [31:0] SINK_BASE=32'h70000,SINK_LIMIT=32'h70800,
 parameter [32:0] CAPACITY_BYTES=33'h100000
)(
 input wire clk,por_n,warm_req,input wire [72:0] actual_cp_frame,
 input wire begin_v,output wire begin_r,input wire [72:0] begin_frame,
 input wire [31:0] score_plane_base,id_plane_base,input wire [32:0] capacity_bytes,
 input wire [7:0] occupied_records,input wire [4:0] layer,candidate_source_layer,
 input wire candidate_masked,
 input wire [511:0] descriptor_readback,input wire [7:0] descriptor_mask,
 input wire descriptor_good,
 // Streaming actual installed records: occupied0, rank-score1, rank-ID2.
 // Each rank source record is exactly2048 bytes; entire planes196608 each.
 input wire record_v,output wire record_r,input wire [1:0] record_kind,
 input wire [6:0] record_rank,input wire [31:0] record_base,record_end,
 input wire [72:0] record_frame,
 // Actual admitted other writers (native, SU/norm, W2); no grant substitution.
 input wire [2:0] other_writer_v,input wire [95:0] other_writer_base,other_writer_end,
 output wire lease_v,input wire lease_granted,input wire [72:0] lease_frame,
 input wire provider_fault,
 input wire source_v,output wire source_r,input wire [72:0] source_frame,
 input wire [6:0] source_rank,input wire source_plane,input wire [4:0] source_word,
 input wire [511:0] source_data,
 output wire source_ACK_v,input wire source_ACK_r,
 output wire [72:0] source_ACK_frame,output wire [6:0] source_ACK_rank,
 output wire source_ACK_plane,output wire [4:0] source_ACK_word,
 output wire m_req_v,input wire m_req_r,output wire m_req_we,
 output wire [31:0] m_req_addr,output wire [255:0] m_req_data,
 output wire [31:0] m_req_strb,output wire [15:0] m_req_tag,
 input wire m_rsp_v,output wire m_rsp_r,input wire m_rsp_we,
 input wire [255:0] m_rsp_data,input wire [15:0] m_rsp_tag,
 output wire reservation_v,input wire reservation_r,
 output wire reservation_checked,reservation_exclusive,
 output wire [72:0] reservation_frame,output wire [511:0] reservation_descriptor,
 input wire gather_retained,gather_sink_visible,input wire [72:0] gather_frame,
 // Real numerical sink/consumer reverse offer; independently matched, held.
 input wire consumer_reverse_v,output wire consumer_reverse_r,
 input wire [72:0] consumer_reverse_frame,input wire consumer_sink_ACK_drained,
 output wire source_reverse_v,input wire source_reverse_r,
 output wire source_reverse_checked,source_drained,output wire [72:0] source_reverse_frame,
 input wire borrower_release_ACK,
 output wire retained,output wire [72:0] held_frame,
 output wire warm_ack,fault,ce,due
);
 function automatic overlap(input [32:0] a,b,c,d);
  overlap=a<d&&c<b;
 endfunction
 function automatic [63:0] expected_desc(input integer i);
  case(i)
   0:expected_desc=ENTRY_PC;
   1:expected_desc={ID_SOURCE,SCORE_SOURCE};
   2:expected_desc={ARENA_LIMIT,ARENA_BASE};
   3:expected_desc={SINK_LIMIT,SINK_BASE};
   4:expected_desc={31'd0,CAPACITY_BYTES};
   5:expected_desc=64'd96|(64'd512<<16)|(64'd32<<32);
   default:expected_desc=0;
  endcase
 endfunction
 wire [511:0] expected_descriptor;
 for(genvar k=0;k<8;k=k+1)assign expected_descriptor[k*64+:64]=expected_desc(k);
 generate if(ENABLE==0)begin:off
  assign begin_r=0;assign record_r=0;assign lease_v=0;assign source_r=0;
  assign source_ACK_v=0;assign source_ACK_frame=0;assign source_ACK_rank=0;
  assign source_ACK_plane=0;assign source_ACK_word=0;
  assign m_req_v=0;assign m_req_we=0;assign m_req_addr=0;assign m_req_data=0;
  assign m_req_strb=0;assign m_req_tag=0;assign m_rsp_r=0;
  assign reservation_v=0;assign reservation_checked=0;assign reservation_exclusive=0;
  assign reservation_frame=0;assign reservation_descriptor=0;
  assign consumer_reverse_r=0;assign source_reverse_v=0;
  assign source_reverse_checked=0;assign source_drained=0;assign source_reverse_frame=0;
  assign retained=0;assign held_frame=0;assign warm_ack=0;assign fault=0;assign ce=0;assign due=0;
 end else begin:on
  localparam [3:0] IDLE=0,RECORDS=1,LEASE=2,SOURCE=3,IO=4,ACK=5,
   BOOK=6,ACTIVE=7,REVERSE=8,RELEASE=9;
  wire [575:0] d;reg [575:0] n;wire good,c_ce,c_due;
  wire [511:0] payload;wire p_good,p_ce,p_due;
  wire [3:0] state=d[173:170];
  wire [31:0] sb=d[104:73],ib=d[136:105];wire [32:0] cap=d[169:137];
  wire [95:0] score_records=d[269:174],id_records=d[365:270],seen=d[461:366];
  wire [12:0] count=d[474:462];wire [15:0] seq=d[490:475];
  wire [1:0] op=d[492:491];wire waiting=d[493],failed=d[510];
  wire [7:0] wanted_occupied=d[501:494],got_occupied=d[509:502];
  wire [6:0] rank=d[517:511];wire [31:0] addr=d[549:518];
  wire live=state!=IDLE;
  assign held_frame=d[72:0];
  wire cp_match=actual_cp_frame==held_frame;
  wire desc_match=descriptor_good&&descriptor_mask==8'hff&&descriptor_readback==expected_descriptor;
  wire [32:0] score_end={1'b0,sb}+33'd196608,id_end={1'b0,ib}+33'd196608;
  wire [32:0] begin_se={1'b0,score_plane_base}+33'd196608;
  wire [32:0] begin_ie={1'b0,id_plane_base}+33'd196608;
  wire geometry=capacity_bytes==CAPACITY_BYTES&&score_plane_base[5:0]==0&&id_plane_base[5:0]==0&&
   begin_se<=capacity_bytes&&begin_ie<=capacity_bytes&&
   !overlap({1'b0,score_plane_base},begin_se,{1'b0,id_plane_base},begin_ie)&&
   !overlap({1'b0,score_plane_base},begin_se,{1'b0,ARENA_BASE},{1'b0,SINK_LIMIT})&&
   !overlap({1'b0,id_plane_base},begin_ie,{1'b0,ARENA_BASE},{1'b0,SINK_LIMIT})&&
   !overlap({1'b0,score_plane_base},begin_se,{1'b0,SCORE_SOURCE},{1'b0,ID_SOURCE}+33'd2048)&&
   !overlap({1'b0,id_plane_base},begin_ie,{1'b0,SCORE_SOURCE},{1'b0,ID_SOURCE}+33'd2048);
  wire begin_match=begin_frame==actual_cp_frame&&desc_match&&geometry&&
   layer==20&&candidate_source_layer==20&&!candidate_masked;
  reg writers_clear;
  always @*begin
   writers_clear=1;
   for(integer w=0;w<3;w=w+1)if(other_writer_v[w])begin
    if(other_writer_base[w*32+:32]>=other_writer_end[w*32+:32]||
     overlap({1'b0,other_writer_base[w*32+:32]},{1'b0,other_writer_end[w*32+:32]},{1'b0,ARENA_BASE},{1'b0,SINK_LIMIT})||
     overlap({1'b0,other_writer_base[w*32+:32]},{1'b0,other_writer_end[w*32+:32]},{1'b0,sb},score_end)||
     overlap({1'b0,other_writer_base[w*32+:32]},{1'b0,other_writer_end[w*32+:32]},{1'b0,ib},id_end))writers_clear=0;
   end
  end
  wire lease_match=lease_granted&&lease_frame==held_frame;
  wire usable=good&&p_good&&!failed&&!provider_fault;
  assign begin_r=usable&&state==IDLE&&!warm_req&&begin_match;
  wire begin_accept=begin_v&&begin_r;
  wire [32:0] record_expected={1'b0,(record_kind==1?sb:ib)}+33'(record_rank)*33'd2048;
  wire record_common=record_frame==held_frame&&record_base[5:0]==0&&record_end[5:0]==0&&
   record_base<record_end&&{1'b0,record_end}<=cap;
  wire record_occupied=record_kind==0&&got_occupied<wanted_occupied&&
   !overlap({1'b0,record_base},{1'b0,record_end},{1'b0,ARENA_BASE},{1'b0,SINK_LIMIT})&&
   !overlap({1'b0,record_base},{1'b0,record_end},{1'b0,sb},score_end)&&
   !overlap({1'b0,record_base},{1'b0,record_end},{1'b0,ib},id_end);
  wire record_source=(record_kind==1||record_kind==2)&&record_rank<96&&
   {1'b0,record_base}==record_expected&&{1'b0,record_end}==record_expected+33'd2048&&
   !(record_kind==1?score_records[record_rank]:id_records[record_rank]);
  wire record_match=record_common&&(record_occupied||record_source);
  assign record_r=usable&&state==RECORDS&&cp_match&&record_match;
  wire record_accept=record_v&&record_r;
  // The original shared arbiter decides grant; it is not synthesized here.
  assign lease_v=usable&&state>=LEASE;
  wire plane=count>=3072;wire [12:0] plane_count=plane?count-13'd3072:count;
  wire [4:0] word_index=5'(32'(plane_count)/32'd96);
  wire source_match=source_frame==held_frame&&source_rank<96&&source_plane==plane&&
   source_word==word_index&&!seen[source_rank];
  assign source_r=usable&&state==SOURCE&&!warm_req&&cp_match&&desc_match&&lease_match&&writers_clear&&source_match;
  wire source_accept=source_v&&source_r;
  assign source_ACK_v=usable&&state==ACK&&cp_match&&lease_match&&desc_match&&writers_clear;
  assign source_ACK_frame=held_frame;assign source_ACK_rank=rank;
  assign source_ACK_plane=plane;assign source_ACK_word=word_index;
  wire ack_accept=source_ACK_v&&source_ACK_r;
  assign m_req_v=usable&&state==IO&&!waiting&&cp_match&&lease_match&&desc_match&&writers_clear;
  assign m_req_we=!op[1];assign m_req_addr=addr+(op[0]?32'd32:0);
  assign m_req_data=op[0]?payload[511:256]:payload[255:0];
  assign m_req_strb=m_req_we?32'hffffffff:0;assign m_req_tag=seq;
  wire req_accept=m_req_v&&m_req_r;
  wire rsp_match=waiting&&m_rsp_we==!op[1]&&m_rsp_tag==seq;
  wire data_match=!op[1]||m_rsp_data==(op[0]?payload[511:256]:payload[255:0]);
  assign m_rsp_r=usable&&state==IO&&waiting&&lease_match&&rsp_match;
  wire rsp_accept=m_rsp_v&&m_rsp_r;
  wire checked_book=usable&&state>=BOOK&&count==6144&&cp_match&&desc_match&&
   lease_match&&writers_clear&&!waiting;
  assign reservation_v=checked_book&&state==BOOK;
  assign reservation_checked=checked_book;assign reservation_exclusive=checked_book;
  assign reservation_frame=held_frame;assign reservation_descriptor=descriptor_readback;
  wire gather_match=gather_retained&&gather_frame==held_frame;
  wire reverse_match=consumer_reverse_frame==held_frame&&consumer_sink_ACK_drained&&
   gather_match&&gather_sink_visible;
  assign consumer_reverse_r=checked_book&&state==ACTIVE&&reverse_match;
  assign source_reverse_v=checked_book&&state==REVERSE;
  assign source_reverse_checked=source_reverse_v;assign source_drained=source_reverse_v;
  assign source_reverse_frame=held_frame;
  assign retained=live||failed||!good||!p_good;
  assign warm_ack=warm_req&&state==IDLE&&usable;
  assign ce=c_ce||p_ce;assign due=c_due||p_due;
  assign fault=failed||due||provider_fault;
  always @*begin
   n=d;
   if(begin_accept)begin
    n=0;n[72:0]=begin_frame;n[104:73]=score_plane_base;n[136:105]=id_plane_base;
    n[169:137]=capacity_bytes;n[173:170]=RECORDS;n[501:494]=occupied_records;
   end
   if(record_accept)begin
    case(record_kind)
     0:n[509:502]=got_occupied+1'b1;
     1:n[174+integer'(record_rank)]=1;
     2:n[270+integer'(record_rank)]=1;
     default:begin end
    endcase
   end
   if(state==RECORDS&&(&score_records)&&(&id_records)&&got_occupied==wanted_occupied)n[173:170]=LEASE;
   if(state==LEASE&&lease_match&&cp_match&&desc_match&&writers_clear)n[173:170]=SOURCE;
   if(source_accept)begin
    n[173:170]=IO;n[517:511]=source_rank;n[492:491]=0;
    n[549:518]=(plane?ib:sb)+32'(source_rank)*32'd2048+32'(word_index)*32'd64;
   end
   if(req_accept)n[493]=1;
   if(rsp_accept)begin
    if(!data_match)n[510]=1;
    else begin
     n[493]=0;n[490:475]=seq+1'b1;
     if(op==3)n[173:170]=ACK;else n[492:491]=op+1'b1;
    end
   end
   if(ack_accept)begin
    n[474:462]=count+1'b1;n[366+integer'(rank)]=1;
    if(plane_count%96==95)n[461:366]=0;
    n[173:170]=count==6143?BOOK:SOURCE;
   end
   if(reservation_v&&reservation_r)n[173:170]=ACTIVE;
   if(consumer_reverse_v&&consumer_reverse_r)n[173:170]=REVERSE;
   if(source_reverse_v&&source_reverse_r)n[173:170]=RELEASE;
   // Sole shared owner actual reverse grant is the final retirement authority.
   if(state==RELEASE&&borrower_release_ACK)n[550]=1;
   if(state==RELEASE&&(d[550]||borrower_release_ACK)&&!gather_retained)n=0;
   if((begin_v&&state==IDLE&&!warm_req&&!begin_match)||
    (live&&(!cp_match||!descriptor_good||!desc_match||!writers_clear))||
    (record_v&&state==RECORDS&&!record_match)||
    (source_v&&state==SOURCE&&!source_match)||
    (m_rsp_v&&state==IO&&(!waiting||!rsp_match))||
    (state>=SOURCE&&state<RELEASE&&!lease_match)||
    (consumer_reverse_v&&state==ACTIVE&&!reverse_match))n[510]=1;
  end
  ot_hbm_accel_gu_metadata #(.WIDTH(576)) control(
   .clk(clk),.rst_n(por_n),.we(good&&n!=d),.next_data(n),.data(d),.good(good),.ce(c_ce),.due(c_due));
  ot_hbm_accel_gu_metadata #(.WIDTH(512)) payload_hold(
   .clk(clk),.rst_n(por_n),.we(source_accept),.next_data(source_data),
   .data(payload),.good(p_good),.ce(p_ce),.due(p_due));
 end endgenerate
endmodule
`default_nettype wire
