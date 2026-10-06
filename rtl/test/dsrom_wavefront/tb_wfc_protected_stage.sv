`timescale 1ns/1fs
// One changed-hookup configuration. External native command/visibility events
// are a finite protocol fixture, not a numerical engine or parent qualification.
module tb_wfc_protected_stage;
 reg fast_clk=0,slow_clk=0;
 initial begin fast_clk=1;forever #0.416667 fast_clk=~fast_clk;end
 initial begin slow_clk=1;forever #0.555556 slow_clk=~slow_clk;end
 reg cold_n=0,slow_rst_n=0;
 reg fast_rst_n=0,cold_fenced=0,cmd_v=0;reg[1:0]cmd_op=0;
 reg[9:0]cmd_user=0;reg[20:0]cmd_pos=0,cmd_token=0;reg[3:0]cmd_block=0;
 reg[15:0]cmd_epoch=9;reg[13:0]cmd_entry=12;
 wire cmd_ready,producer_active,producer_initializing,cfg_fault;
 reg in_valid=0,in_last=0,out_ready=0;reg[511:0]in_data=0;
 wire in_ready,out_valid,out_last;wire[511:0]out_data;
 reg rcfg_we=0;reg[7:0]rcfg_dest=0;reg[2:0]rcfg_mask=0;
 reg[3:0]command_v=0,retire_v=0,fence_v=0;wire[3:0]command_ready;
 reg[187:0]command_identity=0,retire_identity=0,fence_identity=0;
 reg[83:0]command_token=0;reg[27:0]command_home=0,retire_home=0;
 reg[55:0]command_entry=0,command_pc=0,retire_entry=0;reg[15:0]command_unit=0;
 reg[23:0]retire_visibility=0;reg[19:0]fence_visibility=0;
 reg[3:0]retire_quiet=0,retire_capture_drained=0,retire_fault=0;
 reg result_v=0;reg[46:0]result_identity=0;reg[20:0]result_token=17;reg[31:0]result_value=32'h3f800000;
 wire token_result_valid,stage_handoff,producer_pending,whole_fault;
 reg context_restored=0,native_idle=1,native_fragment_done=0,c8_write_quiet=0;
 reg[3:0]xb_we4=0;reg[59:0]xb_waddr4=0;reg[2047:0]xb_wdata4=0;
 reg xb_re=0;reg[14:0]xb_raddr=0;wire[511:0]xb_rq;
 reg xb_v=0,xb_consume_v=0;reg[46:0]xb_owner={16'd9,10'd865,21'd0},xb_consume_owner=0;
 wire xb_ready,xb_reply_v,xb_port_retired;wire[46:0]xb_reply_owner;wire[3:0]xb_row_visible;
 wire vm_pending,vm_initializing,vm_fault,vm_quarantined,vm_port_retired;wire[3:0]vm_phase;
 wire context_v;wire[46:0]context_identity;wire[20:0]context_token;wire[13:0]context_entry;
 wire native_start;wire[20:0]native_token,native_pos;wire[13:0]native_entry;wire[9:0]native_user;
 wire[46:0]native_identity;wire[20:0]captured_token,captured_pos;wire[13:0]captured_pc;
 wire c8_retire_v;wire[46:0]c8_retire_identity;
 wire tok_valid;wire[9:0]tok_user,users_done;wire[20:0]tok_pos,tok_id;
 wire busy,wfc_fault,bl_rx_ready,bl_tx_valid,bl_tx_last;wire[511:0]bl_tx_data;
 ot_dsrom_wfc_protected_stage #(.ENABLE(1),.STRUCTURAL(1))dut(
 .bl_rx_valid(1'b0),.bl_rx_last(1'b0),.bl_rx_data(512'd0),.bl_tx_ready(1'b1),
 .c8_write_quarantine(1'b0),.c8_write_fault(1'b0),.coll_busy(1'b0),.*);
 reg[71:0]books[0:3][0:166];reg[71:0]load0[0:166],load1[0:166],load2[0:166],load3[0:166];
 integer cycles=0,requests=0,starts=0,acks=0,c8_retires=0,flits=0,writes=0,commands=0,retirements=0;
 integer exposed_edge=-1,capture_edges=-1;
 reg[46:0]owner=0;reg holding=0;reg[100:0]held_result;
 integer accepts=0,replies=0,consumes=0,port_retires=0,readcaptures=0,slow_edges=0,accepted_edge=-1,reply_edge=-1,consume_edge=-1;
 integer split_pairs=0,paired_writes=0,paired_read_edge=-1;
 reg[46:0]paired_rx_owner;
 reg negative_phase=0,output_held=0;reg[512:0]held_flit;
 always @(posedge slow_clk)slow_edges=slow_edges+1;
 always @(posedge fast_clk)begin
  cycles=cycles+1;
  if(cold_n&&fast_rst_n&&!negative_phase&&(cfg_fault||whole_fault||wfc_fault||vm_fault||dut.adapter_fault))$fatal(1,"first nominal fault cycle%0d cfg%0b whole%0b wfc%0b",cycles,cfg_fault,whole_fault,wfc_fault);
  if(output_held&&(!out_valid||{out_last,out_data}!==held_flit))$fatal(1,"held output valid/data/last lifetime violated");
  output_held=out_valid&&!out_ready;if(output_held)held_flit={out_last,out_data};
  if(dut.provider_request_v&&dut.provider_request_ready)begin
   accepts=accepts+1;accepted_edge=cycles;
   if(dut.u_adapter.g_live.split)begin
    split_pairs=split_pairs+1;paired_read_edge=cycles;paired_rx_owner=dut.xa_owner;
    if(dut.provider_request_owner!=={16'd9,10'd865,21'd0}||paired_rx_owner!=={16'd9,10'd865,21'd1}||dut.provider_read_enable!=1||dut.provider_write_enable!=0||xb_ready)$fatal(1,"legal overlapping owners not admitted as olddata-read first");
   end
   if(dut.u_adapter.g_live.second_write)begin
    paired_writes=paired_writes+1;
    if(dut.provider_request_owner!==paired_rx_owner||dut.provider_read_enable!=0||dut.provider_write_enable!=1||xb_ready||readcaptures==0)$fatal(1,"paired write lost lease/priority/read consumption");
    $display("NATIVE_TWO_LEASE pair%0d TXowner0004ec200000 RXowner%h fast_read_accept_to_write_accept%0d",paired_writes,dut.provider_request_owner,cycles-paired_read_edge);
   end
  end
  if(dut.u_adapter.g_live.flags[8]&&xb_ready)$fatal(1,"XB accepted during held two-owner pair");
  if(dut.u_adapter.g_live.state==1&&dut.provider_reply_v)begin replies=replies+1;reply_edge=cycles;
   $display("PROTECTED_SERVICE reply bundle%0d owner%h fast_accept_to_reply%0d slow_edges%0d",accepts,dut.provider_reply_owner,cycles-accepted_edge,slow_edges);
  end
  if(dut.xa_read_capture)begin
   readcaptures=readcaptures+1;
   if(!dut.provider_reply_v||dut.provider_reply_owner!==dut.u_adapter.g_live.owner)$fatal(1,"WFC captured unprotected/unowned read");
  end
  if(dut.provider_consume_v)begin
   consumes=consumes+1;consume_edge=cycles;
   if(!dut.provider_allcopies_fenced||dut.provider_consume_owner!==dut.u_adapter.g_live.owner)$fatal(1,"provider consumed without actual caller copies");
  end
  if(vm_port_retired)begin port_retires=port_retires+1;$display("PROTECTED_SERVICE retired bundle%0d fast_consume_to_retire%0d",port_retires,cycles-consume_edge);end
  // Deterministic genuine consumer backpressure; no seed repetitions.
  out_ready<=cycles%7!=0;
  if(dut.u_stage.g_stage.core_start&&dut.advance)exposed_edge=cycles;
  if(dut.stage_request_v&&dut.stage_request_ready)begin
   requests=requests+1;owner=dut.stage_request_identity;
   if(owner!=={16'd9,10'd865,21'(requests-1)}||dut.stage_request_entry!=12||dut.stage_request_token!=(requests==1?3:5))$fatal(1,"joint admission lost actual tuple");
  end
  if(native_start)begin
   starts=starts+1;capture_edges=cycles-exposed_edge;
   if(native_identity!==owner||native_user!=865||native_pos!=starts-1||native_token!=(starts==1?3:5)||native_entry!=12||capture_edges<3)$fatal(1,"canonical native capture wrong");
  end
  if(c8_retire_v)begin c8_retires=c8_retires+1;if(c8_retire_identity!==owner)$fatal(1,"C8 retirement owner mismatch");end
  if(dut.whole_stage_v&&!dut.whole_stage_accepted)begin
   if(holding&&held_result!=={dut.whole_stage_identity,dut.whole_stage_token,dut.whole_stage_value,1'b1})$fatal(1,"held canonical result changed");
   holding=1;held_result={dut.whole_stage_identity,dut.whole_stage_token,dut.whole_stage_value,1'b1};
  end
  if(dut.whole_stage_accepted)begin
   acks=acks+1;holding=0;
   if(!stage_handoff||token_result_valid||dut.whole_stage_identity!==owner||dut.whole_stage_token!=17||dut.whole_stage_value!=32'h3f800000)$fatal(1,"actual ACK not complete L19 handoff");
  end
  if(fast_rst_n&&dut.xa_we&&dut.advance)begin
   if(dut.xa_waddr!=writes%41||dut.xa_wdata!=={16{32'(writes%41+1)}})$fatal(1,"independent VM gold mismatch");
   writes=writes+1;
  end
  if(out_valid&&out_ready)begin
   if(flits==0)begin
    if(out_data[19:16]!=1||out_data[31:24]!=46||out_data[39:32]!=97||out_data[151+:2]!=3||out_data[61+:21]!=17||out_data[82+:32]!=32'h3f800000||out_last)$fatal(1,"independent canonical header gold mismatch");
   end else if(out_data!=={16{32'(flits<=41?flits:1000+flits-1)}}||out_last!=(flits==46))$fatal(1,"independent payload gold mismatch %0d",flits);
   flits=flits+1;
  end
 end
 task automatic beat(input[511:0]data,input last);
  begin @(negedge fast_clk);in_valid=1;in_data=data;in_last=last;
   @(posedge fast_clk);while(!in_ready)@(posedge fast_clk);
   @(negedge fast_clk);in_valid=0;
  end
 endtask
 task automatic send_job(input integer pos,input integer token);
  reg[511:0]header;
  begin header=0;header[19:16]=1;header[31:24]=41;header[39:32]=97;header[151+:2]=3;header[40+:21]=pos;header[114+:21]=token;
   beat(header,0);for(integer w=1;w<=41;w=w+1)beat({16{32'(w)}},w==41);
  end
 endtask
 task automatic program_word(input integer op,u,pos,tok);
  begin @(negedge fast_clk);if(!cmd_ready)$fatal(1,"canonical config not ready");
   cmd_op=2'(op);cmd_user=10'(u);cmd_pos=21'(pos);cmd_token=21'(tok);cmd_v=1;
   @(posedge fast_clk);@(negedge fast_clk);cmd_v=0;
  end
 endtask
 task automatic xb_service(input integer row,input[3:0]we,input rd,input[2047:0]data,input[511:0]expected);
  begin
   @(negedge fast_clk);xb_v=1;xb_we4=we;xb_re=rd;xb_raddr=15'(row);
   xb_waddr4={4{15'(row)}};xb_wdata4=data;
   @(posedge fast_clk);while(!xb_ready)@(posedge fast_clk);
   @(negedge fast_clk);xb_v=0;xb_we4=0;xb_re=0;
   wait(xb_reply_v);@(negedge fast_clk);
   if(xb_reply_owner!==xb_owner||xb_row_visible!==we||(rd&&xb_rq!==expected))$fatal(1,"actual owned XB protected reply/olddata mismatch row%0d",row);
   repeat(3)begin @(negedge fast_clk);if(!xb_reply_v||!vm_pending||xb_reply_owner!==xb_owner||(rd&&xb_rq!==expected)||xb_port_retired)$fatal(1,"read/visible reply retired before consume");end
   xb_consume_owner=xb_owner;xb_consume_v=1;@(posedge fast_clk);@(negedge fast_clk);xb_consume_v=0;
   wait(xb_port_retired);@(posedge fast_clk);@(negedge fast_clk);
  end
 endtask
 initial begin
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank0.hex",load0);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank1.hex",load1);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank2.hex",load2);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank3.hex",load3);
  for(integer n=0;n<167;n=n+1)begin books[0][n]=load0[n];books[1][n]=load1[n];books[2][n]=load2[n];books[3][n]=load3[n];end
  // Actual POR on both related roots; no forced initial state or fault waiver.
  repeat(4)@(negedge slow_clk);cold_n=1;slow_rst_n=1;fast_rst_n=1;
  wait(!vm_initializing);@(negedge fast_clk);
  for(integer w=0;w<46;w=w+1)xb_service(w,1,0,{1536'd0,{16{32'(1000+w)}}},0);
  xb_service(32767,1,0,{1536'd0,{16{32'habcddcba}}},0);
  xb_service(32767,0,1,0,{16{32'habcddcba}});
  wait(!producer_initializing);@(negedge fast_clk);
  // The canonical producer requires real full866 prefix admission. This setup
  // is part of the new joint gate, not a repeat of its standalone proof.
  for(integer u=0;u<866;u=u+1)for(integer pos=0;pos<3;pos=pos+1)program_word(0,u,pos,100+u*3+pos);
  program_word(2,866,3,30);wait(producer_active||cfg_fault);@(negedge fast_clk);
  if(cfg_fault||dut.cfg_users!=866||dut.stage_epoch!=9||dut.stage_entry!=12)$fatal(1,"actual canonical run admission failed");
  rcfg_we=1;rcfg_dest=0;rcfg_mask=1;
  @(negedge fast_clk);rcfg_dest=1;rcfg_mask=2;
  @(negedge fast_clk);rcfg_we=0;c8_write_quiet=1;
  send_job(0,3);wait(requests==1);repeat(6)@(negedge fast_clk);
  if(starts||acks||!producer_pending||!context_v)$fatal(1,"canonical/C8 restoration fence bypass");
  context_restored=1;wait(starts==1);@(negedge fast_clk);
  if(captured_token!=3||captured_pos!=0||captured_pc!=12)$fatal(1,"native tuple capture mismatch");
  native_idle=0;repeat(4)@(negedge fast_clk);native_fragment_done=1;native_idle=1;
  wait(c8_retires==1);repeat(3)@(negedge fast_clk);
  if(acks||flits||!producer_pending||!busy)$fatal(1,"C8 fragment substituted for whole L19");
  for(integer n=0;n<167;n=n+1)begin
   @(negedge fast_clk);if(command_ready!=15)$fatal(1,"book command not ready %0d",n);
   for(integer rank=0;rank<4;rank=rank+1)begin
    command_identity[47*rank+:47]=owner;command_token[21*rank+:21]=3;
    command_home[7*rank+:7]=books[rank][n][6:0];command_entry[14*rank+:14]=books[rank][n][20:7];command_pc[14*rank+:14]=books[rank][n][34:21];command_unit[4*rank+:4]=books[rank][n][38:35];
   end
   command_v=15;@(posedge fast_clk);@(negedge fast_clk);command_v=0;commands=commands+4;
   if(books[0][n][39])begin
    if(acks||dut.whole_stage_v)$fatal(1,"fragment prematurely completed canonical WFC job");
    for(integer rank=0;rank<4;rank=rank+1)begin retire_identity[47*rank+:47]=owner;retire_home[7*rank+:7]=books[rank][n][6:0];retire_entry[14*rank+:14]=books[rank][n][20:7];end
    retire_visibility={24{1'b1}};retire_quiet=15;retire_capture_drained=15;retire_v=15;
    @(posedge fast_clk);@(negedge fast_clk);retire_v=0;retirements=retirements+4;
   end
   if(n%7==0)@(negedge fast_clk);
   if(whole_fault)$fatal(1,"literal source receipt refused %0d",n);
  end
  if(acks||dut.whole_stage_v)$fatal(1,"result/final-fence authority bypassed");
  c8_write_quiet=0;fence_v=15;fence_identity={4{owner}};fence_visibility={20{1'b1}};
  @(posedge fast_clk);@(negedge fast_clk);fence_v=0;result_v=1;result_identity=owner;
  @(posedge fast_clk);@(negedge fast_clk);result_v=0;
  repeat(7)begin @(negedge fast_clk);if(acks||!dut.whole_stage_v||!producer_pending||!stage_handoff||token_result_valid)$fatal(1,"whole producer hold/health contract bypassed");end
  c8_write_quiet=1;
  wait(dut.xa_re&&dut.provider_request_v&&dut.provider_request_ready);@(negedge fast_clk);
  if(!dut.xa_re||dut.xa_raddr!=0)$fatal(1,"expected first actual XA read frontier");
  // This is one accepted native edge: XA read, XB read, four same-owner
  // overlapping writers. Both reads MUST return the old value1; XB3 wins write.
  xb_v=1;xb_re=1;xb_raddr=0;xb_we4=15;xb_waddr4=0;
  xb_wdata4={{16{32'd4444}},{16{32'd3333}},{16{32'd2222}},{16{32'd1111}}};
  @(posedge fast_clk);if(!xb_ready)$fatal(1,"same-owner accepted bundle lacked real backpressure handshake");
  @(negedge fast_clk);xb_v=0;xb_we4=0;xb_re=0;
  wait(xb_reply_v);@(negedge fast_clk);
  if(xb_row_visible!=15||xb_reply_owner!==owner||xb_rq!=={16{32'd1}})$fatal(1,"olddata/allwriter priority reply failed");
  repeat(5)begin @(negedge fast_clk);if(!vm_pending||!xb_reply_v||xb_rq!=={16{32'd1}}||xb_port_retired)$fatal(1,"whole ACK/readcopy debt conflated");end
  if(acks!=1||port_retires==accepts)$fatal(1,"whole ACK did not stay distinct from held provider debt");
  xb_consume_owner=owner;xb_consume_v=1;@(posedge fast_clk);@(negedge fast_clk);xb_consume_v=0;
  wait(xb_port_retired);@(posedge fast_clk);@(negedge fast_clk);
  // Literal native rx_word_free permits next position to overwrite only rows
  // already read by previous TX. Keep both distinct owners, do not reject it.
  native_fragment_done=0;
  fork
   send_job(1,5);
   begin wait(split_pairs>0);xb_owner={16'd9,10'd865,21'd1};xb_service(32767,0,1,0,{16{32'habcddcba}});end
  join
  wait(flits==47);wait(!vm_pending);wait(requests==2);wait(starts==2);repeat(5)@(negedge fast_clk);
  xb_service(0,0,1,0,{16{32'd1}});

  if(cfg_fault||whole_fault||wfc_fault||!busy||!producer_pending||writes!=82||commands!=668||retirements!=192||readcaptures!=46||accepts!=port_retires||accepts!=consumes||accepts!=replies||split_pairs==0||split_pairs!=paired_writes)$fatal(1,"joint nominal mechanism failed cfg%0b whole%0b wfc%0b busy%0b pending%0b writes%0d commands%0d retirements%0d captures%0d accepts%0d retires%0d consumes%0d replies%0d",cfg_fault,whole_fault,wfc_fault,busy,producer_pending,writes,commands,retirements,readcaptures,accepts,port_retires,consumes,replies);
  $display("PROTECTED_JOIN_NOMINAL PASS MAXU866 fullVM32768x512 commands668 retirements192 independentWrites82 independentFlits47 actualACK1 legalSplitPairs%0d cycles%0d nativeCaptureEdges%0d protectedBundles%0d readCaptures%0d",split_pairs,cycles,capture_edges,accepts,readcaptures);
  // New caller negative under a second real WFC owner: wrong external read
  // consumption cannot authorize a reverse receipt or erase accepted debt.
  @(negedge fast_clk);
  xb_owner=owner;xb_v=1;xb_re=1;xb_raddr=32767;
  @(posedge fast_clk);while(!xb_ready)@(posedge fast_clk);
  @(negedge fast_clk);xb_v=0;xb_re=0;
  wait(xb_reply_v);@(negedge fast_clk);
  if(xb_rq!=={16{32'habcddcba}}||xb_reply_owner!==owner||!vm_pending)$fatal(1,"second owner read missing real data/debt");
  negative_phase=1;xb_consume_owner=owner^47'd1;xb_consume_v=1;
  @(posedge fast_clk);@(negedge fast_clk);xb_consume_v=0;repeat(3)@(negedge fast_clk);
  if(!dut.adapter_fault||!vm_pending||!producer_pending||!busy||acks!=1||dut.provider_consume_v)$fatal(1,"wrong-owner consumption authorized retirement");
  fast_rst_n=0;repeat(3)@(negedge fast_clk);fast_rst_n=1;repeat(6)@(negedge fast_clk);
  if(!vm_fault||!vm_quarantined||!vm_pending||!whole_fault||!wfc_fault||!cfg_fault||!producer_pending||!busy||acks!=1||dut.u_memory.g_live.source_packet.owner!==owner)$fatal(1,"warm reset erased actual owned provider/WFC debt");
  $display("PROTECTED_JOIN_NEGATIVE PASS wrongReadConsumeRefused1 warmProviderDebtRetained1 wholeACKUnchanged1 actualOwner%h",owner);
  $display("PROTECTED_JOIN_MECHANISM PASS no_whole_numerical_engine_or_SSFF_qualification");$finish;
 end
endmodule
