`timescale 1ns/1ps
// Existing plane-major formatter on the real held gather bridge port.
// No new allocator, memory, owner, grant, done, or score/ID packing arithmetic.
module ot_hbm_integrated_formatter_provider #(
 parameter integer ENABLE=0,VM_AW=21
)(
 input wire clk,por_n,start,output wire start_ready,
 input wire [31:0] job,input wire [3:0] gen,input wire [16:0] token,input wire [19:0] pos,
 input wire [31:0] arena_base,arena_limit,
 input wire gather_retained,arena_visible,
 input wire pair_v,output wire pair_r,
 input wire [31:0] pair_job,input wire [3:0] pair_gen,input wire [19:0] pair_pos,
 input wire [6:0] pair_rank,input wire [5:0] pair_word,input wire [15:0] pair_tag,
 output wire pairs_v,input wire pairs_r,output wire [511:0] pairs,
 output wire [31:0] pairs_job,output wire [3:0] pairs_gen,output wire [19:0] pairs_pos,
 output wire [6:0] pairs_rank,output wire [5:0] pairs_word,output wire [15:0] pairs_tag,
 output wire pairs_checked,pairs_uncorrectable,retained,fault,
 output wire bridge_req_v,input wire bridge_req_r,output wire [648:0] bridge_req,
 input wire bridge_rsp_v,output wire bridge_rsp_r,input wire [636:0] bridge_rsp,
 input wire release_v,output wire release_r,
 input wire [31:0] release_job,input wire [3:0] release_gen,input wire [19:0] release_pos,
 input wire publication_done,source_reverse_done
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
 assign start_ready=0;assign pair_r=0;assign pairs_v=0;assign pairs=0;
 assign pairs_job=0;assign pairs_gen=0;assign pairs_pos=0;assign pairs_rank=0;assign pairs_word=0;assign pairs_tag=0;
 assign pairs_checked=0;assign pairs_uncorrectable=0;assign retained=0;assign fault=0;
 assign bridge_req_v=0;assign bridge_req=0;assign bridge_rsp_r=0;assign release_r=0;
 end else begin:on
 initial if(VM_AW<13||VM_AW>26)$fatal(1,"actual installer VM word aperture required");
 wire read_v,read_r,read_id,formatter_fault,formatter_ready,formatter_rsp_r;
 wire [VM_AW-1:0] read_addr;wire [6:0] read_rank;wire [15:0] read_tag;
 wire [31:0] read_job;wire [3:0] read_gen;wire [19:0] read_pos;
 // Preserve 33b byte arithmetic until bounds checked; never truncate W15 WA12.
 wire [32:0] byte_address={1'b0,32'(read_addr)}<<6;
 wire [32:0] arena_end={1'b0,arena_base}+33'd393216;
 wire bounds=arena_base[5:0]==0&&arena_limit[5:0]==0&&arena_end=={1'b0,arena_limit}&&
  arena_end<=(33'd1<<(VM_AW+6));
 wire read_bounds=!byte_address[32]&&byte_address>={1'b0,arena_base}&&byte_address+64<=arena_end;
 wire [31:0] rsp_addr=bridge_rsp[51:20];
 wire [31:0] rsp_job=bridge_rsp[595:564];wire [3:0] rsp_gen=bridge_rsp[599:596];
 wire [16:0] rsp_token=bridge_rsp[616:600];wire [19:0] rsp_pos=bridge_rsp[636:617];
 wire rsp_matches=bridge_rsp[3:1]==3'd3&&bridge_rsp[19:4]==read_tag&&
  {1'b0,rsp_addr}==byte_address&&rsp_job==read_job&&rsp_gen==read_gen&&rsp_pos==read_pos&&rsp_token==f[17:1];
 reg [71:0] fault_code;wire [65:0] f=decode64(fault_code);
 assign fault=f[0]||f[65]||formatter_fault;
 wire source_frame=read_job==job&&read_gen==gen&&read_pos==pos&&token==f[17:1];
 assign start_ready=formatter_ready&&bounds&&!fault;
 assign bridge_req_v=read_v&&source_frame&&read_bounds&&!fault;
 assign read_r=bridge_req_r&&source_frame&&read_bounds&&!fault;
 // Bridge req649: kind3, byteaddr32, original logical tag16/rank7/word6,
 // payload512, job32/gen4/input token17/position20. Kind3 is a read.
 wire [5:0] sector_word=6'(read_addr-VM_AW'(arena_base>>6)-VM_AW'(read_rank*32)-(read_id?VM_AW'(3072):VM_AW'(0)));
 assign bridge_req={read_pos,f[17:1],read_gen,read_job,512'd0,sector_word,read_rank,read_tag,byte_address[31:0],3'd3};
 assign bridge_rsp_r=formatter_rsp_r&&rsp_matches&&!fault;
 // ID identity follows the returned byte address, not the expected read_id.
 wire returned_id={1'b0,rsp_addr}>={1'b0,arena_base}+33'd196608;
 ot_hbm_accel_index_w15_planemajor_formatter #(.ENABLE(1),.N(96),.NPER(512),.AW(VM_AW)) formatter(
  .clk(clk),.por_n(por_n),.start(start&&bounds&&!fault),.start_ready(formatter_ready),
  .source_job(job),.source_gen(gen),.source_pos(pos),
  .gather_base(VM_AW'(arena_base>>6)),.gather_limit((VM_AW+1)'(arena_limit>>6)),
  .gather_exclusive(gather_retained),.gather_writers_drained(arena_visible),.retained(retained),.fault(formatter_fault),
  .pair_v(pair_v),.pair_r(pair_r),.pair_job(pair_job),.pair_gen(pair_gen),.pair_pos(pair_pos),
  .pair_rank(pair_rank),.pair_word(pair_word),.pair_tag(pair_tag),
  .pairs_v(pairs_v),.pairs_r(pairs_r),.pairs(pairs),.pairs_job(pairs_job),.pairs_gen(pairs_gen),.pairs_pos(pairs_pos),
  .pairs_rank(pairs_rank),.pairs_word(pairs_word),.pairs_tag(pairs_tag),.pairs_checked(pairs_checked),.pairs_uncorrectable(pairs_uncorrectable),
  .read_v(read_v),.read_r(read_r),.read_addr(read_addr),.read_id(read_id),.read_rank(read_rank),.read_tag(read_tag),
  .read_job(read_job),.read_gen(read_gen),.read_pos(read_pos),
  .rsp_v(bridge_rsp_v&&!fault),.rsp_r(formatter_rsp_r),.rsp_data(bridge_rsp[563:52]),
  .rsp_addr(VM_AW'(rsp_addr>>6)),.rsp_id(returned_id),.rsp_rank(read_rank),
  .rsp_tag(bridge_rsp[19:4]),.rsp_job(rsp_job),.rsp_gen(rsp_gen),.rsp_pos(rsp_pos),
  .rsp_checked(bridge_rsp[0]&&rsp_matches),.rsp_uncorrectable(f[65]),
  .release_v(release_v),.release_r(release_r),.release_job(release_job),.release_gen(release_gen),.release_pos(release_pos),
  .publication_done(publication_done),.source_reverse_done(source_reverse_done));
 always @(posedge clk or negedge por_n)begin
  if(!por_n)fault_code<=encode64(0);
  else if(fault||(start&&(!bounds||!start_ready))||(read_v&&(!source_frame||!read_bounds))||
   (bridge_rsp_v&&!rsp_matches))fault_code<=encode64(f[63:0]|64'd1);
  else if(start&&start_ready)fault_code<=encode64({46'd0,token,1'b0});
 end
 end endgenerate
endmodule
