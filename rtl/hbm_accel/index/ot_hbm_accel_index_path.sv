`timescale 1ps/1fs
// Actual dedicated HBM index instances; fixed source total order and exact
// arithmetic. Query data is actual SU/VM output. Key metadata contains literal
// TP96 global IDs, never ROM stack-major reassociation. Selection SRAM ports
// and candidate consumer are real external ports, not ready/idle assumptions.
module ot_hbm_accel_index_path #(
 parameter integer ENABLE=0,SOURCE_VM_ENABLE=0,NS=16,NK=4,Q=4,W=16,IW=20,K=512,AW=8,FPL=7,FML=5,QL=5
)(
 input wire clk,por_n,start,output wire start_ready,
 input wire [31:0] source_job,input wire[3:0] source_gen,input wire[19:0] source_pos,input wire[6:0] source_rank,
 output wire[31:0] held_job,output wire[3:0] held_gen,output wire[19:0] held_pos,output wire[6:0] held_rank,
 input wire q_block_v,output wire q_block_r,input wire[4:0] q_head,input wire[1:0] q_block,
 input wire[1023:0] q_data,input wire[15:0] q_weight,
 input wire[31:0] original_q_base,rotated_q_base,scaled_weight_base,
 input wire[7:0] source_tail_words,
 output wire vm_read_v,input wire vm_read_r,output wire[31:0] vm_read_addr,
 output wire[7:0] vm_read_tag,output wire[5:0] vm_read_words,
 output wire[31:0] vm_read_job,output wire[3:0] vm_read_gen,
 output wire[19:0] vm_read_pos,output wire[6:0] vm_read_rank,
 input wire vm_rsp_v,output wire vm_rsp_r,input wire[1023:0] vm_rsp_data,
 input wire[7:0] vm_rsp_tag,input wire[31:0] vm_rsp_job,input wire[3:0] vm_rsp_gen,
 input wire[19:0] vm_rsp_pos,input wire[6:0] vm_rsp_rank,
 input wire k_v,output wire k_r,input wire k_last,
 input wire[NS*NK-1:0] k_lv,k_ref,k_keep,
 input wire[NS*NK*IW-1:0] k_idx,input wire[NS*NK*544-1:0] k_data,
 output wire candidate_v,input wire candidate_r,
 output wire[Q-1:0] candidate_last,output wire[Q*W-1:0] candidate_lv,
 output wire[Q*W*16-1:0] candidate_score,output wire[Q*W*IW-1:0] candidate_idx,
 input wire candidate_drained,
 output wire[Q-1:0] cand_out_v,input wire[Q-1:0] cand_out_r,
 output wire[Q-1:0] cand_out_last,output wire[Q*(W/8)-1:0] cand_out_lv,
 output wire[Q*(W/8)*16-1:0] cand_out_score,
 output wire[Q*(W/8)*(IW-3)-1:0] cand_out_block,
 output wire[Q-1:0] cand_mem_we,cand_mem_re,
 output wire[Q*10-1:0] cand_mem_waddr,cand_mem_raddr,
 output wire[Q*(W/8)*(14+IW)-1:0] cand_mem_wdata,
 input wire[Q*(W/8)*(14+IW)-1:0] cand_mem_rdata,
 output wire cand_replay_required,cand_overflow,
 output wire[Q*3*11-1:0] cand_stats,
 output wire[Q-1:0] out_v,input wire[Q-1:0] out_r,output wire[Q-1:0] out_last,
 output wire[Q*W-1:0] out_lv,output wire[Q*W*16-1:0] out_score,
 output wire[Q*W*IW-1:0] out_idx,output wire[Q*W-1:0] out_ninf,
 output wire[Q-1:0] mem_we,mem_re,output wire[Q*AW-1:0] mem_waddr,mem_raddr,
 output wire[Q*W*(17+IW)-1:0] mem_wdata,input wire[Q*W*(17+IW)-1:0] mem_rdata,
 output wire replay_required,overflow,
 output wire retained,output reg fault,output reg done,
 output wire[Q*3*(AW+1)-1:0] selector_stats
);
generate if(!ENABLE)begin:off
 assign start_ready=0;assign q_block_r=0;assign k_r=0;assign candidate_v=0;
 assign candidate_last=0;assign candidate_lv=0;assign candidate_score=0;assign candidate_idx=0;
 assign out_v=0;assign out_last=0;assign out_lv=0;assign out_score=0;assign out_idx=0;assign out_ninf=0;
 assign mem_we=0;assign mem_re=0;assign mem_waddr=0;assign mem_raddr=0;assign mem_wdata=0;
 assign cand_out_v=0;assign cand_out_last=0;assign cand_out_lv=0;
 assign cand_out_score=0;assign cand_out_block=0;assign cand_mem_we=0;assign cand_mem_re=0;
 assign cand_mem_waddr=0;assign cand_mem_raddr=0;assign cand_mem_wdata=0;
 assign cand_replay_required=0;assign cand_overflow=0;assign cand_stats=0;
 assign vm_read_v=0;assign vm_read_addr=0;assign vm_read_tag=0;assign vm_read_words=0;
 assign vm_read_job=0;assign vm_read_gen=0;assign vm_read_pos=0;assign vm_read_rank=0;assign vm_rsp_r=0;
 assign replay_required=0;assign overflow=0;assign retained=0;assign selector_stats=0;
 assign held_job=0;assign held_gen=0;assign held_pos=0;assign held_rank=0;
 always @*begin fault=0;done=0;end
end else begin:on
 initial if(NS*NK!=Q*W||NK>8||8%NK!=0||IW!=20||K!=512||Q!=4||W!=16||NS!=16||NK!=4)
  $fatal(1,"Source-selected HBM index geometry required");
 reg active,query_ready;
 reg[31:0] job;reg[3:0] generation;reg[19:0] position;reg[6:0] rank;
 reg[Q-1:0] emitted_last,emitted_cand_last,seen_input;
 reg[IW-1:0] previous_id[0:Q-1];
 assign held_job=job;assign held_gen=generation;assign held_pos=position;assign held_rank=rank;
 assign retained=active;
 wire qs_ready,qs_done,qs_fault,ql_v,ql_r,query_block_ready;
 wire source_ready,source_fault,source_done,source_block_v;
 wire[4:0] source_head;wire[1:0] source_block;
 wire[1023:0] source_data;wire[15:0] source_weight;
 assign q_block_r=!SOURCE_VM_ENABLE&&query_block_ready&&active&&!fault;
 wire[7:0] ql_head;wire[511:0] ql_codes;wire[31:0] ql_sc;wire[15:0] ql_w;
 assign start_ready=!active&&qs_ready&&source_ready&&!fault;
 wire begin_frame=start&&start_ready;
 if(SOURCE_VM_ENABLE)begin:native_vm
 ot_hbm_accel_index_query_source #(.ENABLE(1)) u_source(
 .clk(clk),.por_n(por_n),.start(begin_frame),.start_ready(source_ready),
 .source_job(source_job),.source_gen(source_gen),.source_pos(source_pos),.source_rank(source_rank),
 .original_q_base(original_q_base),.rotated_q_base(rotated_q_base),.scaled_weight_base(scaled_weight_base),.source_tail_words(source_tail_words),
 .read_v(vm_read_v),.read_r(vm_read_r),.read_addr(vm_read_addr),.read_tag(vm_read_tag),.read_words(vm_read_words),
 .read_job(vm_read_job),.read_gen(vm_read_gen),.read_pos(vm_read_pos),.read_rank(vm_read_rank),
 .rsp_v(vm_rsp_v),.rsp_r(vm_rsp_r),.rsp_data(vm_rsp_data),.rsp_tag(vm_rsp_tag),
 .rsp_job(vm_rsp_job),.rsp_gen(vm_rsp_gen),.rsp_pos(vm_rsp_pos),.rsp_rank(vm_rsp_rank),
 .block_v(source_block_v),.block_r(query_block_ready&&active&&!fault),.block_head(source_head),.block_number(source_block),
 .block_data(source_data),.head_weight(source_weight),.fault(source_fault),.done(source_done));
 end else begin:external_native_stream
 assign source_ready=1;assign source_fault=0;assign source_done=0;
 assign source_block_v=q_block_v;assign source_head=q_head;assign source_block=q_block;
 assign source_data=q_data;assign source_weight=q_weight;
 assign vm_read_v=0;assign vm_read_addr=0;assign vm_read_tag=0;assign vm_read_words=0;
 assign vm_read_job=0;assign vm_read_gen=0;assign vm_read_pos=0;assign vm_read_rank=0;assign vm_rsp_r=0;
 end
 ot_hbm_accel_index_query #(.ENABLE(1)) u_index_q(
 .clk(clk),.por_n(por_n),.start(begin_frame),.start_ready(qs_ready),
 .block_v(source_block_v&&active&&!fault),.block_r(query_block_ready),.block_head(source_head),.block_number(source_block),
 .block_data(source_data),.head_weight(source_weight),.ql_v(ql_v),.ql_r(ql_r),.ql_head(ql_head),
 .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.done(qs_done),.fault(qs_fault));
 wire sv,sr,sp;wire[NS-1:0] slast;wire[NS*NK-1:0] slv,sfault;
 wire[NS*NK*16-1:0] sval;wire[NS*NK*IW-1:0] sidx;
 wire input_ready;
 assign k_r=input_ready&&active&&query_ready&&!fault&&!invalid_ids;
 ot_hdc_v41x_idx_array_l #(.NS(NS),.NK(NK),.NB(4),.IH(32),.IW(IW),.MD(64),.FPL(FPL),.FML(FML),.QL(QL)) u_index_scores(
 .clk(clk),.rst_n(por_n),.ql_v(ql_v),.ql_ready(ql_r),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
 .i_valid(k_v&&active&&query_ready&&!fault&&!invalid_ids),.i_ready(input_ready),.i_last({NS{k_last}}),
 .i_kv(k_lv),.i_ref(k_ref),.i_keep(k_keep),.i_index(k_idx),.i_key(k_data),
 .o_valid(sv),.o_ready(sr),.o_last(slast),.o_kv(slv),.o_fault(sfault),.o_score(sval),.o_index(sidx),.protocol_fault(sp));
 wire[Q-1:0] select_ready,select_out_v;
 assign out_v=select_out_v & {Q{active&&!fault}};
 wire[Q-1:0] cand_ready,cand_valid;
 wire cand_busy,topk_busy;
 assign cand_out_v=cand_valid & {Q{active&&!fault}};
 wire atomic_ready=(&select_ready)&&(&cand_ready);
 assign candidate_v=sv&&active&&!fault&&atomic_ready;
 assign sr=active&&!fault&&atomic_ready&&candidate_r;
 // Raw scored tap is an explicitly accepted third consumer, not a payload
 // substitute. All three see the identical accepted beat; candidate SRAM and
 // actual selected maxima/IDs feed the native collective through cand_out_*.
 assign candidate_last={Q{slast[0]}};assign candidate_lv=slv;assign candidate_score=sval;assign candidate_idx=sidx;
 ot_hdc_v41x_sel #(.Q(Q),.W(W),.IW(IW),.K(K),.AW(AW)) u_topk_local(
 .clk(clk),.rst_n(por_n),.in_valid({Q{sv&&sr}}),.in_ready(select_ready),.in_last({Q{slast[0]}}),
 .in_lv(slv),.in_val(sval),.in_idx(sidx),.in_k(10'd512),
 .out_valid(select_out_v),.out_ready(out_r & {Q{active&&!fault}}),.out_last(out_last),.out_lv(out_lv),.out_val(out_score),.out_idx(out_idx),.out_ninf(out_ninf),
 .mem_we(mem_we),.mem_waddr(mem_waddr),.mem_wdata(mem_wdata),.mem_re(mem_re),.mem_raddr(mem_raddr),.mem_rdata(mem_rdata),
 .rep_req(replay_required),.ovf(overflow),.busy(topk_busy),.stats(selector_stats));
 ot_hbm_accel_index_candidate #(.ENABLE(1)) u_cand_local(
 .clk(clk),.rst_n(por_n),.held_valid(active&&!fault),
 .held_job(job),.held_gen(generation),.held_pos(position),.held_rank(rank),
 .out_job(),.out_gen(),.out_pos(),.out_rank(),
 .in_valid({Q{sv&&sr}}),.in_ready(cand_ready),.in_last({Q{slast[0]}}),
 .in_lv(slv),.in_val(sval),.in_idx(sidx),.in_k(12'd2048),
 .out_valid(cand_valid),.out_ready(cand_out_r & {Q{active&&!fault}}),
 .out_last(cand_out_last),.out_lv(cand_out_lv),.out_val(cand_out_score),.out_blk(cand_out_block),
 .mem_we(cand_mem_we),.mem_waddr(cand_mem_waddr),.mem_wdata(cand_mem_wdata),
 .mem_re(cand_mem_re),.mem_raddr(cand_mem_raddr),.mem_rdata(cand_mem_rdata),
 .rep_req(cand_replay_required),.ovf(cand_overflow),.busy(cand_busy),.stats(cand_stats));
 // Unsupported overflow replay is an explicit refusal, never a false native PASS.
 // Source replay/retention is an actual caller obligation, not automatic DUT input.
 integer l,j;
 reg invalid_ids;
 always @*begin
  invalid_ids=0;
  for(l=0;l<NS*NK;l=l+1)if(k_lv[l])begin
   // Four source-owned block ranges, each <=342 blocks at full 1M TP96.
   // This is an actual ingress bound, not an assumed balanced host array.
   if(((k_idx[l*IW+:IW]>>3)/96)/342 != l/W)invalid_ids=1;
   if(k_idx[l*IW+:IW]>position||((k_idx[l*IW+:IW]>>3)%96)!=rank)invalid_ids=1;
   // Candidate max consumes blocks8. A partial final block cannot be
   // continued as another block on a later beat, nor paired with another ID.
   if((k_idx[l*IW+:IW]&20'd7)!=(l%8))invalid_ids=1;
   if((l%8)!=0 && (!k_lv[(l/8)*8] || k_idx[l*IW+:IW]!=k_idx[((l/8)*8)*IW+:IW]+(l%8)))invalid_ids=1;
   if((l%NK)!=0 && (!k_lv[(l/NK)*NK] || k_idx[l*IW+:IW]!=k_idx[((l/NK)*NK)*IW+:IW]+(l%NK)))invalid_ids=1;
   if((l%W)==0 && seen_input[l/W] && k_idx[l*IW+:IW]<=previous_id[l/W])invalid_ids=1;
   if((l%W)!=0 && (!k_lv[l-1] || k_idx[l*IW+:IW]<=k_idx[(l-1)*IW+:IW]))invalid_ids=1;
  end
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin active<=0;query_ready<=0;job<=0;generation<=0;position<=0;rank<=0;emitted_last<=0;emitted_cand_last<=0;seen_input<=0;fault<=0;done<=0;
    for(j=0;j<Q;j=j+1)previous_id[j]<=0;end
  else begin
   done<=0;
   if(begin_frame)begin active<=1;query_ready<=0;job<=source_job;generation<=source_gen;position<=source_pos;rank<=source_rank;emitted_last<=0;emitted_cand_last<=0;seen_input<=0;
    if(source_rank>=96)fault<=1;end
   if(qs_done)query_ready<=1;
   if(k_v&&k_r)for(j=0;j<NS*NK;j=j+1)if(k_lv[j])begin
    previous_id[j/W]<=k_idx[j*IW+:IW];seen_input[j/W]<=1;
   end
   if(qs_fault||source_fault||sp||(sv&&sr&&|(sfault&slv))||(k_v&&active&&query_ready&&invalid_ids)||replay_required||overflow||cand_replay_required||cand_overflow)fault<=1;
   if(!begin_frame)begin
    emitted_last<=emitted_last|(out_v&out_r&out_last);
    emitted_cand_last<=emitted_cand_last|(cand_out_v&cand_out_r&cand_out_last);
   end
   if(active&&(&(emitted_last|(out_v&out_r&out_last)))&&(&emitted_cand_last)&&!cand_busy&&!topk_busy&&candidate_drained&&!fault)begin active<=0;done<=1;end
  end
 end
end endgenerate
endmodule
