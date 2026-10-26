`timescale 1ns/1ps
// SQ-C2-N59 (10-21): behavioural bench of the Q die's BOUND native59 service child qfd_native59_svc_obs1 at the kit
// parameters (HEAD_PREP 1, NU 4, ROPE 1, USER_BIND 1, MCTX 1, EMB_RELAY 1, RECV_INPUTS 1, LOCAL32 1).
//  (1) lockstep: every output shared with the legacy source qfd_native59_svc (same parameters; the obs1 header says
//      "legacy source remains unchanged") is compared on every edge under random stimulus (biased valids, random wide
//      payloads, random reset pulses).  (2) directed head-prepare scoreboard, independent model: a filler head-prepare
//      (user 1..3) yields head_descriptor_v exactly HP_FILL_EDGES edges later with tag {seq,user,6'd0,token,pos[12:0],6'd0},
//      seq = 0 on a user's first fill and +1 per later fill; a host head-prepare (user 0) followed by a matching host
//      epoch yields the host descriptor {tag[58:43],6'd0,tag[36:0]}; no other descriptor pulses.  (3) completed_tag is
//      X-free and holds between completions.  Verdict lines: N59OBS_PASS / N59OBS_FAIL <why>.
module tb_n59_svc_obs1_hp #(parameter integer SEED=1, parameter integer NRND=6000) ();
 localparam integer HP_FILL_EDGES=3, HP_HOST_EDGES=4;
 reg ck=0, rst_n=0;
 reg host_epoch_valid,host_fused_capability; reg[15:0]host_epoch; reg[58:0]host_tag; reg[1:0]host_generation;
 reg layer_context_v; reg[5:0]command_stage;
 reg head_prepare_v; reg[1:0]head_prepare_user; reg[17:0]head_prepare_token,head_prepare_position;
 reg[17:0]native_token,native_position; reg[379:0]native_cmd; reg[547:0]dd_i;
 reg kv_word_slot; reg[1:0]kv_word_index; reg kv_x3_slot;
 reg qb_v; reg[4:0]qb_beat; reg[511:0]qb_row; reg qb_full,qb_committed,qb_bad;
 reg[1:0]tx_user,rx_user; reg tx_slot; reg[3:0]tx_slot_kind; reg[4:0]tx_slot_beat;
 reg native_rx_v; reg[547:0]native_rx_payload; reg rx_slot; reg[3:0]rx_slot_kind; reg[4:0]rx_slot_beat;
 reg[511:0]emb_code_q; reg[15:0]emb_scale_q; reg visibility_slot,complete_slot;
 // outputs: d = obs1 (DUT), r = legacy reference
 wire[523:0]d_x3,r_x3; wire[58:0]d_x3i,r_x3i; wire[1:0]d_x3g,r_x3g;
 wire d_txv,r_txv; wire[547:0]d_txp,r_txp;
 wire d_hdv,r_hdv; wire[58:0]d_hdt,r_hdt; wire[1:0]d_hdg,r_hdg;
 wire[519:0]d_dr,r_dr; wire d_ecre,r_ecre; wire[23:0]d_eca,r_eca; wire d_esre,r_esre; wire[17:0]d_esa,r_esa;
 wire d_cpl,r_cpl; wire[58:0]d_cpt; wire[94:0]d_ret,r_ret; wire d_flt,r_flt;
`define N59_PORTS(P) \
  .ck(ck),.rst_n(rst_n),.host_epoch_valid(host_epoch_valid),.host_fused_capability(host_fused_capability),.host_epoch(host_epoch), \
  .host_tag(host_tag),.host_generation(host_generation),.layer_context_v(layer_context_v),.command_stage(command_stage), \
  .head_prepare_v(head_prepare_v),.head_prepare_user(head_prepare_user),.head_prepare_token(head_prepare_token),.head_prepare_position(head_prepare_position), \
  .native_token(native_token),.native_position(native_position),.native_cmd(native_cmd),.dd_i(dd_i), \
  .kv_word_slot(kv_word_slot),.kv_word_index(kv_word_index),.kv_x3_slot(kv_x3_slot), \
  .x3(P``_x3),.x3_identity(P``_x3i),.x3_generation(P``_x3g), \
  .qb_v(qb_v),.qb_beat(qb_beat),.qb_row(qb_row),.qb_full(qb_full),.qb_committed(qb_committed),.qb_bad(qb_bad), \
  .tx_user(tx_user),.rx_user(rx_user),.tx_slot(tx_slot),.tx_slot_kind(tx_slot_kind),.tx_slot_beat(tx_slot_beat), \
  .native_tx_v(P``_txv),.native_tx_payload(P``_txp), \
  .head_descriptor_v(P``_hdv),.head_descriptor_tag(P``_hdt),.head_descriptor_generation(P``_hdg), \
  .native_rx_v(native_rx_v),.native_rx_payload(native_rx_payload),.rx_slot(rx_slot),.rx_slot_kind(rx_slot_kind),.rx_slot_beat(rx_slot_beat), \
  .dr_o(P``_dr),.emb_code_re(P``_ecre),.emb_code_addr(P``_eca),.emb_scale_re(P``_esre),.emb_scale_addr(P``_esa), \
  .emb_code_q(emb_code_q),.emb_scale_q(emb_scale_q),.visibility_slot(visibility_slot),.complete_slot(complete_slot), \
  .completed(P``_cpl),.native_ret(P``_ret),.fault(P``_flt)
 qfd_native59_svc_obs1 #(.HEAD_PREP(1),.NU(4),.ROPE(1),.USER_BIND(1),.MCTX(1),.EMB_RELAY(1),.RECV_INPUTS(0),.LOCAL32(0))
  u_dut(`N59_PORTS(d),.completed_tag(d_cpt));
 qfd_native59_svc #(.HEAD_PREP(1),.NU(4),.ROPE(1),.USER_BIND(1),.MCTX(1),.EMB_RELAY(1),.RECV_INPUTS(0),.LOCAL32(0))
  u_ref(`N59_PORTS(r));
 always #1 ck=~ck;
 integer errs=0, cyc=0, nhd=0, nhd_exp=0, ncpl=0, nact=0;
 task automatic err(input string s); begin errs=errs+1; if(errs<=8)$display("N59OBS_ERR cyc=%0d %s",cyc,s); end endtask
 function automatic [31:0] rb(input integer one_in); rb=($urandom%one_in)==0; endfunction
 task automatic rnd_wide(output reg[547:0] v); integer i; begin for(i=0;i<548;i=i+32)v[i+:32]=$urandom; end endtask
 task automatic quiet; begin
  host_epoch_valid=0;host_fused_capability=0;host_epoch=0;host_tag=0;host_generation=2'd1;layer_context_v=0;command_stage=0;
  head_prepare_v=0;head_prepare_user=0;head_prepare_token=0;head_prepare_position=0;native_token=0;native_position=0;native_cmd=0;dd_i=0;
  kv_word_slot=0;kv_word_index=0;kv_x3_slot=0;qb_v=0;qb_beat=0;qb_row=0;qb_full=0;qb_committed=0;qb_bad=0;tx_user=0;rx_user=0;
  tx_slot=0;tx_slot_kind=0;tx_slot_beat=0;native_rx_v=0;native_rx_payload=0;rx_slot=0;rx_slot_kind=0;rx_slot_beat=0;emb_code_q=0;
  emb_scale_q=0;visibility_slot=0;complete_slot=0; end endtask
 task automatic rnd_inputs; reg[547:0]w; begin
  host_epoch_valid=rb(4);host_fused_capability=rb(2);host_epoch=$urandom;host_tag={$urandom,$urandom};host_generation=$urandom;
  layer_context_v=rb(4);command_stage=$urandom%40;head_prepare_v=rb(16);head_prepare_user=$urandom;
  head_prepare_token=$urandom%160000;head_prepare_position=$urandom%9000;native_token=$urandom;native_position=$urandom;
  rnd_wide(w);native_cmd=w[379:0];native_cmd[0]=rb(8);rnd_wide(w);dd_i=w;dd_i[547]=rb(4);
  kv_word_slot=rb(4);kv_word_index=$urandom;kv_x3_slot=rb(4);qb_v=rb(4);qb_beat=$urandom;rnd_wide(w);qb_row=w[511:0];
  qb_full=rb(2);qb_committed=rb(2);qb_bad=rb(32);tx_user=$urandom;rx_user=$urandom;tx_slot=rb(4);tx_slot_kind=$urandom;
  tx_slot_beat=$urandom;native_rx_v=rb(4);rnd_wide(w);native_rx_payload=w;rx_slot=rb(4);rx_slot_kind=$urandom;rx_slot_beat=$urandom;
  rnd_wide(w);emb_code_q=w[511:0];emb_scale_q=$urandom;visibility_slot=rb(8);complete_slot=rb(8);
  if(rb(120))rst_n=0;else rst_n=1; end endtask
 // ---- lockstep compare (every edge, after the edge settles)
 reg[58:0]cpt_prev; reg cpl_prev;
 always @(negedge ck) begin
  cyc=cyc+1;
  if(d_x3!==r_x3||d_x3i!==r_x3i||d_x3g!==r_x3g)err("x3 differs");
  if(d_txv!==r_txv||d_txp!==r_txp)err("native_tx differs");
  if(d_hdv!==r_hdv||d_hdt!==r_hdt||d_hdg!==r_hdg)err("head_descriptor differs");
  if(d_dr!==r_dr)err("dr_o differs");
  if(d_ecre!==r_ecre||d_eca!==r_eca||d_esre!==r_esre||d_esa!==r_esa)err("emb fetch differs");
  if(d_cpl!==r_cpl)err("completed differs");
  if(d_ret!==r_ret)err("native_ret differs");
  if(d_flt!==r_flt)err("fault differs");
  if($isunknown(d_cpt))err("completed_tag X");
  if(rst_n&&!d_cpl&&!cpl_prev&&d_cpt!==cpt_prev&&cyc>4)err("completed_tag moved without a completion");
  cpt_prev=d_cpt; cpl_prev=d_cpl; if(d_cpl)ncpl=ncpl+1;
  if(d_txv||d_x3[523]||d_ecre||d_hdv)nact=nact+1;
 end
 // ---- directed head-prepare scoreboard (independent model)
 reg[13:0]seqm[0:3]; reg seen[0:3];
 reg exp_v[0:15]; reg[58:0]exp_t[0:15];      // expected descriptor per future edge (ring)
 integer edge_no=0, k;
 task automatic expect_at(input integer dly, input [58:0] t); begin
  if(exp_v[(edge_no+dly)%16])err("model: two descriptors expected on one edge");
  exp_v[(edge_no+dly)%16]=1; exp_t[(edge_no+dly)%16]=t; nhd_exp=nhd_exp+1; end endtask
 reg checking=0;
 always @(negedge ck) if(checking) begin
  if(d_hdv!==exp_v[edge_no%16])err($sformatf("descriptor valid %0d expected %0d at edge %0d",d_hdv,exp_v[edge_no%16],edge_no));
  else if(d_hdv&&(d_hdt!==exp_t[edge_no%16]||d_hdg!==2'd1))err($sformatf("descriptor tag %h expected %h",d_hdt,exp_t[edge_no%16]));
  if(d_hdv)nhd=nhd+1;
  exp_v[edge_no%16]=0; edge_no=edge_no+1;
 end
 task automatic fill(input [1:0]u, input [17:0]tok, input [17:0]pos); reg[13:0]s; begin
  s=seen[u]?seqm[u]+14'd1:seqm[u]; seqm[u]=s; seen[u]=1;
  head_prepare_v=1;head_prepare_user=u;head_prepare_token=tok;head_prepare_position=pos;
  expect_at(HP_FILL_EDGES,{s,u,6'd0,tok,pos[12:0],6'd0});
  @(posedge ck); #0.1 head_prepare_v=0; end endtask
 task automatic host(input [15:0]ep, input [17:0]tok, input [17:0]pos); reg[58:0]t; begin
  t={ep,6'd0,tok,pos[12:0],6'd0};
  host_epoch_valid=1;host_fused_capability=1;host_epoch=ep;host_tag=t;
  head_prepare_v=1;head_prepare_user=0;head_prepare_token=tok;head_prepare_position=pos;
  expect_at(HP_HOST_EDGES,{t[58:43],6'd0,t[36:0]});
  @(posedge ck); #0.1 head_prepare_v=0;
  repeat(HP_HOST_EDGES+2)@(posedge ck); #0.1 host_epoch_valid=0;host_fused_capability=0; end endtask
 initial begin
  void'($urandom(SEED));
  for(k=0;k<4;k=k+1)begin seqm[k]=0;seen[k]=0;end for(k=0;k<16;k=k+1)begin exp_v[k]=0;exp_t[k]=0;end
  quiet; rst_n=0; repeat(6)@(posedge ck); #0.1 rst_n=1; repeat(6)@(posedge ck); #0.1;
  // directed: fills for users 1..3 (several per user, back-to-back and spaced), host prepares with matching epochs
  checking=1;
  fill(2'd1,18'd17,18'd5); fill(2'd2,18'd151935,18'd8191); @(posedge ck); #0.1 fill(2'd1,18'd99,18'd6);
  repeat(4)@(posedge ck); #0.1;
  for(k=0;k<12;k=k+1)begin fill(2'(1+k%3),18'($urandom%151936),18'($urandom%8192)); if(k%2)begin @(posedge ck); #0.1; end end
  repeat(6)@(posedge ck); #0.1;
  host(16'h1234,18'd4242,18'd77); repeat(3)@(posedge ck); #0.1;
  host(16'hbeef,18'd100000,18'd8000); repeat(3)@(posedge ck); #0.1;
  fill(2'd3,18'd1,18'd2); repeat(8)@(posedge ck); #0.1;
  checking=0;
  if(nhd!=nhd_exp||nhd_exp!=18)err($sformatf("directed descriptors seen %0d expected %0d",nhd,nhd_exp));
  // random lockstep
  repeat(NRND)begin rnd_inputs; @(posedge ck); #0.1; end
  quiet; rst_n=1; repeat(20)@(posedge ck); #0.1;
  $display("N59OBS activity edges=%0d descriptors=%0d completions=%0d",nact,nhd,ncpl);
  if(nact<NRND/40)err("random phase too quiet (no activity)");
  if(errs==0)$display("N59OBS_PASS seed=%0d",SEED); else $display("N59OBS_FAIL errors=%0d",errs);
  $finish;
 end
endmodule
