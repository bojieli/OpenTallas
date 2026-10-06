`timescale 1ps/1fs
module tb_hbm_pcwb_p2_return_bind;
 reg clk=0,por_n=0;always #512 clk=~clk;
 reg bind_v=0;reg[72:0] frame=0;
 reg[31:0] issue_v=0,return_v=0;reg[95:0] freed=0;
 wire[31:0] ip,rp,empty;wire[511:0] nextord,retord;wire[2335:0] retframe;
 wire drained,fault;integer i,j;
 ot_hbm_pcwb_p2_return_bind #(.ENABLE(1)) dut(
  .clk(clk),.por_n(por_n),.bind_v(bind_v),.bind_frame(frame),
  .issue_v(issue_v),.return_v(return_v),.freed(freed),
  .issue_permit(ip),.return_permit(rp),.next_ordinal(nextord),.return_ordinal(retord),
  .return_frame(retframe),.empty(empty),.drained(drained),.fault(fault));
 task edge_tick;begin @(posedge clk);#1;end endtask
 task step;begin @(negedge clk);#1;end endtask
 task reset;
 begin step();por_n=0;bind_v=0;issue_v=0;return_v=0;freed=0;
 repeat(2)edge_tick();step();por_n=1;edge_tick();end endtask
 task enroll_owner(input[72:0] f);
 begin step();frame=f;bind_v=1;edge_tick();step();bind_v=0;edge_tick();end endtask
 initial begin
 reset();if(!drained||fault||ip!=0)$fatal(1,"COLD_OWNER_PERMISSION");
 enroll_owner((73'b1<<72)|(73'b1<<52)|73'h12345678);
 for(i=0;i<32;i++)begin
  if(ip!==32'hffffffff)$fatal(1,"EARLY_QUOTA_STOP");
  for(j=0;j<32;j++)if(nextord[j*16+:16]!==16'(i))$fatal(1,"ISSUE_ORDINAL");
  step();issue_v='1;edge_tick();step();issue_v=0;edge_tick();
 end
 if(ip!=0||drained||fault)$fatal(1,"CRED32_RESERVATION");
 for(i=0;i<32;i++)begin
  if(rp!==32'hffffffff)$fatal(1,"ORDERED_DEBT_PERMISSION");
  for(j=0;j<32;j++)if(retord[j*16+:16]!==16'(i)||retframe[j*73+:73]!==frame)$fatal(1,"RETURN_OWNER_ORDINAL");
  step();return_v='1;edge_tick();step();return_v=0;edge_tick();
 end
 if(ip!=0||rp!=0||drained||fault)$fatal(1,"RETURN_IS_NOT_LANDING_CREDIT");
 for(i=0;i<32;i++)begin
  step();for(j=0;j<32;j++)freed[j*3+:3]=1;edge_tick();step();freed=0;edge_tick();
 end
 if(!drained||fault||ip!==32'hffffffff)$fatal(1,"ACTUAL_FREED_RECOVERS_SEAT");
 enroll_owner((73'b1<<71)|(73'b1<<51)|73'h87654321);
 for(j=0;j<32;j++)if(nextord[j*16+:16]!==16'd32||retframe[j*73+:73]!==frame)$fatal(1,"OWNER_REBIND_ORDINAL_RETENTION");
 step();dut.on.pc[0].state.code[0]^=72'h4;#1;
 if(ip[0]||rp[0]||drained||fault)$fatal(1,"CE_PERMISSION_OR_STICKY");
 edge_tick();edge_tick();if(!ip[0]||fault)$fatal(1,"CE_SCRUB_RESUME");
 // Actual coded owner UE stops every read without releasing ownership.
 step();dut.on.frame.code[0]^=72'd3;#1;
 if(!fault||ip!=0||rp!=0||drained)$fatal(1,"OWNER_UE_PERMISSION");
 reset();enroll_owner(73'habc);
 step();freed[2:0]=1;edge_tick();step();freed=0;edge_tick();
 if(!fault)$fatal(1,"FALSE_FREED_ACCEPTED");
 reset();enroll_owner(73'hdef);
 step();issue_v[0]=1;edge_tick();step();issue_v=0;bind_v=1;frame=73'hbad;edge_tick();step();bind_v=0;
 if(!fault||drained)$fatal(1,"REBIND_WITH_OWED_READ");
 $display("P2_SERVICE_RETURN_BIND_PASS PCs32 READaccept1024 orderedreturn1024 actualfreed1024 full73 CE UE falsecredit rebinddebt");$finish;
 end
endmodule
