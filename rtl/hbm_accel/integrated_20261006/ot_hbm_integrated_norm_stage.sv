`timescale 1ns/1ps
`default_nettype none
// One existing normative operation seat and one selected norm VM endpoint.
// Existing stage216codedFF budget; no second descriptor/engine for this norm.
// Supplier is the real clock-held vectorVM ABI, NOT a native1024 port alias.
module ot_hbm_integrated_norm_stage #(
 parameter integer ENABLE=0,KIND=0,N=64,D=5120,RD=0,AW=24,
 parameter integer PUBLISH_QUANT=1,ROUTED=1,RW=9,BW=9,BCAST=7,RET=8
)(
 input wire clk,por_n,warm_req,output wire warm_ack,
 input wire enroll_v,output wire enroll_r,input wire [72:0] enroll_frame,
 input wire [31:0] enroll_pc,enroll_op,input wire [15:0] enroll_source,
 input wire [8:0] enroll_expert,input wire enroll_matrix,
 input wire [11:0] enroll_row,input wire [8:0] enroll_count,
 input wire owner_valid,input wire [72:0] owner_frame,
 input wire allocation_valid,input wire [72:0] allocation_frame,
 input wire landing_reserved,input wire [72:0] landing_frame,
 input wire provider_drained,publication_checked,input wire [72:0] publication_frame,
 input wire grant,output wire lease_v,quiet,release_v,input wire release_r,
 output wire publication_v,input wire publication_r,input wire [72:0] publication_owner,
 input wire [AW-1:0] xbase,ubase,wbase,ybase,gain_base,
 input wire [511:0] comb,input wire [127:0] post_pre,input wire [31:0] n_f,eps,lim,
 input wire [(RD?RD/2:1)*32-1:0] cos_t,sin_t,
 output wire [4*N*AW-1:0] rd_addr,output wire [4*N-1:0] rd_re,
 output wire [8*N-1:0] rd_src,input wire [4*N*32-1:0] rd_q,
 output wire [N-1:0] vm_we,output wire [N*AW-1:0] vm_waddr,
 output wire [N*32-1:0] vm_wdata,
 output wire q_valid,output wire [7:0] q_index,output wire [N*8-1:0] q_codes,
 output wire [(N/32)*10-1:0] q_exp,output wire [N*16-1:0] q_bf16,
 output wire [15:0] reserve_events,output wire [72:0] held_frame,
 output wire retained,fault,ce,due
);
 generate if(!ENABLE)begin:g_off
 assign warm_ack=0;assign enroll_r=0;assign lease_v=0;assign quiet=1;assign release_v=0;
 assign publication_v=0;assign rd_addr=0;assign rd_re=0;assign rd_src=0;
 assign vm_we=0;assign vm_waddr=0;assign vm_wdata=0;assign q_valid=0;assign q_index=0;
 assign q_codes=0;assign q_exp=0;assign q_bf16=0;assign reserve_events=0;
 assign held_frame=0;assign retained=0;assign fault=0;assign ce=0;assign due=0;
 end else begin:g_on
 wire [4*N*AW-1:0] child_rd_addr;wire [4*N-1:0] child_rd_re;
 wire [8*N-1:0] child_rd_src;wire [N-1:0] child_vm_we;
 wire [N*AW-1:0] child_vm_waddr;wire [N*32-1:0] child_vm_wdata;
 wire child_q_valid;wire [7:0] child_q_index;
 wire [N*8-1:0] child_q_codes;wire [(N/32)*10-1:0] child_q_exp;wire [N*16-1:0] child_q_bf16;
 assign rd_addr=child_rd_addr;assign rd_src=child_rd_src;
 assign rd_re=child_rd_re&{4*N{!fault}};
 assign vm_waddr=child_vm_waddr;assign vm_wdata=child_vm_wdata;
 assign vm_we=child_vm_we&{N{!fault}};
 assign q_valid=child_q_valid&&!fault;assign q_index=child_q_index;
 assign q_codes=child_q_codes;assign q_exp=child_q_exp;assign q_bf16=child_q_bf16;
 wire sr,start_v,start_r,finish_r,complete_v,issued,stage_fault;
 wire child_busy,child_done,child_fault;wire [31:0] child_id;
 wire source_match=allocation_valid&&allocation_frame==held_frame;
 wire sink_match=landing_reserved&&landing_frame==held_frame;
 wire finish_match=child_id==held_frame[31:0];
 // Poison the SAME coded descriptor on bad child identity or wrong attempted
 // caller release; no raw fault/identity shadow and no accepted foreign ACK.
 wire bad_lease=retained&&(!source_match||!sink_match||(issued&&!grant));
 wire bad_child=bad_lease||child_fault||(child_done&&!finish_match);
 wire bad_release=retained&&publication_r&&publication_owner!=held_frame;
 wire live_owner=owner_valid&&owner_frame==held_frame;
 wire permission=grant&&live_owner&&source_match&&sink_match&&!stage_fault&&!bad_child;
 wire producer_done=provider_drained&&(!child_busy||child_done)&&!bad_child;
 wire consumer_done=!issued||(publication_checked&&publication_frame==held_frame);
 wire admit=allocation_valid&&allocation_frame==enroll_frame&&landing_reserved&&landing_frame==enroll_frame;
 assign enroll_r=sr&&admit;
 assign fault=stage_fault||bad_child||bad_release;
 assign lease_v=retained;
 assign quiet=!issued&&provider_drained;
 assign publication_v=complete_v&&!fault&&release_r;
 assign release_v=complete_v&&!fault&&publication_r&&publication_owner==held_frame;
 wire complete_accept=release_v&&release_r;
 ot_hbm_integrated_stage_join #(.ENABLE(1)) u_stage(
 .clk(clk),.por_n(por_n),.warm_req(warm_req),.warm_ack(warm_ack),
 .enroll_v(enroll_v&&admit),.enroll_r(sr),.enroll_frame(enroll_frame),
 .enroll_pc(enroll_pc),.enroll_op(enroll_op),.enroll_source(enroll_source),
 .enroll_expert(enroll_expert),.enroll_matrix(enroll_matrix),.enroll_row(enroll_row),.enroll_count(enroll_count),
 .owner_valid(owner_valid&&!bad_child&&!bad_release),.owner_frame(owner_frame),.source_permit(permission),
 .start_v(start_v),.start_r(start_r),.finish_v(child_done&&!bad_child&&finish_match),.finish_r(finish_r),
 .producer_drained(producer_done),.consumer_drained(consumer_done),
 .complete_v(complete_v),.complete_r(complete_accept),.retained(retained),.issued(issued),
 .ce(ce),.due(due),.fault(stage_fault),.held_frame(held_frame),.held_pc(),.held_op(),
 .held_source(),.held_expert(),.held_matrix(),.held_row(),.held_count());
 ot_hbm_integrated_norm_vm #(.ENABLE(1),.KIND(KIND),.N(N),.D(D),.RD(RD),.AW(AW),
 .PUBLISH_QUANT(PUBLISH_QUANT),.ROUTED(ROUTED),.LM(5),.LA(6),.RW(RW),.BW(BW),.BCAST(BCAST),.RET(RET),
 .RXS(1),.SXC(1),.FREG(1),.HOLD_COMPLETION(1)) u_norm(
 .clk(clk),.rst_n(por_n),.cmd_valid(start_v),.cmd_ready(start_r),
 .completion_ready(finish_r&&!bad_child&&finish_match),
 .source_ready(permission),.landing_reserved(sink_match&&grant&&!stage_fault&&!bad_child),
 .busy(child_busy),.done(child_done),.fault(child_fault),.job_id(held_frame[31:0]),
 .xbase(xbase),.ubase(ubase),.wbase(wbase),.ybase(ybase),.gain_base(gain_base),
 .comb(comb),.post_pre(post_pre),.n_f(n_f),.eps(eps),.lim(lim),.cos_t(cos_t),.sin_t(sin_t),
 .rd_addr(child_rd_addr),.rd_re(child_rd_re),.rd_src(child_rd_src),.rd_q(rd_q),
 .vm_we(child_vm_we),.vm_waddr(child_vm_waddr),.vm_wdata(child_vm_wdata),.q_valid(child_q_valid),.q_index(child_q_index),
 .q_codes(child_q_codes),.q_exp(child_q_exp),.q_bf16(child_q_bf16),.completion_id(child_id),.reserve_events(reserve_events));
 end endgenerate
endmodule
`default_nettype wire
