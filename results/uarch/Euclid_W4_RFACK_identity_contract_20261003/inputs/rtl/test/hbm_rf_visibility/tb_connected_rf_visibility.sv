`timescale 1ns/1ps
// Executable finite source-join audit, not an adopted SM or qualified macro.
// RF-side extension: native matrix body retained; unchanged Maxwell r3 bounded capture instantiated.
// Actual matrix and full128 service, two dependent in-place SIMD ops without host overwrite.
module tb_connected_rf_visibility;
 parameter integer QWEN=0;
 localparam NC=QWEN?16:8, MAXVECS=4096*NC/128;
 localparam XC=8*266+64*16, FW=QWEN?32768:NC*XC, BEATS=(FW+2047)/2048;
 reg clk=0,rst_n=0; always #5 clk=~clk; // functional10ns only
 reg start=0;reg[12:0]op_rows=16;reg[15:0]op_c=1;reg[7:0]op_g=1;
 wire busy,rv,fault,arrive,released;wire[11:0]rrow;wire[NC*32-1:0]rdata;
 reg release_in=0,d_valid=0;wire d_ready,req_v;wire[31:0]req_addr;wire[9:0]req_tag;
 reg[23:0]d_lines=16;reg req_ready=1,rsp_v=0;reg[9:0]rsp_tag=0;
 reg[1087:0]rsp_data=0;reg xw_en=0;reg[9:0]xw_addr=0;reg[6:0]xw_grp=0;reg[2047:0]xw_data=0;
 generate if(QWEN)begin:g_q
 ot_gpu_sm_q u_sm(.clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_scale(1'b0),
 .busy(busy),.d_valid(d_valid),.d_ready(d_ready),.d_base(32'd0),.d_lines(d_lines),.req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
 .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data[1023:0]),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp[0:0]),.xw_data(xw_data),
 .sw_en(1'b0),.sw_addr(12'd0),.sw_data(16'd0),.rv(rv),.rrow(rrow),.rdata(rdata),.fault(fault),.arrive(arrive),.release_in(release_in),.released(released));
 end else begin:g_ds
 ot_gpu_sm_v u_sm(.clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(1'b0),.op_fmt(2'd0),
 .busy(busy),.d_valid(d_valid),.d_ready(d_ready),.d_base(32'd0),.d_lines(d_lines),.req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
 .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.xw_en(xw_en),.xw_addr(xw_addr[6:0]),.xw_grp(xw_grp),.xw_data(xw_data),
 .rv(rv),.rrow(rrow),.rdata(rdata),.fault(fault),.arrive(arrive),.release_in(release_in),.released(released));
 end endgenerate
 wire issue_valid,weight_wait,x_wait;
 generate if(QWEN)begin
 assign issue_valid=g_q.u_sm.adv&&g_q.u_sm.row_ok;
 assign weight_wait=g_q.u_sm.w_ready&&!g_q.u_sm.w_valid;
 assign x_wait=g_q.u_sm.u_issue.iss_v==0&&busy&&!g_q.u_sm.x_rdy;
 end else begin
 assign issue_valid=g_ds.u_sm.adv&&g_ds.u_sm.row_ok;
 assign weight_wait=g_ds.u_sm.w_ready&&!g_ds.u_sm.w_valid;
 assign x_wait=0;
 end endgenerate
 // Test HBM request response model, finite512 physical outstanding slots,
 // real staging ring/order/MAX_OUT exercised; explicit seven-cycle return.
 integer ready_at[0:511];reg[9:0]pending_tag[0:511];reg pending[0:511];
 integer cyc=0,pick,i,l,case_id=-1,phase=0,rows=16,nres=0,nconsumer=0;
 integer last_producer=-1,first_issue=-1,last_consumer=-1,rf_wait=0,weight_stalls=0,x_stalls=0,peak_pending=0,pcnt;
 reg cap_reserve=0,drain_enable=0,operands_visible=0,activation_visible=0;
 wire capture_ready,capture_done,capture_visible,capture_eligible,capture_busy,capture_fault,capture_ack_ready;
 wire capture_wr_valid;wire[8:0]capture_addr;wire[4095:0]capture_data;
 wire[12:0]capture_rows;wire[9:0]capture_committed;
 reg[31:0]producer_expected,consumer_expected;
 integer accepted_host_writes=0,simd_accepts=0,simd_pass=0;
 reg chain_active=0,negative_epoch_test=0,producer_done_sent=0;
 reg host_rd_valid=0;wire host_rd_ready;reg[8:0]host_a=0,host_b=0;
 wire host_rsp_valid;reg host_rsp_ready=0;wire[4095:0]host_rsp_a,host_rsp_b;
 wire host_wr_valid,host_wr_ready;wire[8:0]host_dst;wire[4095:0]host_wdata;
 wire host_ack_valid,host_ack_ready;
 reg op_valid=0,cap_valid=0,cap_last=0,producer_done_valid=0,ack_retire_enable=1,fence_ready=0;
 wire op_ready,cap_ready,vector_ACK_visible,writes_visible,fence_valid,pending_write,fence_fault;
 reg[7:0]op_epoch=0,cap_epoch=0,producer_done_epoch=0;
 reg[9:0]op_vectors=0;reg[8:0]cap_addr=0;reg[4095:0]cap_data=0;
 wire[8:0]vector_ACK_addr;wire[7:0]vector_ACK_epoch,fence_epoch;
 ot_gpu_rf_visibility_fence #(.ENABLE(1)) RF_fence(
 .clk(clk),.rst_n(rst_n),.op_valid(op_valid),.op_ready(op_ready),.op_epoch(op_epoch),.op_vectors(op_vectors),
 .cap_valid(negative_epoch_test?cap_valid:(capture_wr_valid&&drain_enable)),.cap_ready(cap_ready),
 .cap_epoch(negative_epoch_test?cap_epoch:op_epoch),.cap_addr(negative_epoch_test?cap_addr:capture_addr),
 .cap_last(negative_epoch_test?cap_last:(capture_addr==nvec-1)),.cap_data(negative_epoch_test?cap_data:capture_data),
 .producer_done_valid(producer_done_valid),.producer_done_epoch(producer_done_epoch),
 .host_wr_valid(host_wr_valid),.host_wr_ready(host_wr_ready),.host_dst(host_dst),.host_wdata(host_wdata),
 .host_ack_valid(host_ack_valid),.host_ack_ready(host_ack_ready),.ack_retire_enable(capture_ack_ready),
 .vector_ACK_visible(vector_ACK_visible),.vector_ACK_addr(vector_ACK_addr),.vector_ACK_epoch(vector_ACK_epoch),
 .writes_visible(writes_visible),.fence_valid(fence_valid),.fence_ready(fence_ready),.fence_epoch(fence_epoch),
 .pending_write(pending_write),.fault(fence_fault));
 ot_gpu_matrix_capture_audit #(.ENABLE(1),.NC(NC)) capture_fence(
 .clk(clk),.rst_n(rst_n),.reserve_valid(cap_reserve),.reserve_rows(op_rows),.reserve_ready(capture_ready),
 .row_valid(rv&&phase==0),.row_index(rrow),.row_data(rdata),.wr_valid(capture_wr_valid),
 .wr_ready(cap_ready&&drain_enable&&!negative_epoch_test),.wr_addr(capture_addr),.wr_data(capture_data),
 .ack_valid(host_ack_valid),.retire_enable(ack_retire_enable),.ack_ready(capture_ack_ready),
 .operands_visible(operands_visible),.activation_visible(activation_visible),.matrix_released(released),.lease_release(1'b0),
 .capture_done(capture_done),.rf_visible_done(capture_visible),.consumer_eligible(capture_eligible),.busy(capture_busy),
 .accepted_rows(capture_rows),.committed_vectors(capture_committed),.fault(capture_fault));
 reg simd_valid=0;wire simd_ready;reg[8:0]simd_a=0,simd_b=0,simd_dst=0;
 wire simd_done,simd_fault;reg simd_done_ready=0;
 reg scratch_valid=0,scratch_write=0;wire scratch_ready;reg[9:0]scratch_addr=0;reg[511:0]scratch_wdata=0;
 wire scratch_done;reg scratch_done_ready=0;wire[511:0]scratch_rdata;
 ot_gpu_full_sm_service #(.ENABLE(1)) service(.clk(clk),.rst_n(rst_n),
 .host_rd_valid(host_rd_valid),.host_rd_ready(host_rd_ready),.host_a(host_a),.host_b(host_b),.host_rsp_valid(host_rsp_valid),.host_rsp_ready(host_rsp_ready),.host_rsp_a(host_rsp_a),.host_rsp_b(host_rsp_b),
 .host_wr_valid(host_wr_valid),.host_wr_ready(host_wr_ready),.host_dst(host_dst),.host_wdata(host_wdata),.host_ack_valid(host_ack_valid),.host_ack_ready(host_ack_ready),
 .simd_valid(simd_valid),.simd_ready(simd_ready),.simd_mul(1'b0),.simd_a(simd_a),.simd_b(simd_b),.simd_dst(simd_dst),.simd_done(simd_done),.simd_done_ready(simd_done_ready),.simd_fault(simd_fault),
 .scratch_valid(scratch_valid),.scratch_write(scratch_write),.scratch_ready(scratch_ready),.scratch_addr(scratch_addr),.scratch_wdata(scratch_wdata),.scratch_done(scratch_done),.scratch_done_ready(scratch_done_ready),.scratch_rdata(scratch_rdata));
 task stamp(input string name);$display("STAMP case=%0d qwen=%0d name=%s cycle=%0d",case_id,QWEN,name,cyc);endtask
 always @(posedge clk)begin
 cyc=cyc+1;rsp_v<=0;
 if(rst_n)begin
  if(req_v&&req_ready)begin
   pick=-1;for(i=0;i<512;i=i+1)if(!pending[i]&&pick<0)pick=i;
   if(pick<0)$fatal(1,"finite512 HBM tracker overflow");
   pending[pick]=1;pending_tag[pick]=req_tag;ready_at[pick]=cyc+7;
  end
  pick=-1;pcnt=0;for(i=0;i<512;i=i+1)begin
   if(pending[i])begin pcnt=pcnt+1;if(ready_at[i]<=cyc&&pick<0)pick=i;end
  end
  if(pcnt>peak_pending)peak_pending=pcnt;
  if(pick>=0)begin
   rsp_v<=1;rsp_tag<=pending_tag[pick];pending[pick]=0;rsp_data<=0;
   if(QWEN)for(l=0;l<128;l=l+1)rsp_data[8*l+:8]<=8'd1;
   else for(l=0;l<64;l=l+1)rsp_data[16*l+:16]<=16'h3f80;
  end
  if(host_wr_valid&&host_wr_ready)begin
   accepted_host_writes=accepted_host_writes+1;
   if(chain_active)$fatal(1,"host overwrite between dependent SIMD operations");
   if(accepted_host_writes==1)stamp("RF_first_write_accept");
   $display("RF_VECTOR_WRITE case=%0d index=%0d epoch=%0d cycle=%0d",case_id,host_dst,op_epoch,cyc);
  end
  if(simd_valid&&simd_ready)begin
   simd_accepts=simd_accepts+1;
   $display("SIMD_ALIAS_ACCEPT case=%0d pass=%0d index=%0d a=%0d b=%0d dst=%0d cycle=%0d",case_id,simd_pass,simd_a,simd_a,simd_b,simd_dst,cyc);
   if(!chain_active||accepted_host_writes!=nvec)$fatal(1,"SIMD accepted before actual RF write fence");
  end
  if(capture_fault)$fatal(1,"Maxwell capture contract fault");
  if(fence_fault&&!negative_epoch_test)$fatal(1,"RF fence contract fault");
  if(host_wr_valid&&!host_wr_ready||host_rd_valid&&!host_rd_ready||simd_valid&&!simd_ready)rf_wait=rf_wait+1;
  if(weight_wait)weight_stalls=weight_stalls+1;if(x_wait)x_stalls=x_stalls+1;
  if(issue_valid&&phase==1&&first_issue<0)begin first_issue=cyc;stamp("consumer_first_valid_issue");end
  if(rv)begin
   if(phase==0)begin
    if(nres==0)stamp("producer_first_rv");
    if(rrow!=nres)$fatal(1,"row order/tag mismatch got%0d expected%0d",rrow,nres);
    if(nres>=rows)$fatal(1,"unreserved producer row");
    for(l=0;l<NC;l=l+1)begin
     if(rdata[32*l+:32]!==producer_expected)$fatal(1,"producer exact mismatch row%0d col%0d got%h",rrow,l,rdata[32*l+:32]);
    end
    nres=nres+1;
    if(nres==rows)begin last_producer=cyc;stamp("producer_last_rv");end
   end else begin
    if(rrow!=nconsumer)$fatal(1,"consumer row order");
    for(l=0;l<NC;l=l+1)if(rdata[32*l+:32]!==consumer_expected)$fatal(1,"dependent matrix mismatch row%0d col%0d got%h",rrow,l,rdata[32*l+:32]);
    nconsumer=nconsumer+1;if(nconsumer==rows)begin last_consumer=cyc;stamp("consumer_last_result");end
   end
  end
  if(fault||simd_fault)$fatal(1,"real arithmetic fault");
 end
 end
 reg[BEATS*2048-1:0]fragment;reg[4095:0]cooked,tmp;
 integer j,b,v,nvec,stall,vec_rows;
 task load_fragment(input reg[4095:0]data,input integer initial_one);
 begin
  fragment=0;
  if(QWEN)for(j=0;j<16*128;j=j+1)fragment[16*j+:16]=initial_one?16'h3f80:data[32*(j%128)+16+:16];
  else for(j=0;j<NC;j=j+1)for(b=0;b<64;b=b+1)fragment[j*XC+8*266+16*b+:16]=initial_one?16'h3f80:data[32*((j*64+b)%128)+16+:16];
  for(j=0;j<BEATS;j=j+1)begin
   @(negedge clk);xw_en=1;xw_grp=QWEN?(j%2):j;xw_addr=QWEN?(j/2):0;xw_data=fragment[2048*j+:2048];
  end
  @(negedge clk);xw_en=0;stamp(initial_one?"producer_x_last_write":"consumer_x_last_write");
 end endtask
 task launch;
 begin
  @(negedge clk);d_valid=1;d_lines=rows;
  do @(posedge clk);while(!d_ready);
  @(negedge clk);d_valid=0;
  if(phase==1 && (!capture_eligible||!chain_active||pending_write||host_rsp_valid||simd_done||scratch_done))$fatal(1,"nextmatrix premature visibility/lease");
  start=1;stamp(phase==0?"producer_start":"consumer_start");
  @(negedge clk);start=0;
 end endtask
 task fence_begin;
 begin
  @(negedge clk);op_epoch=case_id+1;op_vectors=nvec;op_valid=1;
  do @(posedge clk);while(!op_ready);
  @(negedge clk);op_valid=0;cap_reserve=1;
  if(!capture_ready)$fatal(1,"capture reservation unavailable");
  @(posedge clk);@(negedge clk);cap_reserve=0;stamp("RF_operation_reservation");
 end endtask
 task producer_drained;
 begin
  if(!producer_done_sent)begin
   while(nres<rows||busy)@(negedge clk);
   @(negedge clk);producer_done_epoch=op_epoch;producer_done_valid=1;
   @(posedge clk);@(negedge clk);producer_done_valid=0;producer_done_sent=1;
  end
 end endtask
 task rf_commit(input integer index,input integer hold_cycles);
 begin
  @(negedge clk);drain_enable=1;ack_retire_enable=0;
  do @(posedge clk);while(!(host_wr_valid&&host_wr_ready));
  if(host_dst!=index)$fatal(1,"capture offer vector order");
  if(index==nvec-1)stamp("RF_last_write_accept");
  @(negedge clk);drain_enable=0;
  while(!vector_ACK_visible)@(negedge clk);
  if(vector_ACK_addr!=index||vector_ACK_epoch!=op_epoch)$fatal(1,"ACK identity mismatch");
  $display("RF_VECTOR_ACK_VISIBLE case=%0d index=%0d epoch=%0d cycle=%0d",case_id,vector_ACK_addr,vector_ACK_epoch,cyc);
  if(index==0)stamp("RF_first_ACK_visible");
  if(index==nvec-1)begin stamp("RF_last_ACK_visible");producer_drained();end
  repeat(hold_cycles)begin
   @(negedge clk);
   if(!pending_write||!vector_ACK_visible||fence_valid||!host_ack_valid||(index==nvec-1&&!writes_visible))$fatal(1,"heldACK released fence");
  end
  ack_retire_enable=1;@(posedge clk);
  $display("RF_VECTOR_ACK_RETIRE case=%0d index=%0d epoch=%0d cycle=%0d",case_id,vector_ACK_addr,vector_ACK_epoch,cyc);
  if(index==nvec-1)stamp("RF_last_ACK_retire");
  @(negedge clk);ack_retire_enable=0;
 end endtask
 task retire_fence;
 begin
  producer_drained();
  while(!fence_valid)@(negedge clk);
  if(!capture_done||!capture_visible||!writes_visible||pending_write||fence_epoch!=op_epoch||accepted_host_writes!=nvec)$fatal(1,"premature RF fence");
  stamp("RF_fence_valid");fence_ready=1;@(posedge clk);
  @(negedge clk);fence_ready=0;chain_active=1;
 end endtask
 task vector_simd(input integer index);
 begin
  @(negedge clk);simd_a=index;simd_b=index;simd_dst=index;simd_valid=1;
  do @(posedge clk);while(!simd_ready);
  if(index==0)stamp("SIMD_first_accept");
  @(negedge clk);simd_valid=0;
  while(!simd_done)@(negedge clk);
  if(index==nvec-1)stamp("SIMD_last_done");
  // Held completion must retain RF ownership and block another operand read.
  host_a=index;host_b=index;host_rd_valid=1;
  repeat(4)begin @(negedge clk);if(!simd_done||host_rd_ready||host_rsp_valid)$fatal(1,"SIMD completion lease");end
  host_rd_valid=0;simd_done_ready=1;@(posedge clk);@(negedge clk);simd_done_ready=0;
 end endtask
 task rf_read;
 begin
  @(negedge clk);host_a=0;host_b=0;host_rd_valid=1;
  do @(posedge clk);while(!host_rd_ready);
  @(negedge clk);host_rd_valid=0;
  while(!host_rsp_valid)@(negedge clk);
  cooked=host_rsp_a;if(host_rsp_a!==host_rsp_b)$fatal(1,"mirrored visibility mismatch");
  for(j=0;j<128;j=j+1)if(cooked[32*j+:32]!==(QWEN?32'h44000000:32'h43800000))$fatal(1,"SIMD RF visibility mismatch");
  stamp("RF_operand_read_visible");
  // A second SIMD alias request must wait while the actual operand read lease is held.
  simd_a=0;simd_b=0;simd_dst=0;simd_valid=1;
  repeat(6)begin @(negedge clk);
   if(simd_ready||!host_rsp_valid||host_rsp_a!==cooked||host_rsp_b!==cooked)$fatal(1,"operand lease/backpressure violation");
  end
  simd_valid=0;host_rsp_ready=1;
  @(posedge clk);@(negedge clk);host_rsp_ready=0;
 end endtask
 task scratch_roundtrip;
 begin
  tmp=cooked;
  for(v=0;v<8;v=v+1)begin
   @(negedge clk);scratch_valid=1;scratch_write=1;scratch_addr=v;scratch_wdata=cooked[512*v+:512];
   do @(posedge clk);while(!scratch_ready);
   @(negedge clk);scratch_valid=0;while(!scratch_done)@(negedge clk);
   if(v==7)stamp("scratch_write_done");scratch_done_ready=1;
   @(posedge clk);@(negedge clk);scratch_done_ready=0;
  end
  for(v=0;v<8;v=v+1)begin
   @(negedge clk);scratch_valid=1;scratch_write=0;scratch_addr=v;
   do @(posedge clk);while(!scratch_ready);
   @(negedge clk);scratch_valid=0;while(!scratch_done)@(negedge clk);
   tmp[512*v+:512]=scratch_rdata;if(v==7)stamp("scratch_read_done");scratch_done_ready=1;
   @(posedge clk);@(negedge clk);scratch_done_ready=0;
  end
  if(tmp!==cooked)$fatal(1,"scratch visible exact mismatch");cooked=tmp;
 end endtask
 task run_case(input integer row_count,input integer hold_cycles,input integer use_scratch);
 begin
  @(negedge clk);rst_n=0;op_valid=0;cap_valid=0;producer_done_valid=0;fence_ready=0;ack_retire_enable=0;
  chain_active=0;negative_epoch_test=0;producer_done_sent=0;accepted_host_writes=0;simd_accepts=0;phase=0;rows=row_count;op_rows=row_count;nres=0;nconsumer=0;last_producer=-1;first_issue=-1;last_consumer=-1;rf_wait=0;weight_stalls=0;x_stalls=0;peak_pending=0;release_in=0;
  nvec=(rows*NC+127)/128;vec_rows=128/NC;case_id=case_id+1;
  producer_expected=QWEN?32'h43000000:32'h42800000;consumer_expected=QWEN?32'h47800000:32'h46800000;
  for(j=0;j<512;j=j+1)pending[j]=0;
  cap_reserve=0;drain_enable=0;operands_visible=0;activation_visible=0;
  repeat(4)@(negedge clk);rst_n=1;fence_begin();load_fragment(0,1);launch();
  for(b=0;b<nvec;b=b+1)begin
   while(nres<(b+1)*vec_rows&&nres<rows)@(negedge clk);
   rf_commit(b,(b==nvec-1)?hold_cycles:0);
  end
  while(busy)@(negedge clk);stamp("producer_busy_fall");stamp("producer_matrix_arrive");
  release_in=arrive;while(!released)@(negedge clk);stamp("producer_barrier_release");
  retire_fence();
  // Both operations consume RF results directly, sameaddr for operands/destination;
  // no host write occurs between them. Checks guard against the old three-op bench flaw.
  simd_pass=0;for(b=0;b<nvec;b=b+1)vector_simd(b);
  stamp("dependent_SIMD_chain_second_pass");
  simd_pass=1;for(b=0;b<nvec;b=b+1)vector_simd(b);
  if(accepted_host_writes!=nvec||simd_accepts!=2*nvec)$fatal(1,"dependent chain provenance/count");
  rf_read();if(use_scratch)scratch_roundtrip();
  operands_visible=1;load_fragment(cooked,0);activation_visible=1;phase=1;launch();
  while(nconsumer<rows)@(negedge clk);while(busy)@(negedge clk);stamp("consumer_busy_fall");
  release_in=arrive;while(!released)@(negedge clk);stamp("consumer_barrier_release");
  $display("CASE id=%0d qwen=%0d rows=%0d vectors=%0d hold_cycles=%0d scratch=%0d producer_to_consumer_issue_cycles=%0d rf_bank_wait_cycles=%0d weight_wait_cycles=%0d x_wait_cycles=%0d peak_HBM_pending=%0d",case_id,QWEN,rows,nvec,hold_cycles,use_scratch,first_issue-last_producer,rf_wait,weight_stalls,x_stalls,peak_pending);
 end endtask
 task reset_pending_ACK_case;
 integer before_writes;
 begin
  @(negedge clk);rst_n=0;phase=0;rows=16;op_rows=16;nres=0;nconsumer=0;last_producer=-1;
  accepted_host_writes=0;simd_accepts=0;chain_active=0;negative_epoch_test=0;producer_done_sent=0;
  op_valid=0;cap_valid=0;producer_done_valid=0;fence_ready=0;ack_retire_enable=0;
  case_id=case_id+1;nvec=rows*NC/128;
  producer_expected=QWEN?32'h43000000:32'h42800000;
  for(j=0;j<512;j=j+1)pending[j]=0;
  cap_reserve=0;drain_enable=0;operands_visible=0;activation_visible=0;
  repeat(4)@(negedge clk);rst_n=1;fence_begin();load_fragment(0,1);launch();
  while(nres<rows||busy)@(negedge clk);
  @(negedge clk);drain_enable=1;
  do @(posedge clk);while(!(host_wr_valid&&host_wr_ready));
  @(negedge clk);drain_enable=0;while(!vector_ACK_visible)@(negedge clk);
  producer_drained();simd_a=0;simd_b=0;simd_dst=0;simd_valid=1;
  repeat(4)begin @(negedge clk);
   if(!host_ack_valid||!pending_write||fence_valid||simd_ready)$fatal(1,"pending ACK did not fence dependent alias");
  end
  stamp("reset_during_actual_RF_ACK");rst_n=0;simd_valid=0;
  repeat(2)@(negedge clk);
  if(pending_write||vector_ACK_visible||fence_valid||writes_visible||host_ack_valid)$fatal(1,"reset retained stale visibility");
  // SRAM contents intentionally unspecified across reset; no stale-data read.
  rst_n=1;op_epoch=op_epoch+1;op_vectors=1;op_valid=1;
  do @(posedge clk);while(!op_ready);
  @(negedge clk);op_valid=0;negative_epoch_test=1;before_writes=accepted_host_writes;
  cap_valid=1;cap_epoch=op_epoch-1;cap_addr=0;cap_last=1;
  @(posedge clk);@(negedge clk);
  if(cap_ready||host_wr_valid||!fence_fault||fence_valid||accepted_host_writes!=before_writes)$fatal(1,"stale epoch accepted after reset");
  cap_valid=0;rst_n=0;repeat(2)@(negedge clk);negative_epoch_test=0;
  $display("RESET_RF_FENCE_PASS qwen=%0d actualmatrixproducer=1 staleepoch_rejected=1",QWEN);
 end endtask
 initial begin
  reset_pending_ACK_case();
  run_case(16,0,0);run_case(16,0,1);run_case(4096,0,0);run_case(4096,240,0);
  $display("CONNECTED_RF_FENCE_PASS qwen=%0d cases=4 plus_reset=1 dependent_alias_ops=2_per_vector no_blackboxes=1",QWEN);$finish;
 end
 initial begin #3000000;$fatal(1,"connected audit finite timeout");end
endmodule
