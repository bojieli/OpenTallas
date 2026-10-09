`timescale 1ps/1fs
`default_nettype none
// Actual73-bit native consumer. 74-bit use requires separately widened consumer;
// no slicing, fabricated read responses, timer publication or implicit retirement.
module ot_hbm_candidate_global_publication_join #(parameter integer ENABLE=0)(
 input wire clk,por_n,publication_start,input wire[72:0] publication_frame,
 output wire publication_start_r,input wire owner_valid,input wire[72:0] owner_frame,
 input wire flit_v,output wire flit_r,input wire[544:0] flit,input wire[72:0] flit_owner,
 input wire expected_kind,input wire[7:0] expected_dst,
 input wire empty_v,output wire empty_r,input wire[6:0] empty_rank,input wire[72:0] empty_frame,
 output wire publication_complete,input wire consumer_start,output wire consumer_start_r,
 output wire out_v,input wire out_r,output wire[33:0] out_tuple,
 output wire[72:0] out_frame,output wire[6:0] out_rank,
 input wire retire,input wire downstream_drained,output wire retained,done,fault
);
 wire rv,rr,sv,sr,last,empty,ce,consumer_retained,consumer_done,consumer_fault,store_fault;
 wire[72:0] rf,sf;wire[6:0] rank,srank;wire[16:0] ordinal,sordinal;wire[33:0] tuple;
 reg finished,finished_n,failed;
 wire legal_retire=finished&&downstream_drained&&!consumer_retained&&!out_v;
 always @(posedge clk or negedge por_n)begin
 if(!por_n)begin finished<=0;finished_n<=1;failed<=0;end
 else if(ENABLE)begin
 if(finished_n!=~finished)failed<=1;
 if(publication_start&&publication_start_r)begin finished<=0;finished_n<=1;end
 if(consumer_done)begin finished<=1;finished_n<=0;end
 if(retire&&!legal_retire)failed<=1;
 end
 end
 ot_hbm_candidate_publication_store #(.ENABLE(ENABLE),.OWNER_W(73)) store(
 .clk(clk),.por_n(por_n),.start(publication_start),.start_frame(publication_frame),.start_r(publication_start_r),
 .owner_valid(owner_valid),.owner_frame(owner_frame),.retire(retire&&legal_retire),
 .consumer_retained(consumer_retained||out_v||!downstream_drained),
 .flit_v(flit_v),.flit_r(flit_r),.flit(flit),.flit_owner(flit_owner),.expected_kind(expected_kind),.expected_dst(expected_dst),
 .empty_v(empty_v),.empty_r(empty_r),.empty_rank(empty_rank),.empty_frame(empty_frame),
 .publication_complete(publication_complete),.retained(retained),.fault(store_fault),
 .read_v(rv),.read_r(rr),.read_frame(rf),.read_rank(rank),.read_ordinal(ordinal),
 .rsp_v(sv),.rsp_r(sr),.rsp_frame(sf),.rsp_rank(srank),.rsp_ordinal(sordinal),.rsp_tuple(tuple),.rsp_last(last),.rsp_empty(empty),.rsp_ce(ce));
 ot_hbm_index_global_order #(.ENABLE(ENABLE)) consumer(
 .clk(clk),.por_n(por_n),.start(consumer_start&&!finished&&!failed),.start_r(consumer_start_r),
 .start_frame(owner_frame),.publication_complete(publication_complete),.owner_valid(owner_valid),.owner_frame(owner_frame),
 .read_v(rv),.read_r(rr),.read_frame(rf),.read_rank(rank),.read_ordinal(ordinal),
 .rsp_v(sv),.rsp_r(sr),.rsp_frame(sf),.rsp_rank(srank),.rsp_ordinal(sordinal),.rsp_tuple(tuple),.rsp_last(last),.rsp_empty(empty),
 .out_v(out_v),.out_r(out_r),.out_tuple(out_tuple),.out_frame(out_frame),.out_rank(out_rank),
 .retained(consumer_retained),.done(consumer_done),.fault(consumer_fault));
 assign done=ENABLE&&finished&&!failed;
 assign fault=ENABLE&&(store_fault||consumer_fault||failed||finished_n!=~finished);
endmodule
`default_nettype wire
