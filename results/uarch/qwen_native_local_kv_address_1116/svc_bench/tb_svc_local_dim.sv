`timescale 1ns/1ps
// Adapter-ON wrapper bench: qfd_native59_svc_obs1 (kit params, NATIVE_LOCAL_KV_ADDR=1, LOCAL32=0) driven through its real
// layer-context / dd / kv-word-slot ports with contiguous local dim 0..127 + actual kind; observes the formatter words it emits.
module tb_svc_local_dim #(parameter integer ADAPTER=1)();
 reg ck=0,rst_n=0; always #1 ck=~ck;
 reg layer_context_v=0;reg[5:0]command_stage=0;reg[17:0]native_position=0;reg[547:0]dd_i=0;reg kv_word_slot=0;reg[1:0]kv_word_index=0;
 wire[523:0]x3;wire[58:0]x3i;wire[1:0]x3g;wire txv;wire[547:0]txp;wire hdv;wire[58:0]hdt;wire[1:0]hdg;wire[519:0]dr;
 wire ecre,esre;wire[23:0]eca;wire[17:0]esa;wire cpl;wire[58:0]cpt;wire[94:0]ret;wire flt;
 qfd_native59_svc_obs1 #(.HEAD_PREP(1),.NU(4),.ROPE(1),.USER_BIND(1),.MCTX(1),.EMB_RELAY(1),.RECV_INPUTS(0),.LOCAL32(0),.NATIVE_LOCAL_KV_ADDR(ADAPTER)) u(
  .ck(ck),.rst_n(rst_n),.host_epoch_valid(1'b0),.host_fused_capability(1'b0),.host_epoch(16'd0),.host_tag(59'd0),.host_generation(2'd1),
  .layer_context_v(layer_context_v),.command_stage(command_stage),.head_prepare_v(1'b0),.head_prepare_user(2'd0),.head_prepare_token(18'd0),.head_prepare_position(18'd0),
  .native_token(18'd0),.native_position(native_position),.native_cmd(380'd0),.dd_i(dd_i),.kv_word_slot(kv_word_slot),.kv_word_index(kv_word_index),.kv_x3_slot(1'b0),
  .x3(x3),.x3_identity(x3i),.x3_generation(x3g),.qb_v(1'b0),.qb_beat(5'd0),.qb_row(512'd0),.qb_full(1'b0),.qb_committed(1'b0),.qb_bad(1'b0),
  .tx_user(2'd0),.rx_user(2'd0),.tx_slot(1'b0),.tx_slot_kind(4'd0),.tx_slot_beat(5'd0),.native_tx_v(txv),.native_tx_payload(txp),
  .head_descriptor_v(hdv),.head_descriptor_tag(hdt),.head_descriptor_generation(hdg),
  .native_rx_v(1'b0),.native_rx_payload(548'd0),.rx_slot(1'b0),.rx_slot_kind(4'd0),.rx_slot_beat(5'd0),
  .dr_o(dr),.emb_code_re(ecre),.emb_code_addr(eca),.emb_scale_re(esre),.emb_scale_addr(esa),.emb_code_q(512'd0),.emb_scale_q(16'd0),
  .visibility_slot(1'b0),.complete_slot(1'b0),.completed(cpl),.completed_tag(cpt),.native_ret(ret),.fault(flt));
 integer fd,od,rc,c;reg[575:0]v;string inp,outp;
 always @(posedge ck) if(u.kvn_v) $fwrite(od,"WORD %0d %03h %0128h\n",c,u.kvn_tag,u.kvn_data);
 always @(posedge ck) if(u.formatter_fault) $fwrite(od,"FAULT %0d %02h\n",c,u.formatter_fault_code);
 always @(posedge ck) if(u.kv_in_bad) $fwrite(od,"KVINBAD %0d\n",c);
 always @(posedge ck) if(flt) $fwrite(od,"SVCFAULT %0d\n",c);
 initial begin
  if(!$value$plusargs("INPUT=%s",inp)||!$value$plusargs("OUTPUT=%s",outp))$fatal(1,"paths");
  fd=$fopen(inp,"r");od=$fopen(outp,"w");if(!fd||!od)$fatal(1,"open");
  repeat(20)@(negedge ck);rst_n=1;repeat(300)@(negedge ck);
  for(c=0;c<110;c=c+1)begin rc=$fscanf(fd,"%h\n",v);if(rc!=1)$fatal(1,"short");
   {kv_word_slot,kv_word_index,dd_i,native_position,command_stage,layer_context_v}=v;@(negedge ck);end
  repeat(10)@(negedge ck);$fclose(fd);$fclose(od);$finish;
 end
endmodule
