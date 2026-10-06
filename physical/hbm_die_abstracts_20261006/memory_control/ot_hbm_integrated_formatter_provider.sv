`timescale 1ns/1ps
// Missing callable join for the selected integrated cluster. Default off.
// The existing formatter owns pair staging; the existing gather owner owns
// the exclusive arena, provider, write/readback publication and two sectors.
// No backing RAM, invented ECC receipt, or independent provider/calendar.
// model-before-build: formatter_join_prebuild.json + existing plane-major model.
// New required caller hooks: pair_token and release_token. Leaving either
// unbound does not qualify the old cluster instance as a connected parent.
module ot_hbm_integrated_formatter_provider #(
 parameter integer ENABLE=0,VM_AW=0
)(
 input wire clk,por_n,start,output wire start_ready,
 input wire [31:0] job,input wire [3:0] gen,input wire [16:0] token,input wire [19:0] pos,
 input wire [31:0] arena_base,arena_limit,input wire gather_retained,arena_visible,
 input wire owner_valid,input wire [72:0] owner_frame,
 input wire pair_v,output wire pair_r,
 input wire [31:0] pair_job,input wire [3:0] pair_gen,input wire [16:0] pair_token,
 input wire [19:0] pair_pos,input wire [6:0] pair_rank,input wire [5:0] pair_word,input wire [15:0] pair_tag,
 output wire pairs_v,input wire pairs_r,output wire [511:0] pairs,
 output wire [31:0] pairs_job,output wire [3:0] pairs_gen,output wire [19:0] pairs_pos,
 output wire [6:0] pairs_rank,output wire [5:0] pairs_word,output wire [15:0] pairs_tag,
 output wire [72:0] pairs_frame,
 output wire pairs_checked,pairs_uncorrectable,retained,fault,
 output wire bridge_req_v,input wire bridge_req_r,output wire [648:0] bridge_req,
 input wire bridge_rsp_v,output wire bridge_rsp_r,input wire [636:0] bridge_rsp,
 input wire release_v,output wire release_r,
 input wire [31:0] release_job,input wire [3:0] release_gen,input wire [16:0] release_token,
 input wire [19:0] release_pos,input wire publication_done,source_reverse_done
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:disabled
 assign start_ready=0;assign pair_r=0;assign pairs_v=0;assign pairs=0;
 assign pairs_job=0;assign pairs_gen=0;assign pairs_pos=0;assign pairs_rank=0;
 assign pairs_word=0;assign pairs_tag=0;assign pairs_frame=0;
 assign pairs_checked=0;assign pairs_uncorrectable=0;assign retained=0;assign fault=0;
 assign bridge_req_v=0;assign bridge_req=0;assign bridge_rsp_r=0;assign release_r=0;
 end else begin:enabled
 initial if(VM_AW<13||VM_AW>26)$fatal(1,"Actual gather aperture VM_AW13..26 required");
 reg [71:0] frame_lo,frame_hi,control_code;
 wire [65:0] lo=decode64(frame_lo),hi=decode64(frame_hi),control=decode64(control_code);
 wire [72:0] frame={hi[8:0],lo[63:0]};
 wire active=control[0],failed=control[1];
 wire bad=lo[65]||hi[65]||control[65];
 wire child_fault,child_retained,child_start_ready,child_pair_r,child_pairs_v,child_release_r;
 wire read_v,read_r,read_id,rsp_r;
 wire [31:0] read_addr,read_job;
 wire [6:0] read_rank;wire [15:0] read_tag;
 wire [3:0] read_gen;wire [19:0] read_pos;
 wire [32:0] end_byte={1'b0,arena_base}+33'd393216;
 wire bounds=arena_base[5:0]==0&&arena_limit[5:0]==0&&end_byte=={1'b0,arena_limit}&&
   end_byte<=(33'd1<<(VM_AW+6));
 wire lease_match=owner_valid&&owner_frame==frame;
 wire start_owner=owner_valid&&owner_frame=={pos,token,gen,job};
 wire pair_match={pair_pos,pair_token,pair_gen,pair_job}==frame;
 wire release_match={release_pos,release_token,release_gen,release_job}==frame;
 wire response_match=bridge_rsp[636:564]==frame&&bridge_rsp[51:20]=={read_addr[25:0],6'b0}&&
   bridge_rsp[19:4]==read_tag&&bridge_rsp[3:1]==3'd3;
 wire address_ok=read_addr[31:26]==0;
 assign fault=failed||bad||child_fault;
 assign retained=active||child_retained||fault;
 assign start_ready=child_start_ready&&!active&&!fault&&bounds&&start_owner;
 assign pair_r=child_pair_r&&active&&!fault&&lease_match&&pair_match;
 assign pairs_v=child_pairs_v&&active&&!fault&&lease_match;
 assign pairs_frame=frame;
 assign release_r=child_release_r&&active&&!fault&&lease_match&&release_match;
 // Existing ABI: {frame73, payload512, word6, rank7, tag16, BYTEaddr32, kind3}.
 assign bridge_req={frame,512'b0,pairs_word,read_rank,read_tag,{read_addr[25:0],6'b0},3'd3};
 assign bridge_req_v=read_v&&active&&!fault&&lease_match&&address_ok;
 assign read_r=bridge_req_r&&active&&!fault&&lease_match&&address_ok;
 // Existing ABI: {frame73, payload512, BYTEaddr32, tag16, kind3, checked1}.
 // The formatter's protected outstanding owner holds ID/rank: rsp637 does
 // not carry them. Address/tag/frame must match before those pins are reused.
 assign bridge_rsp_r=rsp_r&&active&&!fault&&lease_match&&response_match;
 ot_hbm_accel_index_w15_planemajor_formatter #(.ENABLE(1),.N(96),.NPER(512),.AW(32)) u_formatter(
  .clk(clk),.por_n(por_n),.start(start&&start_ready),.start_ready(child_start_ready),
  .source_job(job),.source_gen(gen),.source_pos(pos),
  .gather_base(arena_base>>6),.gather_limit({1'b0,arena_limit}>>6),
  .gather_exclusive(gather_retained&&owner_valid),.gather_writers_drained(arena_visible&&bounds),
  .retained(child_retained),.fault(child_fault),
  .pair_v(pair_v&&active&&!fault&&pair_match),.pair_r(child_pair_r),
  .pair_job(pair_job),.pair_gen(pair_gen),.pair_pos(pair_pos),.pair_rank(pair_rank),.pair_word(pair_word),.pair_tag(pair_tag),
  .pairs_v(child_pairs_v),.pairs_r(pairs_r&&!fault),.pairs(pairs),
  .pairs_job(pairs_job),.pairs_gen(pairs_gen),.pairs_pos(pairs_pos),
  .pairs_rank(pairs_rank),.pairs_word(pairs_word),.pairs_tag(pairs_tag),
  .pairs_checked(pairs_checked),.pairs_uncorrectable(pairs_uncorrectable),
  .read_v(read_v),.read_r(read_r),.read_addr(read_addr),.read_id(read_id),.read_rank(read_rank),
  .read_tag(read_tag),.read_job(read_job),.read_gen(read_gen),.read_pos(read_pos),
  .rsp_v(bridge_rsp_v&&active&&!fault&&response_match),.rsp_r(rsp_r),.rsp_data(bridge_rsp[563:52]),
  .rsp_addr(bridge_rsp[51:20]>>6),.rsp_id(read_id),.rsp_rank(read_rank),.rsp_tag(bridge_rsp[19:4]),
  .rsp_job(bridge_rsp[595:564]),.rsp_gen(bridge_rsp[599:596]),.rsp_pos(bridge_rsp[636:617]),
  .rsp_checked(bridge_rsp[0]),.rsp_uncorrectable(1'b0),
  .release_v(release_v&&active&&!fault&&release_match),.release_r(child_release_r),
  .release_job(release_job),.release_gen(release_gen),.release_pos(release_pos),
  .publication_done(publication_done),.source_reverse_done(source_reverse_done)
 );
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin frame_lo<=encode64(0);frame_hi<=encode64(0);control_code<=encode64(0);end
  else if(bad||child_fault||(active&&(!gather_retained||!lease_match))||
    (start&&!start_ready)||(pair_v&&active&&!pair_match)||
    (release_v&&active&&!release_match)||(read_v&&!address_ok)||
    (bridge_rsp_v&&active&&(!response_match||!bridge_rsp[0])))
   control_code<=encode64(64'd3); // quarantine retained owner until cold POR
  else if(start&&start_ready)begin
   frame_lo<=encode64({pos[10:0],token,gen,job});
   frame_hi<=encode64({55'b0,pos[19:11]});
   control_code<=encode64(64'd1);
  end else if(release_v&&release_r)control_code<=encode64(0);
 end
 end endgenerate
endmodule
