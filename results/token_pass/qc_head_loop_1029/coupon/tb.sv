`timescale 1ns/1ps
module tb;
 parameter integer MODE=0,FWD=8,TXD=18;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,raw_slot=0,headpin=0,callback=0,load=0;
 reg[FWD-1:0]forwarded=0;
 always @(posedge ck)begin headpin<=raw_slot;forwarded<={forwarded,headpin};callback<=forwarded[FWD-1];end
 wire hv,hf;wire[547:0]hr;wire[22:0]hp;
 qfd_mu_head_context_tx_lctx32 h(.ck(ck),.rst_leaf({40{rst}}),.source_copies({6{callback}}),.tx_v_pub(hp),
 .descriptor_v(load),.descriptor_tag({16'd16,6'd0,18'd123,13'd79,6'd0}),.descriptor_generation(2'd2),
 .send_slot(MODE==0&&callback),.send_user(2'd0),.program_ready(1'b1),.installed_fusedcap(1'b1),
 .program_epoch(16'h42a1),.program_digest(64'hbd510612),.tx_v(hv),.tx_record(hr),.fault(hf));
 wire wv,wo,wf;wire[547:0]wr;wire[35:0]sc;
 assign sc={24'd0,{10{MODE==1&&callback}},2'd0};
 qfd_sys_face_record_port_n32 w(.ck(ck),.rst_leaf({54{rst}}),.source_copies(sc),
 .auth_slot(1'b0),.context_slot(1'b0),.witness_slot(MODE==1&&callback),.rx_v(1'b0),.rx_record(548'd0),
 .execution_active(1'b0),.program_obs2(152'd0),.descriptor_obs(69'd0),.cfg_image_ready(2'd0),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),
 .begin_v(),.auth_v(),.begin_epoch(),.auth_epoch(),.expected_pw(),.expected_dw(),.auth_digest(),
 .program_ready(),.installed_fusedcap(),.commit_v(),.program_epoch(),.program_digest(),
 .host_epoch_valid(),.host_epoch(),.host_tag(),.host_gen(),.tx_v(wv),.tx_observed_v(wo),.tx_record(wr),.fault(wf));
 reg[548:0]outwrap=0,ret[0:4],incapture=0;
 always @(posedge ck)begin
  outwrap<=MODE==0?{hv,hr}:{wo,wr};ret[0]<=outwrap;
  for(integer k=1;k<5;k=k+1)ret[k]<=ret[k-1];
  incapture<=ret[4];
 end
 // Exact g_dly fire delay of ot_qwen_d2d_static_end_s7, including its final FF.
 reg[TXD-2:0]sr=0;reg fire=0;
 always @(posedge ck)if(!rst)begin sr<=0;fire<=0;end else begin sr<={sr,raw_slot};fire<=sr[TXD-2];end
 integer c,seen=0;
 initial begin
  repeat(20)@(negedge ck);rst=1;load=1;@(negedge ck);load=0;repeat(4)@(negedge ck);
  for(c=0;c<40;c=c+1)begin
   raw_slot=c==0;@(posedge ck);#0.001;
   if(incapture[548])begin seen=seen+1;$display("ACTUAL_RECORD mode%0d post_edge%0d",MODE,c);end
   if(fire!==incapture[548])$fatal(1,"LOOP_FAIL mode%0d FWD%0d TXD%0d edge%0d fire%0b observed%0b",MODE,FWD,TXD,c,fire,incapture[548]);
   if(MODE==0&&hf)$fatal(1,"head source fault");
   if(MODE==1&&wf)$fatal(1,"witness source fault");
   @(negedge ck);
  end
  if(seen!=1)$fatal(1,"missing actual record");
  $display("LOOP_PASS mode%0d FWD%0d TXD%0d",MODE,FWD,TXD);$finish;
 end
endmodule
