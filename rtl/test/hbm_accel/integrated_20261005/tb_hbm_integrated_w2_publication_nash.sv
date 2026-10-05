`timescale 1ns/1ps
// Component fixture: actual CP20, W2 sink, shared protected borrower and byte RAM.
// Distinct literal payloads are test stimulus, not native arithmetic outputs.
// This component has root POR only; it does not certify parent warm quarantine.
module tb_hbm_integrated_w2_publication_nash;
 parameter integer REGISTERED_SUBBLOCKS=0;
 parameter integer PROTECTED_TRANSACTION_PIPELINE=0;
 `include "private_alloc.svh"
 reg clk=0; always #5 clk=~clk;
 reg por_n=0,cmd_we=0,db_v=0,cpl_rdy=0;
 reg [1:0] cmd_addr=0; reg [63:0] cmd_wdata=0;
 localparam [31:0] JOB=32'h9234abcd, OPA=32'h00002317, OPB=32'h0000b5a2;
 localparam [3:0] GEN=4'h9;
 localparam [16:0] TOKEN=17'h1a321;
 localparam [19:0] POS=20'hfffff;
 localparam [72:0] FRAME={POS,TOKEN,GEN,JOB};
 wire db_rdy,cpl_v; wire [1:0] launch_v; wire [31:0] launch_pc;
 wire [16:0] launch_token,cpl_token; wire [19:0] launch_pos,cpl_position;
 wire [31:0] cpl_job,cpl_cycles,st_kernels,st_busy; wire [3:0] cpl_generation,cpl_status;
 reg [1:0] sm_done=0,res_v=0; reg [63:0] res_data=0;
 wire shared_fault,sink_fault;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2),.NCMD(4)) cp(
  .clk(clk),.rst_n(por_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
  .db_v(db_v),.db_rdy(db_rdy),.db_token(TOKEN),.db_pos(POS),.db_job(JOB),.db_generation(GEN),
  .cpl_position(cpl_position),.cpl_job(cpl_job),.cpl_generation(cpl_generation),
  .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(launch_token),.launch_pos(launch_pos),
  .sm_done(sm_done),.sm_fault({1'b0,shared_fault|sink_fault}),.res_v(res_v),.res_data(res_data),
  .cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_token(cpl_token),.cpl_status(cpl_status),
  .cpl_cycles(cpl_cycles),.st_kernels(st_kernels),.st_busy(st_busy));
 reg lease_requested=0,reserve_v=0,release_intent=0,allocated=0;
 reg native_done=0,result_v=0; reg [31:0] result_op=0;
 reg [11:0] result_row=0; reg [255:0] result_data=0;
 wire [2:0] grants,releases;
 wire source_permit,retained,sink_done,sink_quiet,sink_retire_r,reserve_r;
 wire s_req_v,s_req_r,s_rsp_v,s_rsp_r;
 wire [336:0] s_req; wire [272:0] s_rsp;
 wire [3:0] req_rdy,rsp_v,rsp_we,response_authorized;
 wire [63:0] rsp_tag; wire [1023:0] rsp_data;
 wire m_req_v,m_req_ready,m_req_we,m_rsp_ready;
 wire [31:0] m_req_addr,m_req_strb; wire [255:0] m_req_data;
 wire [15:0] m_req_tag; reg m_rsp_v=0,m_rsp_we=0;
 reg [15:0] m_rsp_tag=0; reg [255:0] m_rsp_data=0;
 wire shared_idle,native_credit_empty;
 integer cycle=0,writes=0,reads=0,verified=0,released=0,request_stalls=0,delivery_stalls=0;
 integer provider_age=0,accepted_requests=0,consumed_responses=0;
 reg provider_pending=0,corrupt=0,corrupted=0,cp_callback=0;
 reg control_corrupt=0,owner_corrupt=0,protection_injected=0;
 wire protection_negative=control_corrupt||owner_corrupt;
 reg [7:0] ram[0:RAM_BYTES-1];
 wire provider_drained=!provider_pending&&!m_rsp_v&&accepted_requests==consumed_responses;
 wire installed=allocated && BASE_A[5:0]==0 && BASE_B[5:0]==0 &&
  LIMIT_A==BASE_A+64 && LIMIT_B==BASE_B+64 && LIMIT_A<=BASE_B && LIMIT_B<=RAM_BYTES;
 wire delivery_enabled=cycle%7>=2;
 // Same parent hook: native completion alone is insufficient to request release.
 wire release_v=release_intent&&sink_retire_r;
 wire release_accept=release_v&&releases[2];
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) owner(
  .clk(clk),.por_n(por_n),.native_clients_drained(accepted_requests==consumed_responses),
  .cdc_drained(provider_drained),.observe_req(4'b0),.observe_rsp(4'b0),
  .observe_req_we(4'b0),.observe_rsp_we(4'b0),.observe_req_tag(64'b0),.observe_rsp_tag(64'b0),
  .return_offer(4'b0),.response_authorized(response_authorized),
  .native_job(JOB),.native_gen(GEN),.native_token(TOKEN),.native_pos(POS),.native_credit_empty(native_credit_empty),
  .lease_v({lease_requested,2'b0}),.borrower_quiet({!retained,2'b11}),
  .lease_job({JOB,64'b0}),.lease_gen({GEN,8'b0}),.lease_token({TOKEN,34'b0}),.lease_pos({POS,40'b0}),
  .lease_granted(grants),.release_v({release_v,2'b0}),.release_r(releases),
  .release_job({JOB,64'b0}),.release_gen({GEN,8'b0}),.release_token({TOKEN,34'b0}),.release_pos({POS,40'b0}),
  .req_v({s_req_v,3'b0}),.req_rdy(req_rdy),.req_we({s_req[336],3'b0}),
  .req_addr({s_req[335:304],96'b0}),.req_wdata({s_req[303:48],768'b0}),
  .req_wstrb({s_req[47:16],96'b0}),.req_tag({s_req[15:0],48'b0}),
  .rsp_v(rsp_v),.rsp_rdy({s_rsp_r&&delivery_enabled,3'b0}),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_ready),.m_req_we(m_req_we),.m_req_addr(m_req_addr),
  .m_req_wdata(m_req_data),.m_req_wstrb(m_req_strb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_ready),.m_rsp_we(m_rsp_we),.m_rsp_tag(m_rsp_tag),.m_rsp_data(m_rsp_data),
  .idle(shared_idle),.fault(shared_fault));
 assign s_req_r=req_rdy[3];
 assign s_rsp_v=rsp_v[3]&&delivery_enabled;
 assign s_rsp={rsp_tag[63:48],rsp_we[3],rsp_data[1023:768]};
 ot_hbm_integrated_w2_result_sink #(.ENABLE(1),.REGISTERED_SUBBLOCKS(REGISTERED_SUBBLOCKS),.PROTECTED_TRANSACTION_PIPELINE(PROTECTED_TRANSACTION_PIPELINE)) sink(
  .clk(clk),.por_n(por_n),.owned(grants[2]),.installed(installed),.reserve_v(reserve_v),.reserve_r(reserve_r),
  .pair_op(1'b1),.rows_a(2'd2),.rows_b(2'd2),.op_a(OPA),.op_b(OPB),
  .base_a(BASE_A),.limit_a(LIMIT_A),.base_b(BASE_B),.limit_b(LIMIT_B),.provider_tag(16'hf239),.frame(FRAME),
  .source_permit(source_permit),.retained(retained),.done(sink_done),.quiet(sink_quiet),.fault(sink_fault),
  .result_v(result_v),.result_op(result_op),.result_row(result_row),.result_data(result_data),
  .native_done(native_done),.retire_v(release_accept),.retire_r(sink_retire_r),
  .req_v(s_req_v),.req_r(s_req_r),.req(s_req),.rsp_v(s_rsp_v),.rsp_r(s_rsp_r),.rsp(s_rsp));
 function automatic [255:0] literal_row(input integer slot);
  for(integer k=0;k<8;k=k+1)literal_row[k*32+:32]=32'h82451037 ^ (32'h01371b29*32'(slot+1)) ^ (32'h01020408*32'(k+1));
 endfunction
 function automatic integer address_slot(input integer a);
  if(a==BASE_A)address_slot=0;else if(a==BASE_A+32)address_slot=1;
  else if(a==BASE_B)address_slot=2;else if(a==BASE_B+32)address_slot=3;else address_slot=-1;
 endfunction
 assign m_req_ready=!provider_pending&&!m_rsp_v&&(cycle%5>=2);
 integer slot,j; reg [255:0] expected_row;
 always @(posedge clk)begin
  if(por_n)begin
   cycle<=cycle+1;
   if(cycle>2000)$fatal(1,"logical progress exhausted: cycle=%0d writes=%0d reads=%0d verified=%0d",cycle,writes,reads,verified);
   if(shared_fault&&!protection_negative)$fatal(1,"shared owner fault cycle=%0d",cycle);
   if(sink_fault&&!corrupt&&!protection_negative)$fatal(1,"normal sink fault cycle=%0d",cycle);
   if(m_req_v&&!m_req_ready)request_stalls<=request_stalls+1;
   if(rsp_v[3]&&!delivery_enabled)delivery_stalls<=delivery_stalls+1;
   if((release_accept||cp_callback||cpl_v)&&verified!=4&&!corrupt&&
      (!protection_negative||release_accept||cp_callback||cpl_status==0))$fatal(1,"early release/CP END before all four payload readbacks");
   if(protection_injected&&(release_accept||cp_callback||(cpl_v&&cpl_status==0)))
    $fatal(1,"protection corruption released accepted debt or posted successful CPL");
   sm_done<=0;res_v<=0;
   if(release_accept)begin
    if(!provider_drained||!sink_done||verified!=4)$fatal(1,"release without checked provider drain");
    released<=released+1;cp_callback<=1;
    sm_done<=2'b01;res_v<=2'b01;res_data<={32'b0,15'b0,TOKEN};
    $display("ACTUAL_SHARED_RELEASE cycle=%0d verified=%0d",cycle,verified);
   end
   if(m_req_v&&m_req_ready)begin
    slot=address_slot(integer'(m_req_addr));
    if(slot<0||m_req_addr+32>RAM_BYTES||!installed||!grants[2])$fatal(1,"unallocated byte address or unowned request %h",m_req_addr);
    provider_pending<=1;provider_age<=0;accepted_requests<=accepted_requests+1;
    m_rsp_tag<=m_req_tag;m_rsp_we<=m_req_we;
    expected_row=literal_row(slot);
    if(m_req_we)begin
     if(m_req_strb!==32'hffffffff)$fatal(1,"partial unexpected strobe");
     for(j=0;j<8;j=j+1)if(m_req_data[j*32+:32]!==expected_row[j*32+:32])$fatal(1,"write original row%0d word%0d mismatch",slot,j);
     for(j=0;j<32;j=j+1)if(m_req_strb[j])ram[integer'(m_req_addr)+j]<=m_req_data[j*8+:8];
     m_rsp_data<=0;writes<=writes+1;
    end else begin
     for(j=0;j<32;j=j+1)m_rsp_data[j*8+:8]<=ram[integer'(m_req_addr)+j];
     if(corrupt&&!corrupted)begin m_rsp_data[0]<=~ram[integer'(m_req_addr)][0];corrupted<=1;end
     reads<=reads+1;
    end
    $display("PROVIDER_ACCEPT cycle=%0d we=%0d byte_address=%0d slot=%0d",cycle,m_req_we,m_req_addr,slot);
   end
   if(provider_pending&&!m_rsp_v)begin
    provider_age<=provider_age+1;
    if(provider_age==4)m_rsp_v<=1;
   end
   if(m_rsp_v&&m_rsp_ready)begin
    m_rsp_v<=0;provider_pending<=0;consumed_responses<=consumed_responses+1;
   end
   if(s_rsp_v&&s_rsp_r&&!s_rsp[256])begin
    // Independently compare all eight words of the original restored row.
    slot=address_slot(integer'(m_req_addr));expected_row=literal_row(slot);
    if(s_rsp[255:0]!==expected_row)begin
     if(!corrupt)$fatal(1,"normal original consumer mismatch slot%0d",slot);
     $display("CORRUPT_READBACK_DETECTED cycle=%0d slot=%0d",cycle,slot);
    end else begin
     verified<=verified+1;$display("ORIGINAL_ROW_VERIFIED cycle=%0d slot=%0d",cycle,slot);
    end
   end
  end
 end
 wire callback_seat_available;
 generate if(PROTECTED_TRANSACTION_PIPELINE)begin:callback_reservation
  assign callback_seat_available=retained&&grants[2]&&!sink_fault&&sink.transaction_pipeline.u_pipe.have_free;
 end else begin:callback_legacy
  assign callback_seat_available=source_permit;
 end endgenerate
 task automatic issue_row(input integer s);
  @(negedge clk);
  if(!callback_seat_available)$fatal(1,"no retained owner/free preGO seat for no-ready result slot%0d",s);
  result_v=1;result_op=s<2?OPA:OPB;result_row=12'(s%2);result_data=literal_row(s);
 endtask
 generate if(PROTECTED_TRANSACTION_PIPELINE)begin:inject_pipeline
  initial begin
   wait(control_corrupt);wait(provider_pending);@(negedge clk);
   sink.transaction_pipeline.u_pipe.code[71]=sink.transaction_pipeline.u_pipe.code[71]^72'h3;
   protection_injected=1;
  end
  initial begin
   integer ce_word,ce_start,ce_stall_edges;
   if($test$plusargs("CORRECT_PAYLOAD_CE")||$test$plusargs("CORRECT_SELECTED_PAYLOAD_CE"))begin
    ce_word=$test$plusargs("CORRECT_SELECTED_PAYLOAD_CE")?51:8;
    wait(provider_pending);@(negedge clk);
    ce_start=cycle;ce_stall_edges=0;
    sink.transaction_pipeline.u_pipe.code[ce_word]=sink.transaction_pipeline.u_pipe.code[ce_word]^72'h1;
    // Check the real accepted-debt owner on every correction service edge.
    // The selected-stage case targets the payload held for the accepted WR.
    @(negedge clk);
    while(!sink.transaction_pipeline.u_pipe.normal)begin
     if(sink_fault||source_permit||s_req_v||s_rsp_r||!retained||!owner.on.debt[0])
      $fatal(1,"CE used unchecked permission or lost accepted debt");
     ce_stall_edges=ce_stall_edges+1;
     @(negedge clk);
    end
    if(sink_fault||sink.transaction_pipeline.u_pipe.ce[ce_word]||!retained||ce_stall_edges==0)
     $fatal(1,"CE did not hold/recheck/scrub protected payload");
    $display("PASS_CORRECT_PAYLOAD_CE codeword=%0d start=%0d resume=%0d stall_edges=%0d held_owner_debt=1 protected_recheck=1",ce_word,ce_start,cycle,ce_stall_edges);
   end
  end
 end else if(REGISTERED_SUBBLOCKS)begin:inject_registered
  initial begin
   wait(control_corrupt);wait(provider_pending);@(negedge clk);
   // Two parity-invalid copies must fail closed. The routed alias census gives
   // no independent-physical-copy credit; this is source functional injection.
   sink.registered_subblocks.control_view.a[0]=~sink.registered_subblocks.control_view.a[0];
   sink.registered_subblocks.control_view.b[0]=~sink.registered_subblocks.control_view.b[0];
   protection_injected=1;
  end
 end else begin:inject_legacy
  initial begin
   wait(control_corrupt);wait(provider_pending);@(negedge clk);
   sink.on.code[24]=sink.on.code[24]^72'h3;
   protection_injected=1;
  end
 end endgenerate
 initial begin
  wait(owner_corrupt);wait(provider_pending);@(negedge clk);
  owner.on.control_code=owner.on.control_code^72'h3;
  protection_injected=1;
 end
 reg [76:0] held_cpl;
 reg [15:0] debt_tag;reg debt_we;
 task automatic check_retained_protection_debt;
  wait(provider_pending);
  debt_tag=m_req_tag;debt_we=m_req_we;
  wait(protection_injected);
  // Allow the real provider/borrower to capture a return, but never retire it
  // through a corrupt authority. Check the actual existing protected ledger.
  repeat(12)begin
   @(negedge clk);
   if(!por_n||!retained||sink_retire_r||release_accept||released!=0||cp_callback||
      (cpl_v&&cpl_status==0)||s_req_v||m_req_v)
    $fatal(1,"accepted debt disappeared or escaped corrupt authority");
   if(!owner.on.debt[0]||owner.on.debt[19:4]!==debt_tag||owner.on.debt[3]!==debt_we||
      owner.on.fl[65]||owner.on.fh[65]||owner.on.frame[72:0]!==FRAME)
    $fatal(1,"protected accepted debt/tag/frame lost after authority corruption");
  end
  if(!(shared_fault||sink_fault))$fatal(1,"authority DUE did not assert fault");
  $display("AUTHORITY_CORRUPTION_ACCEPTED_DEBT_RETAINED control=%0d owner=%0d tag=%h",control_corrupt,owner_corrupt,debt_tag);
  $fatal(1,"EXPECTED_AUTHORITY_CORRUPTION_FAIL_CLOSED retained_debt=1 releases=0 root_por=1");
 endtask
 initial begin
  corrupt=$test$plusargs("CORRUPT_READBACK");
  control_corrupt=$test$plusargs("CORRUPT_SINK_CONTROL");
  owner_corrupt=$test$plusargs("CORRUPT_SHARED_OWNER");
  if(integer'(corrupt)+integer'(control_corrupt)+integer'(owner_corrupt)>1)
   $fatal(1,"select one concrete fault injection per run");
  for(integer k=0;k<RAM_BYTES;k=k+1)ram[k]=8'h6d;
  repeat(3)@(negedge clk);por_n=1;
  repeat(2)@(negedge clk);
  if(source_permit||reserve_r||grants!=0)$fatal(1,"cold source permission");
  // Existing Program.put generates these extents; fixture commits them explicitly.
  allocated=1;
  cmd_we=1;cmd_addr=0;cmd_wdata=64'h1000100000000321;
  @(negedge clk);cmd_addr=1;cmd_wdata=64'h2000000000000000;
  @(negedge clk);cmd_we=0;db_v=1;
  @(negedge clk);db_v=0;
  wait(launch_v[0]);
  if(launch_token!==TOKEN||launch_pos!==POS||launch_pc!==32'h321)$fatal(1,"actual CP launch identity");
  @(negedge clk);lease_requested=1;
  wait(grants[2]);@(negedge clk);
  if(source_permit)$fatal(1,"source permit before accepted output reservation");
  reserve_v=1;wait(reserve_r);@(negedge clk);reserve_v=0;lease_requested=0;
  wait(source_permit);
  issue_row(1);issue_row(2);issue_row(0);issue_row(3);
  @(negedge clk);result_v=0;native_done=1;release_intent=1;
  @(negedge clk);native_done=0;
  if(writes>=4||release_accept||cpl_v)$fatal(1,"early native completion did not precede physical publication");
  if(protection_negative)begin
   check_retained_protection_debt();
  end else if(corrupt)begin
   wait(sink_fault);repeat(2)@(negedge clk);
   if(released!=0||cp_callback||grants[2]!==1)$fatal(1,"corruption released ownership");
   if(cpl_v&&cpl_status==0)$fatal(1,"corruption posted successful completion");
   $fatal(1,"EXPECTED_CORRUPT_READBACK_FAIL_CLOSED retained_owner=1 released=0");
  end else begin
   wait(cpl_v);@(negedge clk);
   if(cpl_status!=0||cpl_token!==TOKEN||cpl_position!==POS||cpl_job!==JOB||cpl_generation!==GEN||released!=1||grants!=0)
    $fatal(1,"actual CP END/CPL original tuple or owner release mismatch");
   held_cpl={cpl_job,cpl_generation,cpl_position,cpl_token,cpl_status};
   repeat(12)begin @(negedge clk);
    if(!cpl_v||{cpl_job,cpl_generation,cpl_position,cpl_token,cpl_status}!==held_cpl||db_rdy)$fatal(1,"held CP completion mutated");
   end
   for(integer s=0;s<4;s=s+1)begin
    expected_row=literal_row(s);
    for(integer k=0;k<32;k=k+1)if(ram[(s<2?BASE_A:BASE_B)+(s%2)*32+k]!==expected_row[k*8+:8])$fatal(1,"final byte RAM row%0d byte%0d",s,k);
   end
   if(writes!=4||reads!=4||verified!=4||request_stalls==0||delivery_stalls==0||!provider_drained)$fatal(1,"exact traffic/stall/drain counts");
   cpl_rdy=1;@(negedge clk);cpl_rdy=0;
   if(cpl_v||!db_rdy)$fatal(1,"completion did not accept exactly once");
   $display("PASS W2_PUBLICATION_SHARED_CPEND_CPL rows=4 words=32 writes=%0d reads=%0d verified=%0d releases=%0d reqstall=%0d delivery_stall=%0d",writes,reads,verified,released,request_stalls,delivery_stalls);
   $finish;
  end
 end
endmodule
