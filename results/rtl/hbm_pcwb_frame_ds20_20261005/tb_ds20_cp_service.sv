`timescale 1ps/1fs
// Minimum newly COMPOSED mechanism: actual CP + c6 join control + DS writer,
// native ownerframe + one actual CMD1 PC/CA + PHY queue/visibility.
// The kernel produces one row fixture, not model arithmetic or a full token.
module tb_ds20_cp_service;
 reg service_clk=0,core_clk=0,por_n=0;
 always #512 service_clk=~service_clk;
 always #416.6665 core_clk=~core_clk;
 reg cmd_we=0,cmd_addr=0;reg [63:0] cmd_data=0;
 reg db_v=0;reg [31:0] db_job=32'h12345678;reg [3:0] db_gen=4'hf;reg [19:0] db_pos=0;
 wire cp_ready,db_ready,cp_done;wire [31:0] cp_job;wire [3:0] cp_gen,cp_status;wire [19:0] cp_pos;
 reg sm_done=0;wire launch;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(1),.NCMD(2)) cp(
  .clk(core_clk),.rst_n(por_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
  .db_v(db_v&&db_ready),.db_rdy(cp_ready),.db_job(db_job),.db_generation(db_gen),.db_pos(db_pos),.db_token(17'd7),
  .cpl_position(cp_pos),.cpl_job(cp_job),.cpl_generation(cp_gen),.launch_v(launch),.launch_pc(),.launch_token(),.launch_pos(),
  .sm_done(sm_done),.sm_fault(1'b0),.res_v(1'b0),.res_data(32'b0),.cpl_v(cp_done),.cpl_rdy(1'b1),
  .cpl_token(),.cpl_status(cp_status),.cpl_cycles(),.st_kernels(),.st_busy());
 wire own_v,own_r,owned,released,source_window,assoc_fault;
 wire [31:0] job,held_job;wire [3:0] gen,held_gen;wire [19:0] position,held_pos;
 wire [6:0] rank,held_rank;wire [1:0] stack,held_stack;
 reg row_v=0;wire row_r;wire [19:0] row_pos=cp_pos;wire [6:0] row_die=3;
 ot_ds_hbm_pcwb_owner_join #(.ENABLE(1),.DIE(3),.STACK(0)) join_owner(
  .clk_sm(core_clk),.rst_sm_n(por_n),.service_clk(service_clk),.por_n(por_n),
  .db_v(db_v&&db_ready),.db_rdy(cp_ready),.db_rdy_eff(db_ready),.issuer_done(cp_done),
  .cpl_job(cp_job),.cpl_generation(cp_gen),.cpl_position(cp_pos),
  .owner_v(own_v),.owner_r(own_r),.owner_held(owned),.owner_fenced(released),
  .o_job(job),.o_gen(gen),.o_pos(position),.o_rank(rank),.o_stack(stack),
  .row_acc(row_v&&row_r),.row_die(row_die),.row_pos(row_pos),.assoc_fault(assoc_fault),.source_window_owned(source_window));
 wire frame_fault,row_match,fenced,wr_drained,wq_empty,writer_fence,pc_busy;
 wire [6:0] queued;wire [3:0] flight,visible_held;
 wire all_drained=wr_drained&&wq_empty&&queued==0&&writer_fence&&!pc_busy;
 wire active=source_window&&owned&&!frame_fault&&!assoc_fault;
 ot_hbm_pcwb_owner_frame_ds20 #(.ENABLE(1),.STACK(0)) frame(
  .service_clk(service_clk),.por_n(por_n),.owner_v(own_v),.owner_r(own_r),
  .owner_job(job),.owner_gen(gen),.owner_pos(position),.rank(rank),.stack(stack),
  .writes_fenced(writer_fence&&wr_drained&&wq_empty&&queued==0),.all_drained(all_drained),
  .external_fault(adapter_fault||pc_fault||ca_fault),.bad_event(1'b0),
  .row_attempt(row_v&&active),.row_pos(row_pos),.row_die(row_die),.row_association_matches(row_match),
  .owner_held(owned),.held_job(held_job),.held_gen(held_gen),.held_pos(held_pos),.held_rank(held_rank),.held_stack(held_stack),
  .fenced(fenced),.owner_released(released),.fault(frame_fault));
 wire writer_row_r,writer_v,writer_ready;wire [4:0] wb_pc,wb_bank,wb_col;wire [18:0] wb_row;wire [255:0] wb_data;
 wire wr_receipt_v;wire [135:0] wr_receipt;wire [15:0] issued,acked;
 assign row_r=writer_row_r&&active&&row_match;
 ot_hbm_accel_dskv_wb #(.ENABLE(1),.STACK(0)) writer(
  .clk(service_clk),.rst_n(por_n),.die(row_die),.pos(row_pos),.row_v(row_v&&active&&row_match),.row_r(writer_row_r),
  .row_kind(2'b0),.row_slot(6'b0),.row_r2(1'b0),.row_data({544{8'ha5}}),
  .sh_v(1'b0),.sh_slot(3'b0),.sh_data(4352'b0),
  .wq_v(writer_v),.wq_r(writer_ready),.wq_pc(wb_pc),.wq_bank(wb_bank),.wq_row(wb_row),.wq_col(wb_col),.wq_data(wb_data),
  .ack_n((wr_receipt_v&&active)?6'd1:6'd0),.issued(issued),.acked(acked),.fence_ok(writer_fence));
 wire adapter_ready,wq_v,wq_r,cv,cwe,phy_v,phy_we,adapter_fault,pc_fault,ca_fault;
 wire [4:0] cb,cc,pb,pc;wire [18:0] cr,pr;wire [255:0] cd,pd;
 wire [135:0] phy_receipt;reg phy_r=0,visibility_enable=0;
 reg [135:0] receipt_fifo[0:31];reg [255:0] memory[0:127];integer accepted=0,returned=0;
 wire visible_v=visibility_enable&&returned<accepted;wire visible_r;
 assign writer_ready=active&&wb_pc==0&&adapter_ready;
 ot_hbm_pcwb_prepaid_column_frame_ds20 #(.ENABLE(1),.PC(0)) adapter(
  .service_clk(service_clk),.por_n(por_n),.context_valid(active),.owner_job(held_job),.owner_gen(held_gen),.owner_pos(held_pos),.owner_rank(held_rank),.owner_stack(held_stack),
  .wr_v(writer_v&&wb_pc==0),.wr_r(adapter_ready),.wr_bank(wb_bank),.wr_row(wb_row),.wr_col(wb_col),.wr_data(wb_data),
  .wq_v(wq_v),.wq_r(wq_r),.col_v(cv),.col_we(cwe),.col_bank(cb),.col_row(cr),.col_col(cc),.col_data(cd),
  .phy_col_v(phy_v),.phy_col_r(phy_r),.phy_we(phy_we),.phy_bank(pb),.phy_row(pr),.phy_col(pc),.phy_data(pd),.phy_receipt(phy_receipt),
  .visible_v(visible_v),.visible_r(visible_r),.visible_receipt(receipt_fifo[returned]),
  .wr_visible_v(wr_receipt_v),.wr_visible_r(active),.wr_visible_receipt(wr_receipt),
  .queued(queued),.inflight(flight),.visible_not_returned(visible_held),.all_writes_drained(wr_drained),.fault(adapter_fault));
 wire rv,rg;wire [2:0] ro;wire [4:0] rb;wire [18:0] rr;wire [31:0] grants;
 ot_hbm_accel_stream_pc_wb_command_match #(.ENABLE(1),.WB_EN(1),.WA_LATE(1),.DIGEST_CUT(1),.CMD_MATCH_CUT(1),.PC(0),.REF_MODE(1),.CRED(64),.WQ(8)) controller(
  .clk(service_clk),.rst_n(por_n),.desc_v(1'b0),.desc_r(),.desc_row(19'b0),.desc_n(11'b0),.go(1'b0),.next_posted(1'b0),.notice(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(rg),.row_op(ro),.row_bank(rb),.row_row(rr),
  .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(3'b0),.busy(pc_busy),.ref_fault(pc_fault),
  .wq_v(wq_v),.wq_bank(wb_bank),.wq_row(wb_row),.wq_col(wb_col),.wq_data(wb_data),.wq_r(wq_r),
  .col_we(cwe),.col_wdata(cd),.col_row(cr),.wr_ack(),.wq_empty(wq_empty));
 ot_hbm_pcwb_ca_slots #(.ENABLE(1)) ca(
  .service_clk(service_clk),.por_n(por_n),.run_enable(1'b1),.row_req({31'b0,rv}),.row_op({93'b0,ro}),.row_bank({155'b0,rb}),.row_row({589'b0,rr}),
  .ca_ready(16'hffff),.row_grant(grants),.ca_valid(),.ca_pc_lsb(),.ca_op(),.ca_bank(),.ca_row(),.fault(ca_fault));
 assign rg=grants[0];
 always @(posedge service_clk)if(por_n)begin
  if(frame_fault||assoc_fault||adapter_fault||pc_fault||ca_fault)$fatal(1,"composed source fault");
  if(phy_v&&phy_r)begin
   if(!phy_we||pd!={32{8'ha5}}||phy_receipt[135:104]!=32'h12345678||phy_receipt[103:100]!=15||phy_receipt[99:80]!=0||phy_receipt[79:73]!=3||phy_receipt[72:71]!=0)$fatal(1,"PHY actual frame/payload mismatch");
   memory[pb*32+pc]=pd;receipt_fifo[accepted]=phy_receipt;accepted=accepted+1;
  end
  if(visible_v&&visible_r)begin
   if(memory[receipt_fifo[returned][28:24]*32+receipt_fifo[returned][4:0]]!={32{8'ha5}})$fatal(1,"visibility before backing write");
   returned=returned+1;
  end
 end
 task tick;begin @(posedge service_clk);#1;end endtask
 initial begin
  #1;repeat(2)tick();@(negedge service_clk);por_n=1;
  @(negedge core_clk);cmd_we=1;cmd_addr=0;cmd_data=(64'h1<<60)|(64'h1<<44)|64'd99;
  @(negedge core_clk);cmd_addr=1;cmd_data=64'h2<<60;
  @(negedge core_clk);cmd_we=0;db_v=1;
  @(posedge core_clk);#1;if(db_ready)$fatal(1,"adjacent doorbell accept gap");
  @(negedge core_clk);db_v=0;
  for(integer n=0;n<40&&!source_window;n=n+1)tick();
  if(!source_window||held_job!=32'h12345678||held_gen!=15||held_pos!=0)$fatal(1,"CP to actual parent binding failed");
  tick();if(!released||cp_done||db_ready)$fatal(1,"early empty fence incorrectly means CPdone");
  @(negedge service_clk);row_v=1;#1;if(!row_r)$fatal(1,"owned DS row refused");tick();@(negedge service_clk);row_v=0;
  @(negedge core_clk);sm_done=1;
  for(integer n=0;n<30&&!cp_ready;n=n+1)tick();
  if(!cp_ready||db_ready||acked!=0||issued==0)$fatal(1,"CPdone bypassed actual WR/visibility debt");
  @(negedge core_clk);db_job=32'h87654321;db_gen=0;db_pos=1;db_v=1;sm_done=0;
  repeat(5)begin tick();if(db_ready||released)$fatal(1,"pending next step admitted early");end
  @(negedge service_clk);phy_r=1;visibility_enable=1;
  for(integer n=0;n<2000&&acked!=17;n=n+1)tick();
  if(accepted!=17||returned!=17||issued!=17||acked!=17||!writer_fence)$fatal(1,"actual17sector row failed to drain");
  // Next actual accepted CP step is allowed only after all source debt drains.
  for(integer n=0;n<40&&cp_job!=32'h87654321;n=n+1)tick();
  if(cp_job!=32'h87654321)$fatal(1,"next source step never accepted");
  @(negedge service_clk);row_v=1;
  while(!source_window)begin #1;if(row_r)$fatal(1,"old heldframe accepted row across CDC gap");tick();end
  @(negedge service_clk);row_v=0;db_v=0;
  if(held_job!=32'h87654321||held_gen!=0||held_pos!=1)$fatal(1,"new held tuple incorrect");
  $display("PASS_DS20_COMPOSED_CP_SERVICE 17actualDSsectors; CPdone != PHYvisibility; all debt before nextaccept; actualboundwindow; exactfullwidthidentity");$finish;
 end
endmodule
