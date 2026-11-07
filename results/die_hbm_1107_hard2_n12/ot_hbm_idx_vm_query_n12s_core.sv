`default_nettype none
// ---------------------------------------------------------------------------
// HBM-HARD-2-N12 2026-11-07: n12 operand reader core, form vN. n12r core (HBM-HARD-1-IDX, forms vL/vM) reduced to LEGAL
// requests only. Fixes two measured problems of vM. Same ports, same cycle at every output, PIN CYCLES 0.
//  (1) FF hold. 354 of 355 internal misses are zero-logic flop pairs, natural slack about +3.5 ps; 273 of them are the
//      181-stage tag line. The tag per stage goes from 39 bits to 10: {query valid, weight valid, high-bank bit,
//      query_index}. A legal query reads banks {0..3} or {4..7}, a legal weight read banks {0,1}, so the per-bank
//      valid and code bits are redundant. 5249 fewer flops, 1086 of them large reset flops.
//  (2) TT -3.63 qsec_r[1] -> face_fault. The four 16-bit sector adders become one: a legal query sector has [1:0]==0,
//      so the four sectors share bits [15:2].
// LEGAL means: not both slots, query_sector[1:0]==0 on a query, weight_sector[2:0]==0 on a weight read. An illegal
// request sets `bad` at the same edge as the request registers. So fault is cycle exact against the old core on every
// stimulus, and all other outputs are cycle exact against the old core until fault=1 (fault is sticky until reset).
// Data flops keep no reset, as before; reset is held >=64 clk by the die boot.
(* keep_hierarchy, keep *)
module ot_hbm_idx_n12s_rep #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_hbm_idx_vm_query_n12s_core #(parameter integer VM_RT_EXTRA=0)(
 input wire clk,rst_n,input wire[1:0]sid,
 input wire weight_slot,query_slot,input wire[6:0]query_index,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg block_v,output reg[4:0]block_head,output reg[1:0]block_number,
 output reg[1023:0]block_data,output reg[15:0]head_weight,
 output wire fault
);
 localparam integer D=8+VM_RT_EXTRA;
 localparam integer REP=8; // select replicas per 256-bit word (32 bits each)
 wire[1:0]rst_r;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_r));
 // ---- request decode: one adder; sector bits [15:2] of a legal query
 wire[13:0]qsum=query_sector[15:2]+14'(query_index);
 wire qhi=qsum[0];
 wire q_sid_ok=qsum[13]||qsum[12:11]==sid;
 wire w_sid_ok=weight_sector[15]||weight_sector[14:13]==sid;
 wire sid_bad=(query_slot&&!q_sid_ok)||(weight_slot&&!w_sid_ok);
 wire[7:0]q_req={{4{query_slot&&qhi}},{4{query_slot&&!qhi}}};
 wire[7:0]w_req={6'd0,{2{weight_slot}}};
 // ---- tag line
 reg tq[0:D-1];reg tw[0:D-1];
 reg thi[0:D-1];reg[6:0]tqi[0:D-1];
 wire tq_e=tq[D-1];wire tw_e=tw[D-1];wire thi_e=thi[D-1];wire[6:0]qi_e=tqi[D-1];
 wire[7:0]expected={{4{tq_e&&thi_e}},{2{tq_e&&!thi_e}},{2{(tq_e&&!thi_e)||tw_e}}};
 // ---- VM face
 reg[7:0]rq_v;reg[127:0]rq_s;reg[2047:0]res_d;reg face_fault;
 wire[7:0]rrv;
 for(genvar b=0;b<8;b=b+1)begin:g_pack
  assign vm_rq[17*b+:17]={rq_v[b],rq_s[16*b+:16]};
  assign rrv[b]=vm_rr[257*b+256];
 end
 always @(posedge clk or negedge rst_r[1])begin
  if(!rst_r[1])begin
   rq_v<=0;face_fault<=0;
   for(integer d=0;d<D;d=d+1)begin tq[d]<=0;tw[d]<=0;end
  end else begin
   for(integer d=1;d<D;d=d+1)begin tq[d]<=tq[d-1];tw[d]<=tw[d-1];end
   tq[0]<=query_slot&&q_sid_ok;tw[0]<=weight_slot&&w_sid_ok;
   rq_v<=sid_bad?8'd0:(q_req|w_req);
   if(sid_bad||rrv!=expected)face_fault<=1;
  end
 end
 always @(posedge clk)begin
  for(integer d=1;d<D;d=d+1)begin thi[d]<=thi[d-1];tqi[d]<=tqi[d-1];end
  thi[0]<=qhi;tqi[0]<=query_index;
  for(integer b=0;b<8;b=b+1)begin
   rq_s[16*b+:16]<=({16{q_req[b]}}&{qsum,2'(b)})|({16{w_req[b]}}&{weight_sector[15:3],2'd0,1'(b)});
   res_d[256*b+:256]<=vm_rr[257*b+:256];
  end
 end
 // ---- early decode from the D side of the old res_v / result_tag
 wire[3:0]hit_lo={4{tq_e&&!thi_e}}&rrv[3:0];
 wire[3:0]hit_hi={4{tq_e&&thi_e}}&rrv[7:4];
 wire[3:0]parts_d=hit_lo|hit_hi;
 wire[1:0]wv_d={2{tw_e}}&rrv[1:0];
 wire en_d=|parts_d;
 // ---- registered selects, one replica per 32 data bits
 reg[511:0]weights;
 for(genvar g=0;g<REP;g=g+1)begin:g_rep
  for(genvar p=0;p<4;p=p+1)begin:g_p
   wire[2:0]c;
   ot_hbm_idx_n12s_rep #(.W(3)) u_r(.clk(clk),.d({en_d,hit_hi[p],hit_lo[p]}),.q(c));
   always @(posedge clk)if(c[2])block_data[p*256+g*32+:32]<=({32{c[0]}}&res_d[p*256+g*32+:32])|({32{c[1]}}&res_d[(p+4)*256+g*32+:32]);
  end
  for(genvar w=0;w<2;w=w+1)begin:g_w
   wire c;
   ot_hbm_idx_n12s_rep #(.W(1)) u_r(.clk(clk),.d(wv_d[w]),.q(c));
   always @(posedge clk)if(c)weights[w*256+g*32+:32]<=res_d[w*256+g*32+:32];
  end
 end
 reg[3:0]parts;reg[1:0]wv;reg[6:0]qid;reg en;
 always @(posedge clk)begin parts<=parts_d;wv<=wv_d;qid<=qi_e;en<=en_d;end
 reg[15:0]hw_sel;
 always @*begin
  hw_sel=0;
  for(integer h=0;h<32;h=h+1)if(qid[6:2]==5'(h))hw_sel=weights[h*16+:16];
 end
 // ---- control, reset as before
 reg[1:0]weight_seen;reg bad;
 assign fault=bad||face_fault;
 always @(posedge clk or negedge rst_r[0])begin
  if(!rst_r[0])begin weight_seen<=0;bad<=0;block_v<=0;end
  else begin
   block_v<=en;
   if(weight_slot&&query_slot)bad<=1;
   if(weight_slot&&weight_sector[2:0]!=0)bad<=1;
   if(query_slot&&query_sector[1:0]!=0)bad<=1;
   if(wv[0])weight_seen[0]<=1;
   if(wv[1])weight_seen[1]<=1;
   if(en)begin
    if(parts!=4'hf||weight_seen!=2'b11)bad<=1;
   end
  end
 end
 always @(posedge clk)if(en)begin
  block_head<=qid[6:2];block_number<=qid[1:0];head_weight<=hw_sel;
 end
endmodule
`default_nettype wire
