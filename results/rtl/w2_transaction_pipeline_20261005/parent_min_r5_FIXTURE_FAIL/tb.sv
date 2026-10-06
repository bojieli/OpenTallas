`timescale 1ns/1ps
// Actual additive context + unchanged CP/reset hooks. Retained canonical R2
// caller rows and two emitted source frames; finite addressed RAM. No native
// arithmetic replay, full token, HBM timing or physical-clock qualification.
module tb_hbm_w2_protected_parent_min;
 reg clk=0,clk_mem=0;always #0.416666666667 clk=~clk;always #0.512 clk_mem=~clk_mem;
 localparam [31:0] JOB=32'h9234abcd,BASE=32'h071bd800;
 localparam [3:0] GEN=9;localparam [16:0] TOKEN=17'h1a321;localparam [19:0] POS=20'hfffff;
 localparam [72:0] FRAME={POS,TOKEN,GEN,JOB};
 reg por_n=0,cmd_we=0,db_v=0,cpl_rdy=0,warm_req=0;
 reg [1:0] cmd_addr=0;reg [63:0] cmd_data=0;
 wire cp_idle,cp_cpl_v,cp_cpl_rdy,cp_reset_n,warm_ack,warm_wait,all_drained,cpl_v;
 wire [1:0] launch_v;wire [31:0] launch_pc;wire [16:0] launch_token,cpl_token;
 wire [19:0] launch_pos,cpl_pos;wire [31:0] cpl_job;wire [3:0] cpl_gen,cpl_status;
 reg [1:0] sm_done=0,res_v=0;reg [63:0] res_data=0;
 wire db_ready=cp_idle&&all_drained&&!warm_wait;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2),.NCMD(4)) cp(
 .clk(clk),.rst_n(cp_reset_n),.cmd_we(cmd_we&&!warm_wait),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
 .db_v(db_v&&db_ready),.db_rdy(cp_idle),.db_token(TOKEN),.db_pos(POS),.db_job(JOB),.db_generation(GEN),
 .cpl_position(cpl_pos),.cpl_job(cpl_job),.cpl_generation(cpl_gen),.launch_v(launch_v),.launch_pc(launch_pc),
 .launch_token(launch_token),.launch_pos(launch_pos),.sm_done(sm_done),.sm_fault({1'b0,fault}),
 .res_v(res_v),.res_data(res_data),.cpl_v(cp_cpl_v),.cpl_rdy(cp_cpl_rdy),.cpl_token(cpl_token),.cpl_status(cpl_status),
 .cpl_cycles(),.st_kernels(),.st_busy());
 reg lease_v=0,reserve_v=0,release_intent=0,native_done=0,cv=0,caller_start=0;
 reg [7:0] crow=0;reg [255:0] cy=0;
 wire granted,release_r,reserve_r,permit,retained,sink_done,caller_ready,fault;
 reg native_req_v=0,map_valid=0;reg [31:0] native_req_addr=0;reg [9:0] native_req_tag=0;
 reg [2:0] map_sm=0,map_count=0;reg [15:0] map_offset=0;reg [3:0] map_lanes=0;
 reg [191:0] map_addresses=0;reg [95:0] map_tags=0,map_cfg=0;
 wire native_req_r,native_rsp_pending,native_rsp_v;wire [9:0] native_rsp_tag;wire [1087:0] native_rsp_data;
 wire m_req_v,m_req_rdy,m_req_we,m_rsp_rdy;wire [31:0] m_req_addr,m_req_strb;
 wire [255:0] m_req_data;wire [15:0] m_req_tag;
 reg m_rsp_v=0,m_rsp_we=0;reg [255:0] m_rsp_data=0;reg [15:0] m_rsp_tag=0;
 reg pending=0;integer age=0,accepted=0,consumed=0,writes=0,reads=0,native_accepts=0,native_returns=0,releases=0,cycle=0;
 wire provider_drained=!pending&&!m_rsp_v&&accepted==consumed;
 assign m_req_rdy=!pending&&!m_rsp_v&&cycle%5>=2;
 ot_hbm_w2_protected_parent_context #(.ENABLE(1),.PROTECTED_TRANSACTION_PIPELINE(1),.PROTECTED_PARENT_BOUNDARY(1)) dut(
 .clk_sm(clk),
 .rst_sm_n(por_n),
 .clk_mem(clk_mem),
 .rst_mem_n(por_n),
 .cp_reset_req(warm_req),
 .cp_idle(cp_idle),
 .cp_cpl_v(cp_cpl_v),
 .cp_cpl_rdy(cpl_rdy),
 .cp_reset_n(cp_reset_n),
 .cp_reset_ack(warm_ack),
 .cp_reset_wait(warm_wait),
 .all_routes_drained(all_drained),
 .qualified_cpl_v(cpl_v),
 .qualified_cpl_rdy(cp_cpl_rdy),
 .installed(1'b1),
 .weights_installed(1'b1),
 .reserve_v(reserve_v),
 .reserve_r(reserve_r),
 .source_permit(permit),
 .retained(retained),
 .done(sink_done),
 .pair_op(1'b1),
 .rows_a(2'd2),
 .rows_b(2'd2),
 .op_a(32'd0),
 .op_b(32'd1),
 .base_a(BASE),
 .limit_a(BASE+64),
 .base_b(BASE+64),
 .limit_b(BASE+128),
 .provider_tag(16'd62009),
 .frame(FRAME),
 .producer_cv(cv),
 .producer_fault('0),
 .producer_crow(crow),
 .producer_cy(cy),
 .producer_busy(cv),
 .producer_arrive('0),
 .producer_released('0),
 .caller_start(caller_start),
 .caller_sm_ready(1'b1),
 .caller_pair(1'b1),
 .caller_bound(1'b1),
 .caller_rows(9'd4),
 .caller_op_a(32'd0),
 .caller_op_b(32'd1),
 .caller_ctx_ready(caller_ready),
 .caller_busy(),
 .caller_arrive(),
 .caller_released(),
 .native_done(native_done),
 .lease_v(lease_v),
 .release_v(release_intent&&dut.sink_retire_r),
 .release_frame(FRAME),
 .lease_granted(granted),
 .release_r(release_r),
 .other_lease_v('0),
 .other_quiet(2'b11),
 .other_release_v('0),
 .other_lease_job('0),
 .other_release_job('0),
 .other_lease_gen('0),
 .other_release_gen('0),
 .other_lease_token('0),
 .other_release_token('0),
 .other_lease_pos('0),
 .other_release_pos('0),
 .other_grants(),
 .other_releases(),
 .native_clients_drained(provider_drained),
 .cdc_drained(provider_drained),
 .other_routes_drained(1'b1),
 .w2_quiet(!cv&&!native_req_v&&!native_rsp_pending),
 .observe_req('0),
 .observe_rsp('0),
 .observe_req_we('0),
 .observe_rsp_we('0),
 .return_offer('0),
 .observe_req_tag('0),
 .observe_rsp_tag('0),
 .native_job(JOB),
 .native_gen(GEN),
 .native_token(TOKEN),
 .native_pos(POS),
 .response_authorized(),
 .other_req_v('0),
 .other_req_we('0),
 .other_rsp_rdy('0),
 .other_req_addr('0),
 .other_req_wstrb('0),
 .other_req_wdata('0),
 .other_req_tag('0),
 .other_req_rdy(),
 .other_rsp_v(),
 .other_rsp_we(),
 .other_rsp_tag(),
 .other_rsp_data(),
 .native_req_v(native_req_v),
 .native_req_r(native_req_r),
 .native_req_addr(native_req_addr),
 .native_req_tag(native_req_tag),
 .map_valid(map_valid),
 .map_frame(FRAME),
 .map_native_addr(native_req_addr),
 .map_sm(map_sm),
 .map_compact_offset(map_offset),
 .map_lanes(map_lanes),
 .map_count(map_count),
 .map_byte_addresses(map_addresses),
 .map_tags(map_tags),
 .map_cfg(map_cfg),
 .native_delivery_permit(1'b1),
 .native_rsp_pending(native_rsp_pending),
 .native_rsp_v(native_rsp_v),
 .native_rsp_tag(native_rsp_tag),
 .native_rsp_data(native_rsp_data),
 .m_req_v(m_req_v),
 .m_req_rdy(m_req_rdy),
 .m_req_we(m_req_we),
 .m_req_addr(m_req_addr),
 .m_req_wstrb(m_req_strb),
 .m_req_wdata(m_req_data),
 .m_req_tag(m_req_tag),
 .m_rsp_v(m_rsp_v),
 .m_rsp_rdy(m_rsp_rdy),
 .m_rsp_we(m_rsp_we),
 .m_rsp_tag(m_rsp_tag),
 .m_rsp_data(m_rsp_data),
 .fault(fault)
 );
 reg [31:0] addresses[0:3267];reg [255:0] memory[0:3267];
 reg [447:0] maps[0:1];reg [1087:0] expected_native[0:1];reg [255:0] gold[0:3];
 function automatic integer locate(input [31:0] a);
  integer lo,hi,mid;begin locate=-1;lo=0;hi=3267;
   while(lo<=hi)begin mid=(lo+hi)/2;if(addresses[mid]==a)begin locate=mid;lo=hi+1;end
    else if(addresses[mid]<a)lo=mid+1;else hi=mid-1;end
  end
 endfunction
 integer index,slot;reg [255:0] expected_publication;
 always @(posedge clk_mem)if(por_n)begin
  if(m_req_v&&m_req_rdy)begin
   index=locate(m_req_addr);if(index<0||!granted)$fatal(1,"unallocated/unowned actual provider tuple");
   pending<=1;age<=0;accepted<=accepted+1;m_rsp_tag<=m_req_tag;m_rsp_we<=m_req_we;
   if(m_req_we)begin
    slot=(m_req_addr-BASE)/32;expected_publication=gold[slot];
    if(slot<0||slot>=4||m_req_strb!==32'hffffffff||m_req_data!==expected_publication)
     $fatal(1,"original canonical publication write mismatch");
    memory[index]<=m_req_data;m_rsp_data<=0;writes<=writes+1;
   end else begin m_rsp_data<=memory[index];if(m_req_addr>=BASE&&m_req_addr<BASE+128)reads<=reads+1;end
   $display("PARENT_PROVIDER_ACCEPT cycle=%0d we=%0d address=%h tag=%h",cycle,m_req_we,m_req_addr,m_req_tag);
  end else if(pending&&!m_rsp_v)begin age<=age+1;if(age==4)m_rsp_v<=1;end
  if(m_rsp_v&&m_rsp_rdy)begin pending<=0;m_rsp_v<=0;consumed<=consumed+1;end
 end
 integer current=0,saved_accepts;reg reset_seen=0,warm_requested=0;
 always @(posedge clk)if(por_n)begin
  cycle<=cycle+1;sm_done<=0;res_v<=0;
  if(fault)$fatal(1,"owned additive context fault cycle=%0d sink=%b sector=%b owner=%b cdc=%b reset=%b caller=%b state=%0d caller_cnt=%0d caller_row=%0d op=%0d rv=%b",cycle,dut.sink_fault,dut.adapter_fault,dut.shared_fault,dut.cdc_fault,dut.reset_fault,dut.caller_fault,dut.u_w2_sink.transaction_pipeline.u_pipe.state,dut.u_caller_cut.protected_caller.u_protected.cnt,dut.caller_row,dut.result_op,dut.result_v);
  if(native_req_v&&native_req_r)native_accepts<=native_accepts+1;
  if(native_rsp_v)begin
   if(native_rsp_tag!==10'(current*37)||native_rsp_data!==expected_native[current])$fatal(1,"actual source sector readback mismatch");
   native_returns<=native_returns+1;
  end
  if(release_intent&&release_r)begin
   if(writes!=4||reads!=4||!provider_drained||!sink_done)$fatal(1,"early owned publication release");
   releases<=releases+1;sm_done<=1;res_v<=1;res_data<={32'b0,15'b0,TOKEN};
   $display("PARENT_PUBLICATION_RELEASE cycle=%0d writes=%0d readbacks=%0d",cycle,writes,reads);
  end
  if(!cp_reset_n)begin
   reset_seen<=1;if(!cp_idle||!all_drained||retained||granted||!provider_drained)$fatal(1,"local reset erased accepted root debt");
  end
  if(!all_drained&&(!cp_reset_n||warm_ack))$fatal(1,"premature warm completion");
  if(warm_wait&&db_ready)$fatal(1,"warm admitted new CP work");
 end
 initial begin
  wait(accepted>consumed);@(negedge clk);warm_req=1;warm_requested=1;
  if(!granted||!retained)$fatal(1,"warm lacked real accepted owner/debt");
  $display("PARENT_WARM_REQUEST cycle=%0d accepted=%0d consumed=%0d",cycle,accepted,consumed);
 end
 reg [2047:0] dir,goldfile;reg [76:0] held_cpl;
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("GOLD=%s",goldfile))$fatal(1,"actual inputs required");
  $readmemh({dir,"/memory_addresses.hex"},addresses);$readmemh({dir,"/memory.hex"},memory);
  $readmemh({dir,"/maps.hex"},maps);$readmemh({dir,"/expected.hex"},expected_native);$readmemh(goldfile,gold);
  repeat(3)@(negedge clk);por_n=1;
  @(negedge clk);$display("STARTUP cp_idle=%b all_drained=%b fault=%b caller_quiet=%b transport=%b native_credit=%b shared_idle=%b adapter=%b reset=%b",cp_idle,all_drained,fault,dut.caller_quiet,dut.transport_drained,dut.native_credit_empty,dut.shared_idle,dut.adapter_drained,cp_reset_n);$fflush();
  wait(db_ready);@(negedge clk);
  cmd_we=1;cmd_addr=0;cmd_data=64'h1000100000000321;
  @(negedge clk);cmd_addr=1;cmd_data=64'h2000000000000000;
  @(negedge clk);cmd_we=0;db_v=1;@(negedge clk);db_v=0;
  wait(launch_v[0]);$display("REAL_CP_LAUNCH cycle=%0d",cycle);$fflush();@(negedge clk);lease_v=1;wait(granted);$display("REAL_PARENT_GRANT cycle=%0d",cycle);$fflush();@(negedge clk);lease_v=0;reserve_v=1;
  do @(posedge clk);while(!reserve_r);@(negedge clk);reserve_v=0;wait(permit);$display("REAL_PARENT_RESERVATION cycle=%0d",cycle);$fflush();
  for(current=0;current<2;current=current+1)begin
   @(negedge clk);{map_cfg,map_tags,map_addresses,native_req_addr,map_sm,map_offset,map_lanes,map_count}=maps[current];
   for(integer j=0;j<6;j=j+1)map_tags[j*16+:16]=16'(32768+current*6+j);
   native_req_tag=10'(current*37);saved_accepts=native_accepts;native_req_v=1;map_valid=1;
   wait(native_accepts!=saved_accepts);@(negedge clk);native_req_v=0;map_valid=0;
   wait(native_returns==current+1);@(negedge clk);
  end
  wait(caller_ready);@(negedge clk);caller_start=1;@(negedge clk);caller_start=0;
  for(integer row=0;row<4;row=row+1)begin cv=1;crow=8'(row);cy=gold[row];@(negedge clk);end
  cv=0;native_done=1;release_intent=1;@(negedge clk);native_done=0;
  wait(cpl_v);@(negedge clk);
  if(cpl_status||cpl_job!==JOB||cpl_gen!==GEN||cpl_pos!==POS||cpl_token!==TOKEN||releases!=1||granted||native_returns!=2)
   $fatal(1,"actual connected CPL/owner/source identity");
  held_cpl={cpl_job,cpl_gen,cpl_pos,cpl_token,cpl_status};
  repeat(12)begin @(negedge clk);
   if(!cpl_v||{cpl_job,cpl_gen,cpl_pos,cpl_token,cpl_status}!==held_cpl||!cp_reset_n||warm_ack||db_ready||!por_n)
    $fatal(1,"held CPL/reset quarantine changed");
  end
  cpl_rdy=1;@(negedge clk);cpl_rdy=0;wait(warm_ack);@(negedge clk);
  if(!warm_requested||!reset_seen||!por_n||!provider_drained||!all_drained||retained||granted||cpl_v)
   $fatal(1,"actual warm acknowledgement before matched drain");
  $display("PASS_PROTECTED_PARENT_WARM cycle=%0d publications=4 writes=%0d readbacks=%0d releases=%0d accepted=%0d consumed=%0d native_frames=%0d root_por=1 held_cpl=12",cycle,writes,reads,releases,accepted,consumed,native_returns);
  warm_req=0;wait(!warm_wait);@(negedge clk);if(!db_ready)$fatal(1,"CP admission failed to reopen");
  $finish;
 end
endmodule
