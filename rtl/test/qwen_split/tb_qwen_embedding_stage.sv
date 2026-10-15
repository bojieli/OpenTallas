`timescale 1ns/1ps
// Minimum actual embedding region: source PW/DW -> actual TT/SU controllers ->
// exact controller decoder -> real64-lane FP SU -> full NOX SRAM memory.
// Returned HBM beats are an explicit real-payload boundary; clocks share one
// logical test phase. Inactive ME/CROM/KV/attention ports are held inactive,
// and the test asserts that no such command is emitted. No fixture core_done.
module tb_qwen_embedding_stage;
 reg ck=0;always #1 ck=~ck;
 wire [75:0] program_obs;
 wire [68:0] descriptor_obs;
 wire  cfg_image_ready;
 reg  rsi=0;
 reg [186:0] dh=0;
 wire [55:0] dc;
 wire [43:0] kvd;
 wire [546:0] cd_d;
 wire [49:0] coll_cmd;
 reg  coll_cmd_free=0;
 reg [517:0] cc=0;
 reg [94:0] me_ret=0;
 reg  me_mem_ok=0;
 reg  kv_ok=0;
 reg  kv_write_drained=0;
 wire [379:0] me_cmd;
 wire [75:0] me_program_obs;
 wire  me_image_ready;
 wire  me_controller_fault;
 wire [56:0] xs;
 wire [24:0] cbc0;
 wire [24:0] cbc1;
 wire [24:0] cbc2;
 wire [24:0] cbc3;
 wire [24:0] cbc4;
 wire [24:0] cbc5;
 wire [24:0] cbc6;
 wire [24:0] cbc7;
 reg [9:0] cbr0=0;
 reg [9:0] cbr1=0;
 reg [9:0] cbr2=0;
 reg [9:0] cbr3=0;
 reg [9:0] cbr4=0;
 reg [9:0] cbr5=0;
 reg [9:0] cbr6=0;
 reg [9:0] cbr7=0;
 reg  vm_rst_n=0;
 reg [552:0] vm_mx=0;
 reg [550:0] vm_rb0=0;
 reg [550:0] vm_rb1=0;
 reg [550:0] vm_rb2=0;
 wire [15:0] vm_ld;
 wire  vm_mo;
 reg  vm_mee=0;
 wire  vm_svr_rdy;
 reg [519:0] vm_ar=0;
 wire [552:0] vm_xaw;
 reg  vm_q_epoch=0;
 reg  vm_q_start=0;
 wire  vm_q_committed;
 wire [523:0] vm_q;
 wire  vm_q_done;
 wire [38:0] vm_write_commit_v;
 wire [311:0] vm_write_commit_line;
 wire [623:0] vm_write_commit_mask;
 wire  vm_fault;
 reg [15:0] context_epoch=0;
 reg  embed_beat_slot=0;
 reg  embed_beat_v=0;
 reg [255:0] embed_beat_data=0;
 reg [17:0] embed_beat_token=0;
 reg [5:0] embed_beat_word=0;
 reg  embed_beat_half=0;
 reg  embed_beat_scale=0;
 reg [15:0] embed_beat_epoch=0;
 reg  embed_fill_begin=0;
 reg [17:0] embed_fill_token=0;
 reg [15:0] embed_fill_epoch=0;
 reg  embed_expected_word_slot=0;
 reg [17:0] embed_expected_token=0;
 reg [5:0] embed_expected_word=0;
 reg  embed_expected_scale=0;
 reg [15:0] embed_expected_epoch=0;
 wire  su_copy_active;
 wire  su_copy_done;
 wire [2136:0] su_copy_xsw;
 wire [62:0] su_native_issue;
 wire [63:0] su_kv_we;
 wire [1535:0] su_kv_waddr;
 wire [2047:0] su_kv_wdata;
 wire [205:0] su_ca0;
 reg [511:0] su_cq0=0;
 wire [205:0] su_ca1;
 reg [511:0] su_cq1=0;
 wire [205:0] su_ca2;
 reg [511:0] su_cq2=0;
 wire [205:0] su_ca3;
 reg [511:0] su_cq3=0;
 wire [205:0] su_ca4;
 reg [511:0] su_cq4=0;
 wire [205:0] su_ca5;
 reg [511:0] su_cq5=0;
 wire [205:0] su_ca6;
 reg [511:0] su_cq6=0;
 wire [205:0] su_ca7;
 reg [511:0] su_cq7=0;
 wire  embedding_fault;
 qfd_embedding_stage_static dut(
 .ck(ck),
 .ck_sched(ck),
 .program_obs(program_obs),
 .descriptor_obs(descriptor_obs),
 .cfg_image_ready(cfg_image_ready),
 .rsi(rsi),
 .dh(dh),
 .dc(dc),
 .kvd(kvd),
 .cd_d(cd_d),
 .coll_cmd(coll_cmd),
 .coll_cmd_free(coll_cmd_free),
 .cc(cc),
 .me_ret(me_ret),
 .me_mem_ok(me_mem_ok),
 .kv_ok(kv_ok),
 .kv_write_drained(kv_write_drained),
 .ck_me_sched(ck),
 .me_cmd(me_cmd),
 .me_program_obs(me_program_obs),
 .me_image_ready(me_image_ready),
 .me_controller_fault(me_controller_fault),
 .xs(xs),
 .cbc0(cbc0),
 .cbc1(cbc1),
 .cbc2(cbc2),
 .cbc3(cbc3),
 .cbc4(cbc4),
 .cbc5(cbc5),
 .cbc6(cbc6),
 .cbc7(cbc7),
 .cbr0(cbr0),
 .cbr1(cbr1),
 .cbr2(cbr2),
 .cbr3(cbr3),
 .cbr4(cbr4),
 .cbr5(cbr5),
 .cbr6(cbr6),
 .cbr7(cbr7),
 .vm_leaf_ck({448{ck}}),
 .vm_commit_ck({39{ck}}),
 .ck_vm(ck),
 .ck_vm_out_relay(ck),
 .ck_vm_in_relay(ck),
 .vm_rst_n(vm_rst_n),
 .vm_mx(vm_mx),
 .vm_rb0(vm_rb0),
 .vm_rb1(vm_rb1),
 .vm_rb2(vm_rb2),
 .vm_ld(vm_ld),
 .vm_mo(vm_mo),
 .vm_mee(vm_mee),
 .vm_svr_rdy(vm_svr_rdy),
 .vm_ar(vm_ar),
 .vm_xaw(vm_xaw),
 .vm_q_epoch(vm_q_epoch),
 .vm_q_start(vm_q_start),
 .vm_q_committed(vm_q_committed),
 .vm_q(vm_q),
 .vm_q_done(vm_q_done),
 .vm_write_commit_v(vm_write_commit_v),
 .vm_write_commit_line(vm_write_commit_line),
 .vm_write_commit_mask(vm_write_commit_mask),
 .vm_fault(vm_fault),
 .context_epoch(context_epoch),
 .embed_beat_slot(embed_beat_slot),
 .embed_beat_v(embed_beat_v),
 .embed_beat_data(embed_beat_data),
 .embed_beat_token(embed_beat_token),
 .embed_beat_word(embed_beat_word),
 .embed_beat_half(embed_beat_half),
 .embed_beat_scale(embed_beat_scale),
 .embed_beat_epoch(embed_beat_epoch),
 .embed_fill_begin(embed_fill_begin),
 .embed_fill_token(embed_fill_token),
 .embed_fill_epoch(embed_fill_epoch),
 .embed_expected_word_slot(embed_expected_word_slot),
 .embed_expected_token(embed_expected_token),
 .embed_expected_word(embed_expected_word),
 .embed_expected_scale(embed_expected_scale),
 .embed_expected_epoch(embed_expected_epoch),
 .ck_su_head({64{ck}}),
 .ck_su_exp({64{ck}}),
 .ck_su_rcp({64{ck}}),
 .ck_su_rsq({64{ck}}),
 .ck_su_lane({64{ck}}),
 .ck_su_align({16{ck}}),
 .ck_su_red({9{ck}}),
 .su_copy_active(su_copy_active),
 .su_copy_done(su_copy_done),
 .su_copy_xsw(su_copy_xsw),
 .su_native_issue(su_native_issue),
 .su_kv_we(su_kv_we),
 .su_kv_waddr(su_kv_waddr),
 .su_kv_wdata(su_kv_wdata),
 .su_ca0(su_ca0),
 .su_cq0(su_cq0),
 .su_ca1(su_ca1),
 .su_cq1(su_cq1),
 .su_ca2(su_ca2),
 .su_cq2(su_cq2),
 .su_ca3(su_ca3),
 .su_cq3(su_cq3),
 .su_ca4(su_ca4),
 .su_cq4(su_cq4),
 .su_ca5(su_ca5),
 .su_cq5(su_cq5),
 .su_ca6(su_ca6),
 .su_cq6(su_cq6),
 .su_ca7(su_ca7),
 .su_cq7(su_cq7),
 .embedding_fault(embedding_fault)
 );
 reg[63:0]image[0:1023],descriptors[0:7];reg[511:0]codes[0:63];reg[15:0]scale[0:0];reg[31:0]expected[0:4095];
 string vectors,image_dir;integer mut=0,k,w,l,go_count=0,vector_writes=0,stage_age=-1,done_count=0,storage_checks=0,errors=0;
 reg check_storage=0;
 always @(posedge ck)begin
  embed_expected_word_slot<=embed_beat_slot&&(embed_beat_half||embed_beat_scale);
  embed_expected_word<=embed_beat_word;embed_expected_scale<=embed_beat_scale;
  embed_expected_epoch<=16'd43;embed_expected_token<=18'd151935;
  if(dut.u_control_vm.u_seq.u_seq.sg_go)stage_age<=0;else if(stage_age>=0)stage_age<=stage_age+1;
  if(su_native_issue[0])begin
   go_count=go_count+1;
   if(su_native_issue[18:1]!=1||su_native_issue[36:19]!=4096||su_native_issue[38:37]!=1||su_native_issue[62:39]!=4096)$fatal(1,"actual source SU command changed");
  end
  if(|dut.vm_sa[2309:2246])begin
   if(dut.vm_sa[2309:2246]!==64'hffffffffffffffff||dut.vm_sa[2221:2198]!=4096+64*vector_writes||dut.vm_sa[2245:2222]!=4097+64*vector_writes)$fatal(1,"actual SU vector write schedule");
   for(integer lane=0;lane<64;lane=lane+1)if(dut.vm_sa[150+32*lane+:32]!==expected[64*vector_writes+lane])begin
    if(errors<4)$display("actual decode/math mismatch vector%0d lane%0d got%h expected%h",vector_writes,lane,dut.vm_sa[150+32*lane+:32],expected[64*vector_writes+lane]);errors=errors+1;
   end
   vector_writes=vector_writes+1;
  end
  if(|su_kv_we||me_cmd[0]||coll_cmd[49]||cd_d[546])$fatal(1,"source embedding stage emitted unrelated operation");
  if(dc[50])begin
   done_count=done_count+1;
   if(stage_age!=422)$fatal(1,"actual stage deadline moved age%0d",stage_age);
  end
 end
 // Read the functional model's actual SRAM cells after real registered bank
 // writes, not a producer interface or a copied reference memory.
 for(genvar group=0;group<8;group=group+1)begin:g_check_group
  for(genvar bank=0;bank<8;bank=bank+1)begin:g_check_bank
   reg[511:0]actual_word;
   integer line,lane,index;
   always @(posedge check_storage)begin
    for(line=4;line<8;line=line+1)begin
     actual_word={dut.u_control_vm.u_vm.u_vm.g_tile.g_t[group].u_t.g_b[bank].u_bt.u_b.g_mac.u_hi.word_read(line),dut.u_control_vm.u_vm.u_vm.g_tile.g_t[group].u_t.g_b[bank].u_bt.u_b.g_mac.u_lo.word_read(line)};
     for(lane=0;lane<16;lane=lane+1)begin
      index=((line*64+8*group+bank)*16+lane)-4096;
      if(actual_word[32*lane+:32]!==expected[index])begin
       if(errors<4)$display("actual SRAM mismatch scalar%0d got%h expected%h",index,actual_word[32*lane+:32],expected[index]);errors=errors+1;
      end
      storage_checks=storage_checks+1;
     end
    end
   end
  end
 end
 task pw(input integer address,input[63:0]data);
  @(negedge ck);dh[118]=1;dh[117:108]=10'(address);dh[107:44]=data;
  @(negedge ck);dh[118]=0;
 endtask
 initial begin
  if(!$value$plusargs("VECTORS=%s",vectors)||!$value$plusargs("IMAGE=%s",image_dir))$fatal(1,"actual source image and payload vectors required");
  void'($value$plusargs("MUT=%d",mut));
  $readmemh({vectors,"/codes.hex"},codes);$readmemh({vectors,"/expected.hex"},expected);$readmemh({vectors,"/scale.hex"},scale);
  $readmemh({image_dir,"/PW.hex"},image);$readmemh({image_dir,"/DW.hex"},descriptors);
  context_epoch=43;embed_fill_epoch=43;embed_fill_token=151935;embed_beat_token=151935;embed_beat_epoch=43;
  // No ME command exists in this source program; external engine is idle.
  me_ret=95'd3;kv_ok=1;kv_write_drained=1;dh[43]=1;
  repeat(8)@(negedge ck);rsi=1;vm_rst_n=1;repeat(24)@(negedge ck);
  for(k=0;k<1024;k=k+1)pw(k,image[k]);
  for(k=0;k<8;k=k+1)begin
   @(negedge ck);dh[186]=1;dh[185:183]=3'(k);dh[182:119]=descriptors[k];
   @(negedge ck);dh[186]=0;
  end
  repeat(16)@(negedge ck);
  if(!cfg_image_ready||!me_image_ready)$fatal(1,"real program/control stores did not seal");
  embed_fill_begin=1;@(negedge ck);embed_fill_begin=0;repeat(2)@(negedge ck);
  for(w=0;w<64;w=w+1)begin
   embed_beat_slot=1;embed_beat_v=1;embed_beat_half=0;embed_beat_word=6'(w);embed_beat_data=codes[w][255:0];
   @(negedge ck);embed_beat_half=1;embed_beat_data=codes[w][511:256];if(mut==1&&w==63)embed_beat_v=0;
   @(negedge ck);
  end
  embed_beat_slot=1;embed_beat_v=1;embed_beat_half=0;embed_beat_scale=1;embed_beat_word=0;embed_beat_data=0;embed_beat_data[15*16+:16]=scale[0];
  @(negedge ck);embed_beat_slot=0;embed_beat_v=0;repeat(8)@(negedge ck);
  dh[35:18]=151935;dh[17:0]=0;dh[42]=1;@(negedge ck);dh[42]=0;
  repeat(480)@(negedge ck);check_storage=1;@(negedge ck);
  if(go_count!=1||vector_writes!=64||done_count!=1||storage_checks!=4096)$fatal(1,"actual stage coverage go%0d writes%0d done%0d SRAM%0d",go_count,vector_writes,done_count,storage_checks);
  if(embedding_fault||vm_fault||me_controller_fault||dc[55]||dc[52]||dc[51]||errors)$fatal(1,"actual embedding region faults embedding%b VM%b ME%b dc%h errors%0d",embedding_fault,vm_fault,me_controller_fault,dc,errors);
  $display("PASS actual source embedding stage token151935 129beats realTT/SU fixedEND realFP64 VMmacros4096 cells checked no fixturecompletion");$finish;
 end
 initial begin #16000;$fatal(1,"actual embedding stage timeout");end
endmodule
