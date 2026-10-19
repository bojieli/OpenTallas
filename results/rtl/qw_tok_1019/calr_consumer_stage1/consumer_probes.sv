`timescale 1ns/1ps
// Prepared passive source probes. NOT YET ELABORATED OR EXECUTED in connected
// CALR/CTLM->ME/XPF vehicle. No functional ports or handles are introduced.
module qw_me_probe #(parameter G=4,AW=24)(input clk,rst_n,go,ready,m_v,ov,
 input[G-1:0]x_re,input[G*AW-1:0]x_addr,input[G*32-1:0]x_q);
 wire probe_enabled=$test$plusargs("QW_PROBE");
 integer edge_id=0,epoch=0;reg was_reset=1;
 always @(posedge clk)begin
  edge_id=edge_id+1;
  if(!rst_n)was_reset=1;
  else begin
   if(was_reset)begin epoch=epoch+1;was_reset=0;end
   if(probe_enabled&&go&&ready)$display("QWEVENT|%0t|%m|%0d|%0d|ME_ACCEPT|0|0",$time,edge_id,epoch);
   if(probe_enabled&&|x_re)$display("QWEVENT|%0t|%m|%0d|%0d|ME_X_READ|%h|%h",$time,edge_id,epoch,x_addr,x_re);
   // mq_x<=x_q is an unconditional actual input capture; m_v is logged
   // separately as its existing valid tag, not a reconstructed transaction.
   if(probe_enabled&&m_v)$display("QWEVENT|%0t|%m|%0d|%0d|ME_MEM_PIPE_CAPTURE_TAG_MV|%h|0",$time,edge_id,epoch,x_q);
   if(probe_enabled&&ov)$display("QWEVENT|%0t|%m|%0d|%0d|ME_RESULT_VALID|0|0",$time,edge_id,epoch);
  end
 end
endmodule
bind ot_qwen_w12_matvec_part qw_me_probe #(.G(G),.AW(AW)) stage1_probe
(.clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.m_v(m_v),.ov(ov),.x_re(x_re),.x_addr(x_addr),.x_q(x_q));
module qw_head_probe #(parameter NH=8)(input ck,rst_i,g_q,rd_now,busy,last,vd,
 input[NH-1:0]rv,lr_v,lq_v,input[NH*28-1:0]rp);
 wire probe_enabled=$test$plusargs("QW_PROBE");
 integer edge_id=0,epoch=0;reg was_reset=1;
 always @(posedge ck)begin
  edge_id=edge_id+1;
  if(!rst_i)was_reset=1;
  else begin
   if(was_reset)begin epoch=epoch+1;was_reset=0;end
   if(probe_enabled&&g_q)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_HEAD_GO_CAPTURE|0|0",$time,edge_id,epoch);
   if(probe_enabled&&rd_now)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_READ_DECODE|%h|%h",$time,edge_id,epoch,rp,rv);
   if(probe_enabled&&|lr_v)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_LEAF_REQUEST_PINS|%h|0",$time,edge_id,epoch,lr_v);
   if(probe_enabled&&|lq_v)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_QD_INPUT_CAPTURE|%h|0",$time,edge_id,epoch,lq_v);
   if(probe_enabled&&busy&&last)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_EPOCH_STATE_CLEAR|0|0",$time,edge_id,epoch);
  end
 end
endmodule
bind ot_qfd_xhead qw_head_probe #(.NH(NH)) stage1_probe
(.ck(ck),.rst_i(rst_i),.g_q(g_q),.rd_now(rd_now),.busy(busy),.last(last),.vd(vd),.rv(rv),.rp(rp),.lr_v(lr_v),.lq_v(lq_v));
module qw_leaf_probe(input clk,rst_n,w_v,w_ep,c_v,c_ep,r_v,r_t,r_ep,q_v,q_bad,
 input[27:0]r_p,input[63:0]q,w_m,input[5:0]w_off);
 wire probe_enabled=$test$plusargs("QW_PROBE");
 integer edge_id=0,epoch=0;reg was_reset=1;
 always @(posedge clk)begin
  edge_id=edge_id+1;
  if(!rst_n)was_reset=1;
  else begin
   if(was_reset)begin epoch=epoch+1;was_reset=0;end
   if(probe_enabled&&c_v)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_LEAF_CLEAR_CAPTURE|%0d|0",$time,edge_id,epoch,c_ep);
   if(probe_enabled&&w_v)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_LEAF_WRITE_CAPTURE|%0d|%h",$time,edge_id,epoch,{w_ep,w_off},w_m);
   if(probe_enabled&&r_v)$display("QWEVENT|%0t|%m|%0d|%0d|XPF_LEAF_READ_CAPTURE|%h|%0d",$time,edge_id,epoch,r_p,{r_ep,r_t});
  end
 end
 // Actual settled Q pins. Their request identity is deliberately unresolved.
 always @(negedge clk)if(probe_enabled&&rst_n&&q_v)
  $display("QWEVENT|%0t|%m|%0d|%0d|XPF_LEAF_Q_PINS|%h|%0d",$time,edge_id,epoch,q,q_bad);
endmodule
bind ot_qfd_xs_leaf qw_leaf_probe stage1_probe
(.clk(clk),.rst_n(rst_n),.w_v(w_v),.w_ep(w_ep),.w_m(w_m),.w_off(w_off),.c_v(c_v),.c_ep(c_ep),
 .r_v(r_v),.r_t(r_t),.r_ep(r_ep),.r_p(r_p),.q_v(q_v),.q(q),.q_bad(q_bad));
