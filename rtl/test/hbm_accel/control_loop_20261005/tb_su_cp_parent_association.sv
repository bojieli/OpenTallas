`timescale 1ns/1ps
// One real CP LAUNCH/END, protected CP + real common borrower + association.
// Transaction consumer tests wiring/debt, not SU arithmetic or full-token rate.
module tb_su_cp_parent_association;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,cmd_we=0,db_v=0,cpl_ready=0;
 reg [7:0] cmd_addr=0;reg [63:0] cmd_data=0;
 wire db_rdy,cpl_v;wire [1:0] launch_v;wire [31:0] launch_pc,job;
 wire [3:0] gen;wire [16:0] token;wire [19:0] pos;
 reg [31:0] job_flip=0,pc_flip=0;reg [3:0] gen_flip=0;
 reg [16:0] token_flip=0;reg [19:0] pos_flip=0;
 wire [31:0] live_job=job^job_flip,live_pc=launch_pc^pc_flip;
 wire [3:0] live_gen=gen^gen_flip;wire [16:0] live_token=token^token_flip;
 wire [19:0] live_pos=pos^pos_flip;
 wire lease_v,release_v,qualified_owned,pending,quiet,selected,done,cp_fault;
 wire [31:0] held_job,held_pc;wire [3:0] held_gen;
 wire [16:0] held_token;wire [19:0] held_pos;
 wire [2:0] grants,releases;wire shared_fault,shared_idle,native_empty;
 reg exec_done=0;reg [3:0] retired=0;
 wire exec_owned,new_permit,association_fault;
 reg request_v=0,response_ready=0;
 wire [3:0] req_rdy,rsp_v,rsp_we;wire [63:0] rsp_tag;wire [1023:0] rsp_data;
 wire m_req_v,m_req_we,m_rsp_rdy;wire [31:0] m_req_addr,m_req_strb;
 wire [255:0] m_req_data;wire [15:0] m_req_tag;
 reg m_req_ready=0,m_rsp_v=0;reg [15:0] m_rsp_tag=0;
 reg [255:0] m_rsp_data=0;
 wire routes_drained=quiet&&!selected&&shared_idle&&!exec_done;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2)) cp(
  .clk(clk),.rst_n(por_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
  .db_v(db_v&&routes_drained),.db_rdy(db_rdy),.db_token(17'h12345),.db_pos(20'habcde),.db_job(32'h12345678),.db_generation(4'd3),
  .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(token),.launch_pos(pos),
  .cpl_job(job),.cpl_generation(gen),.cpl_position(),.sm_done({1'b0,done}),
  .sm_fault({1'b0,cp_fault|association_fault}),.res_v(2'd0),.res_data(64'd0),
  .cpl_v(cpl_v),.cpl_rdy(cpl_ready&&routes_drained));
 ot_hbm_integrated_su_cp_bind #(.ENABLE(1),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1),.REGISTERED_BOUNDARY(1),.BALANCED_OWNER_BOUNDARY(1)) binding(
  .clk(clk),.por_n(por_n),.launch_v(launch_v),.launch_pc(live_pc),.cp_job(live_job),.cp_gen(live_gen),.launch_token(live_token),.launch_pos(live_pos),
  .lease_v(lease_v),.lease_granted(grants[1]),.release_v(release_v),.release_r(releases[1]),.exec_done(exec_done),.exec_fault(1'b0),
  .retired_original_ops(retired),.shared_fault(shared_fault),.owned(qualified_owned),.pending(pending),.quiet(quiet),.selected(selected),.done(done),.fault(cp_fault),
  .selected_pc(held_pc),.held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos));
 ot_hbm_integrated_su_cp_association #(.ENABLE(1)) association(
  .clk(clk),.por_n(por_n),.raw_grant(grants[1]),.qualified_owned(qualified_owned),
  .exec_owned(exec_owned),.new_request_permit(new_permit),.fault(association_fault));
 wire off_owned,off_permit,off_fault;
 ot_hbm_integrated_su_cp_association baseline(
  .clk(clk),.por_n(por_n),.raw_grant(grants[1]),.qualified_owned(qualified_owned),
  .exec_owned(off_owned),.new_request_permit(off_permit),.fault(off_fault));
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) owner(
  .clk(clk),.por_n(por_n),.native_clients_drained(1'b1),.cdc_drained(1'b1),
  .observe_req(4'd0),.observe_rsp(4'd0),.observe_req_we(4'd0),.observe_rsp_we(4'd0),.observe_req_tag(64'd0),.observe_rsp_tag(64'd0),
  .return_offer(4'd0),.response_authorized(),.native_job(live_job),.native_gen(live_gen),.native_token(live_token),.native_pos(live_pos),.native_credit_empty(native_empty),
  .lease_v({1'b0,lease_v,1'b0}),.borrower_quiet({1'b1,quiet,1'b1}),
  .lease_job({32'd0,held_job,32'd0}),.lease_gen({4'd0,held_gen,4'd0}),.lease_token({17'd0,held_token,17'd0}),.lease_pos({20'd0,held_pos,20'd0}),.lease_granted(grants),
  .release_v({1'b0,release_v,1'b0}),.release_r(releases),.release_job({32'd0,held_job,32'd0}),.release_gen({4'd0,held_gen,4'd0}),.release_token({17'd0,held_token,17'd0}),.release_pos({20'd0,held_pos,20'd0}),
  .req_v({1'b0,request_v&&new_permit,2'd0}),.req_rdy(req_rdy),.req_we(4'd0),.req_addr({32'd0,32'd128,64'd0}),.req_wdata(1024'd0),.req_wstrb(128'd0),.req_tag({16'd0,16'h5321,32'd0}),
  .rsp_v(rsp_v),.rsp_rdy({1'b0,response_ready&&exec_owned,2'd0}),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_ready),.m_req_we(m_req_we),.m_req_addr(m_req_addr),.m_req_wdata(m_req_data),.m_req_wstrb(m_req_strb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),.m_rsp_we(1'b0),.m_rsp_tag(m_rsp_tag),.m_rsp_data(m_rsp_data),.idle(shared_idle),.fault(shared_fault));
 integer checks=0,cycle=0,source_accepts=0,provider_accepts=0,response_accepts=0,release_accepts=0,cpl_accepts=0;
 integer grant_cycle=-1,qualified_cycle=-1,admission_cycle=-1;
 task tick;begin @(posedge clk);#1;end endtask
 task drive;begin @(negedge clk);end endtask
 task ck(input reg ok,input string what);begin checks=checks+1;if(!ok)$fatal(1,"%s",what);end endtask
 always @(posedge clk)begin
  cycle=cycle+1;
  if(por_n)begin
   if(grants[1]&&grant_cycle<0)grant_cycle=cycle;
   if(qualified_owned&&qualified_cycle<0)qualified_cycle=cycle;
   if(exec_owned&&admission_cycle<0)admission_cycle=cycle;
   if(request_v&&new_permit&&req_rdy[2])source_accepts=source_accepts+1;
   if(m_req_v&&m_req_ready)begin
    if(m_req_addr!=128||m_req_tag!=16'h5321||m_req_we)$fatal(1,"accepted captured request changed");
    provider_accepts=provider_accepts+1;
   end
   if(rsp_v[2]&&response_ready&&exec_owned)begin
    if(rsp_tag[47:32]!=16'h5321||rsp_we[2]||rsp_data[767:512]!=256'h123456789abcdef)$fatal(1,"response identity/data changed");
    response_accepts=response_accepts+1;
   end
   if(release_v&&releases[1])release_accepts=release_accepts+1;
   if(cpl_v&&cpl_ready&&routes_drained)cpl_accepts=cpl_accepts+1;
  end
 end
 task reset;
 begin
  drive();por_n=0;cmd_we=0;db_v=0;cpl_ready=0;request_v=0;response_ready=0;m_req_ready=0;m_rsp_v=0;exec_done=0;retired=0;
  job_flip=0;gen_flip=0;token_flip=0;pos_flip=0;pc_flip=0;
  source_accepts=0;provider_accepts=0;response_accepts=0;release_accepts=0;cpl_accepts=0;
  grant_cycle=-1;qualified_cycle=-1;admission_cycle=-1;
  repeat(2)tick();drive();por_n=1;tick();
  drive();cmd_we=1;cmd_addr=0;cmd_data=64'h10001000c0000004;tick();
  drive();cmd_addr=1;cmd_data=64'h2000000000000000;tick();drive();cmd_we=0;
 end endtask
 task start;
 begin
  drive();db_v=1;tick();drive();db_v=0;
  wait(exec_owned);tick();
  ck(!shared_fault&&!association_fault&&qualified_owned,"real CP and shared lease join");
  ck(admission_cycle-qualified_cycle==0&&qualified_cycle-grant_cycle==1,"qualified admission one edge after rawgrant, no join stage");
  ck(off_owned==grants[1]&&off_permit&&!off_fault,"defaultOFF legacy passthrough");
 end endtask
 task flip(input integer field);
 begin
  case(field)0:job_flip=1;1:gen_flip=1;2:token_flip=1;3:pos_flip=1;4:pc_flip=1;endcase
  #1;ck(!qualified_owned&&!new_permit&&!release_v&&!done,"same-edge foreign veto denies new accepts");
  ck(exec_owned,"accepted execution remains held under live veto");
 end endtask
 task restore;
 begin job_flip=0;gen_flip=0;token_flip=0;pos_flip=0;pc_flip=0;end endtask
 task transact(input integer stage,input integer field);
 begin
  drive();request_v=1;
  do tick();while(source_accepts==0);
  drive();request_v=0;
  if(stage==0)flip(field);
  wait(m_req_v);drive();m_req_ready=1;tick();drive();m_req_ready=0;
  if(stage==1)flip(field);
  m_rsp_v=1;m_rsp_tag=16'h5321;m_rsp_data=256'h123456789abcdef;
  wait(m_rsp_rdy);tick();drive();m_rsp_v=0;
  wait(rsp_v[2]);drive();
  if(stage==2)flip(field);
  repeat(3)begin tick();ck(rsp_v[2]&&exec_owned,"held accepted response survives current veto/backpressure");end
  response_ready=1;tick();drive();response_ready=0;
  ck(source_accepts==1&&provider_accepts==1&&response_accepts==1,"accepted original debt consumed exactly once");
  ck(!shared_fault&&grants[1],"original borrower remains owned after response");
  if(stage>=0)begin
   request_v=1;repeat(4)begin tick();ck(!req_rdy[2]&&!m_req_v&&source_accepts==1&&exec_owned,"new requests denied while accepted association retained");end
   drive();request_v=0;restore();tick();
   ck(cp_fault&&exec_owned&&!release_v&&release_accepts==0,"transient foreign owner remains quarantine without dropping original debt");
   ck(cpl_accepts==0,"no faulted CPL accepted without drain");
  end
 end endtask
 task finish;
 begin
  drive();retired=4;exec_done=1;
  wait(!grants[1]);drive();exec_done=0;retired=0;
  wait(routes_drained);wait(cpl_v);drive();
  repeat(3)begin tick();ck(cpl_v&&!grants[1]&&!exec_owned,"CPL backpressure after actual grant and executor cleanup");end
  cpl_ready=1;tick();drive();cpl_ready=0;
  ck(release_accepts==1&&cpl_accepts==1,"one actual release and CPL");
  ck(!association.on.associated_q&&association.on.associated_n,"actual grant removal clears association");
 end endtask
 integer stage,field;
 initial begin
  reset();start();transact(-1,0);finish();
  // Next launch after real grant/response/CPL cleanup, without root reset.
  source_accepts=0;provider_accepts=0;response_accepts=0;release_accepts=0;cpl_accepts=0;
  grant_cycle=-1;qualified_cycle=-1;admission_cycle=-1;
  start();transact(-1,0);finish();
  for(stage=0;stage<3;stage=stage+1)for(field=0;field<5;field=field+1)begin reset();start();transact(stage,field);end
  $display("PASS_CP_PARENT_ASSOCIATION checks=%0d foreign_cases=15 healthy_transactions=2 warm_rearm=1 accepted_debt_drained=17 added_executor_start_edges=1",checks);$finish;
 end
 // Structural source cuts bound the test; this is not a host/job time limit.
 initial begin repeat(4000)tick();$fatal(1,"finite protocol test deadlocked");end
endmodule
