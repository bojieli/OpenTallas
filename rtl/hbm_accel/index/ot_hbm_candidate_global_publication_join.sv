`timescale 1ps/1fs
`default_nettype none
// Native consumer has73-bit owner ABI. Optional74-bit boundary explicitly
// rejects the unsupported high bit; no silent truncation into another frame.
module ot_hbm_candidate_global_publication_join #(
 parameter integer ENABLE=0,OWNER_W=73,MUT_SLOT=0
)(
 input wire clk,por_n,publication_start,input wire[OWNER_W-1:0] publication_frame,
 output wire publication_start_r,input wire owner_valid,input wire[OWNER_W-1:0] owner_frame,
 input wire flit_v,output wire flit_r,input wire[544:0] flit,input wire[OWNER_W-1:0] flit_owner,
 input wire expected_kind,input wire[7:0] expected_dst,
 input wire empty_v,output wire empty_r,input wire[6:0] empty_rank,input wire[OWNER_W-1:0] empty_frame,
 output wire publication_complete,input wire consumer_start,output wire consumer_start_r,
 output wire out_v,input wire out_r,output wire[33:0] out_tuple,
 output wire[OWNER_W-1:0] out_frame,output wire[6:0] out_rank,
 input wire retire,input wire downstream_drained,output wire retained,done,fault
);
 wire rv,rr,sv,sr,last,empty,ce,consumer_retained,consumer_done,consumer_fault,store_fault;
 wire store_start_r,global_start_r,global_out_v;
 wire[72:0] rf,global_out_frame;wire[OWNER_W-1:0] sf;
 wire[6:0] rank,srank;wire[16:0] ordinal,sordinal;wire[33:0] tuple;
 reg finished,failed;
 wire owner_supported=(owner_frame>>73)==0;
 wire start_supported=(publication_frame>>73)==0;
 wire legal_retire=finished&&downstream_drained&&!consumer_retained&&!global_out_v;
 assign publication_start_r=store_start_r&&!failed&&start_supported&&owner_supported;
 assign consumer_start_r=global_start_r&&!finished&&!failed&&owner_supported;
 assign out_v=global_out_v&&!failed&&owner_supported;
 assign out_frame=OWNER_W'(global_out_frame);
 always @(posedge clk or negedge por_n)begin
 if(!por_n)begin finished<=0;failed<=0;end
 else if(ENABLE)begin
 if((publication_start&&!start_supported)||(owner_valid&&!owner_supported))failed<=1;
 if(publication_start&&publication_start_r)finished<=0;
 if(consumer_done)finished<=1;
 if(retire&&!legal_retire)failed<=1;
 end
 end
 ot_hbm_candidate_publication_store #(.ENABLE(ENABLE),.OWNER_W(OWNER_W),.MUT_SLOT(MUT_SLOT)) store(
 .clk(clk),.por_n(por_n),.start(publication_start&&publication_start_r),.start_frame(publication_frame),.start_r(store_start_r),
 .owner_valid(owner_valid),.owner_frame(owner_frame),.retire(retire&&legal_retire),
 .consumer_retained(consumer_retained||global_out_v||!downstream_drained),
 .flit_v(flit_v&&!failed),.flit_r(flit_r),.flit(flit),.flit_owner(flit_owner),.expected_kind(expected_kind),.expected_dst(expected_dst),
 .empty_v(empty_v&&!failed),.empty_r(empty_r),.empty_rank(empty_rank),.empty_frame(empty_frame),
 .publication_complete(publication_complete),.retained(retained),.fault(store_fault),
 .read_v(rv),.read_r(rr),.read_frame(OWNER_W'(rf)),.read_rank(rank),.read_ordinal(ordinal),
 .rsp_v(sv),.rsp_r(sr),.rsp_frame(sf),.rsp_rank(srank),.rsp_ordinal(sordinal),.rsp_tuple(tuple),.rsp_last(last),.rsp_empty(empty),.rsp_ce(ce));
 ot_hbm_index_global_order #(.ENABLE(ENABLE)) consumer(
 .clk(clk),.por_n(por_n),.start(consumer_start&&consumer_start_r),.start_r(global_start_r),
 .start_frame(owner_frame[72:0]),.publication_complete(publication_complete&&!failed),
 .owner_valid(owner_valid&&owner_supported&&!failed),.owner_frame(owner_frame[72:0]),
 .read_v(rv),.read_r(rr),.read_frame(rf),.read_rank(rank),.read_ordinal(ordinal),
 .rsp_v(sv),.rsp_r(sr),.rsp_frame(sf[72:0]),.rsp_rank(srank),.rsp_ordinal(sordinal),.rsp_tuple(tuple),.rsp_last(last),.rsp_empty(empty),
 .out_v(global_out_v),.out_r(out_r&&!failed&&owner_supported),.out_tuple(out_tuple),.out_frame(global_out_frame),.out_rank(out_rank),
 .retained(consumer_retained),.done(consumer_done),.fault(consumer_fault));
 assign done=ENABLE&&finished&&!failed;
 assign fault=ENABLE&&(store_fault||consumer_fault||failed);
endmodule
`default_nettype wire
