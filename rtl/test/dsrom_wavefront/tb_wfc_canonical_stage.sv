`timescale 1ns/1ps
// One changed-hookup configuration. External native command/visibility events
// are a finite protocol fixture, not a numerical engine or parent qualification.
module tb_wfc_canonical_stage;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,cold_fenced=0,cmd_v=0;reg[1:0]cmd_op=0;
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
 wire context_v;wire[46:0]context_identity;wire[20:0]context_token;wire[13:0]context_entry;
 wire native_start;wire[20:0]native_token,native_pos;wire[13:0]native_entry;wire[9:0]native_user;
 wire[46:0]native_identity;wire[20:0]captured_token,captured_pos;wire[13:0]captured_pc;
 wire c8_retire_v;wire[46:0]c8_retire_identity;
 wire tok_valid;wire[9:0]tok_user,users_done;wire[20:0]tok_pos,tok_id;
 wire busy,wfc_fault,bl_rx_ready,bl_tx_valid,bl_tx_last;wire[511:0]bl_tx_data;
 ot_dsrom_wfc_canonical_stage #(.ENABLE(1),.STRUCTURAL(1))dut(
 .bl_rx_valid(1'b0),.bl_rx_last(1'b0),.bl_rx_data(512'd0),.bl_tx_ready(1'b1),
 .c8_write_quarantine(1'b0),.c8_write_fault(1'b0),.coll_busy(1'b0),.*);
 reg[71:0]books[0:3][0:166];reg[71:0]load0[0:166],load1[0:166],load2[0:166],load3[0:166];
 integer cycles=0,requests=0,starts=0,acks=0,c8_retires=0,flits=0,writes=0,commands=0,retirements=0;
 integer exposed_edge=-1,capture_edges=-1;
 reg[46:0]owner=0;reg holding=0;reg[100:0]held_result;
 always @(posedge clk)begin
  cycles=cycles+1;
  // Deterministic genuine consumer backpressure; no seed repetitions.
  out_ready<=cycles%7!=0;
  if(dut.u_stage.g_stage.core_start)exposed_edge=cycles;
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
  if(rst_n&&dut.u_stage.g_stage.vm_we)begin
   if(dut.u_stage.g_stage.vm_waddr!=writes%41||dut.u_stage.g_stage.vm_wdata!=={16{32'(writes%41+1)}})$fatal(1,"independent VM gold mismatch");
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
  begin @(negedge clk);in_valid=1;in_data=data;in_last=last;
   @(posedge clk);while(!in_ready)@(posedge clk);
   @(negedge clk);in_valid=0;
  end
 endtask
 task automatic send_job(input integer pos,input integer token);
  reg[511:0]header;
  begin header=0;header[19:16]=1;header[31:24]=41;header[39:32]=97;header[151+:2]=3;header[40+:21]=pos;header[114+:21]=token;
   beat(header,0);for(integer w=1;w<=41;w=w+1)beat({16{32'(w)}},w==41);
  end
 endtask
 task automatic program_word(input integer op,u,pos,tok);
  begin @(negedge clk);if(!cmd_ready)$fatal(1,"canonical config not ready");
   cmd_op=2'(op);cmd_user=10'(u);cmd_pos=21'(pos);cmd_token=21'(tok);cmd_v=1;
   @(posedge clk);@(negedge clk);cmd_v=0;
  end
 endtask
 initial begin
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank0.hex",load0);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank1.hex",load1);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank2.hex",load2);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank3.hex",load3);
  for(integer n=0;n<167;n=n+1)begin books[0][n]=load0[n];books[1][n]=load1[n];books[2][n]=load2[n];books[3][n]=load3[n];end
  // Only the source words needed by this changed mechanism and full-depth highword.
  for(integer w=0;w<46;w=w+1)begin @(negedge clk);xb_we4=1;xb_waddr4[14:0]=w;xb_wdata4[511:0]={16{32'(1000+w)}};end
  @(negedge clk);xb_waddr4[14:0]=32767;xb_wdata4[511:0]={16{32'habcddcba}};
  @(negedge clk);xb_we4=0;rst_n=1;
  wait(!producer_initializing);@(negedge clk);
  // The canonical producer requires real full866 prefix admission. This setup
  // is part of the new joint gate, not a repeat of its standalone proof.
  for(integer u=0;u<866;u=u+1)for(integer pos=0;pos<3;pos=pos+1)program_word(0,u,pos,100+u*3+pos);
  program_word(2,866,3,30);wait(producer_active||cfg_fault);@(negedge clk);
  if(cfg_fault||dut.cfg_users!=866||dut.stage_epoch!=9||dut.stage_entry!=12)$fatal(1,"actual canonical run admission failed");
  rcfg_we=1;rcfg_dest=0;rcfg_mask=1;
  @(negedge clk);rcfg_dest=1;rcfg_mask=2;
  @(negedge clk);rcfg_we=0;c8_write_quiet=1;
  send_job(0,3);wait(requests==1);repeat(6)@(negedge clk);
  if(starts||acks||!producer_pending||!context_v)$fatal(1,"canonical/C8 restoration fence bypass");
  context_restored=1;wait(starts==1);@(negedge clk);
  if(captured_token!=3||captured_pos!=0||captured_pc!=12)$fatal(1,"native tuple capture mismatch");
  native_idle=0;repeat(4)@(negedge clk);native_fragment_done=1;native_idle=1;
  wait(c8_retires==1);repeat(3)@(negedge clk);
  if(acks||flits||!producer_pending||!busy)$fatal(1,"C8 fragment substituted for whole L19");
  for(integer n=0;n<167;n=n+1)begin
   @(negedge clk);if(command_ready!=15)$fatal(1,"book command not ready %0d",n);
   for(integer rank=0;rank<4;rank=rank+1)begin
    command_identity[47*rank+:47]=owner;command_token[21*rank+:21]=3;
    command_home[7*rank+:7]=books[rank][n][6:0];command_entry[14*rank+:14]=books[rank][n][20:7];command_pc[14*rank+:14]=books[rank][n][34:21];command_unit[4*rank+:4]=books[rank][n][38:35];
   end
   command_v=15;@(posedge clk);@(negedge clk);command_v=0;commands=commands+4;
   if(books[0][n][39])begin
    if(acks||dut.whole_stage_v)$fatal(1,"fragment prematurely completed canonical WFC job");
    for(integer rank=0;rank<4;rank=rank+1)begin retire_identity[47*rank+:47]=owner;retire_home[7*rank+:7]=books[rank][n][6:0];retire_entry[14*rank+:14]=books[rank][n][20:7];end
    retire_visibility={24{1'b1}};retire_quiet=15;retire_capture_drained=15;retire_v=15;
    @(posedge clk);@(negedge clk);retire_v=0;retirements=retirements+4;
   end
   if(n%7==0)@(negedge clk);
   if(whole_fault)$fatal(1,"literal source receipt refused %0d",n);
  end
  if(acks||dut.whole_stage_v)$fatal(1,"result/final-fence authority bypassed");
  c8_write_quiet=0;fence_v=15;fence_identity={4{owner}};fence_visibility={20{1'b1}};
  @(posedge clk);@(negedge clk);fence_v=0;result_v=1;result_identity=owner;
  @(posedge clk);@(negedge clk);result_v=0;
  repeat(7)begin @(negedge clk);if(acks||!dut.whole_stage_v||!producer_pending||!stage_handoff||token_result_valid)$fatal(1,"whole producer hold/health contract bypassed");end
  c8_write_quiet=1;wait(acks==1);wait(flits==47);repeat(5)@(negedge clk);
  if(cfg_fault||whole_fault||wfc_fault||busy||producer_pending||writes!=41||commands!=668||retirements!=192)$fatal(1,"joint nominal mechanism failed");
  $display("CANONICAL_ACTIVE_NOMINAL PASS MAXU866 fullVM32768x512 commands668 retirements192 independentWrites41 independentFlits47 actualACK1 cycles%0d nativeCaptureEdges%0d",cycles,capture_edges);
  // Meaningful new joint negative: an early owner-matched final fence cannot
  // release the second admitted WFC owner. No second full-book replay.
  native_fragment_done=0;send_job(1,5);wait(requests==2);wait(starts==2);@(negedge clk);
  fence_v=15;fence_identity={4{owner}};fence_visibility={20{1'b1}};
  @(posedge clk);@(negedge clk);fence_v=0;repeat(3)@(negedge clk);
  if(!whole_fault||!producer_pending||!busy||acks!=1||dut.whole_stage_v||dut.whole_stage_accepted)$fatal(1,"early final fence erased joint owner or authorized ACK");
  rst_n=0;repeat(3)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
  xb_re=1;xb_raddr=32767;@(negedge clk);
  if(!whole_fault||!wfc_fault||!cfg_fault||!producer_pending||!busy||acks!=1||xb_rq!=={16{32'habcddcba}})$fatal(1,"warm reset erased retained canonical owner/VM");
  $display("CANONICAL_ACTIVE_NEGATIVE PASS earlyFenceFalseACK0 acceptedDebtRetained1 warmQuarantine1 fullVMHighwordPreserved1");
  $display("CANONICAL_ACTIVE_MECHANISM PASS no_whole_numeric_engine_or_physical_qualification");$finish;
 end
endmodule
