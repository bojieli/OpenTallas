`timescale 1ps/1ps
module tb_root_contract;
  reg c54=0,c474=0,c476=0,c55=0,stopped=0,rsi=0,leaf_override=0;
  integer phase=0, rel=100000, negative=0;
  initial begin #10000; forever begin #4000; if(!stopped)c54=~c54; end end
  initial begin if($value$plusargs("phase=%d",phase))begin end #(10000+phase/3); forever begin #4000;if(!stopped)c474=~c474;end end
  initial begin #(10000+phase*2/3); forever begin #4000;if(!stopped)c476=~c476;end end
  initial begin #(10000+phase); forever begin #4000;if(!stopped)c55=~c55;end end
  wire root;
  qfd_rstseq rstseq_rom(.ck(c54),.rsi(rsi),.rso_ctlm(root));
  wire t1,t2,t11,t12,t13,t14,t15,t16,t24,t25;
  ot_qwen_rst_rep rstt_rst_seq_ctlm_9(.clk(c54),.d(root),.q0(t1));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_10(.clk(c54),.d(t1),.q0(t2));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_11(.clk(c474),.d(t2),.q0(t11));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_33(.clk(c474),.d(t11),.q0(t12));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_14(.clk(c474),.d(t12),.q0(t13));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_17(.clk(c474),.d(t13),.q0(t14));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_20(.clk(c474),.d(t14),.q0(t15));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_23(.clk(c476),.d(t15),.q0(t16));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_25(.clk(c55),.d(t16),.q0(t24));
  ot_qwen_rst_rep rstt_rst_seq_ctlm_0(.clk(c55),.d(t24),.q0(t25));
  wire leaf=t25&&!leaf_override;
  wire lpr_root,lpr_core,lpr_hr;
  ot_pl_pad #(.W(1),.N(1)) u_lpr_root(.ck(c54),.d(leaf),.q(lpr_root));
  ot_pl_pad #(.W(1),.N(2)) u_lpr_core(.ck(c54),.d(lpr_root),.q(lpr_core));
  ot_pl_pad #(.W(1),.N(2)) u_lpr_hr(.ck(c55),.d(lpr_root),.q(lpr_hr));
  reg [7:0] i=8'h3c;
  wire [31:0] bank; wire [11:0] epo; wire [3:0] vld; wire[7:0] o;
  ot_pl_land_local_w #(.W(8),.D(4)) w(.ck(c55),.rsi(lpr_hr),.i(i),.bank(bank),.epo(epo),.vld(vld));
  ot_pl_land_local_r #(.W(8),.D(4),.K(2)) r(.ck(c54),.rsi(lpr_core),.bank(bank),.epo(epo),.vld(vld),.o(o));
  integer stage=0,first_capture=0,first_output=0;
  always @(negedge root) $display("LEDGER root_assert t=%0t",$time);
  always @(posedge root) $display("LEDGER root_release t=%0t n=%0d",$time,rstseq_rom.n);
  always @(negedge leaf) $display("LEDGER leaf_assert t=%0t",$time);
  always @(posedge leaf) $display("LEDGER leaf_release t=%0t",$time);
  always @(posedge w.rq) $display("LEDGER writer_rq_release t=%0t",$time);
  always @(posedge r.rq) $display("LEDGER reader_rq_release t=%0t",$time);
  always @(posedge c55) if(stage==2 && w.rq && !first_capture) begin first_capture=1;$display("LEDGER first_capture t=%0t value=%h wc=%0d",$time,i,w.wc);end
  always @(negedge c54) if(stage==2 && o==8'ha5 && !first_output)begin first_output=1;$display("LEDGER first_output t=%0t value=%h",$time,o);end
  initial begin
    if($value$plusargs("release=%d",rel))begin end
    if($value$plusargs("negative=%d",negative))begin end
    #(rel);rsi=1;
    #23000000;
    if(vld!==4'b1111 || r.warm!==1 || o!==8'h3c)$fatal(1,"BASELINE_NOT_WARM vld=%b warm=%b o=%h",vld,r.warm,o);
    stopped=1;stage=1;
    #10000;i=8'ha5;if(negative)leaf_override=1;else rsi=0;
    #10000;if(negative)leaf_override=0;else rsi=1;
    #10000;
    if(negative)begin
      if(w.rq===1 && vld===4'b1111 && r.warm===1 && o===8'h3c)begin
        $display("LEAF_PULSE_LOST expected causal failure retained warm=%b vld=%b o=%h",r.warm,vld,o);
        $fatal(1,"LEAF_PULSE_LOST");
      end
      $fatal(1,"NEGATIVE_DID_NOT_REPRODUCE");
    end
    if(root!==0 || rstseq_rom.n!==0)$fatal(1,"ROOT_PULSE_NOT_CAPTURED");
    if(o!==8'h3c)$fatal(1,"UNEXPECTED_ASYNC_OUTPUT_CHANGE");
    $display("LEDGER stopped_state retained_o=%h root=%b leaf=%b warm=%b vld=%b",o,root,leaf,r.warm,vld);
    #170000;stopped=0;
    #400000;
    if(root!==0 || vld!==0 || r.warm!==0 || o!==0)$fatal(1,"RESUMED_RESET_FLUSH_FAIL root=%b vld=%b warm=%b o=%h",root,vld,r.warm,o);
    $display("LEDGER resumed_flush t=%0t root=%b leaf=%b wrq=%b rrq=%b warm=%b vld=%b o=%h",$time,root,leaf,w.rq,r.rq,r.warm,vld,o);
    stage=2;
    #11000000;
    if(!first_capture || !first_output || o!==8'ha5)$fatal(1,"FIRST_USE_FAIL");
    $display("ROOT_CONTRACT PASS phase=%0d release=%0d capture=%0d output=%0d",phase,rel,first_capture,first_output);$finish;
  end
endmodule
