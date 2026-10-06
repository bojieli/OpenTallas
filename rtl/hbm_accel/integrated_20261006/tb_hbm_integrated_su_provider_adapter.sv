`timescale 1ns/1ps
// One deterministic configuration. Actual unchanged association is the golden
// for grant lifetime; literal selected-parent bus and frame wires are golden.
module tb_hbm_integrated_su_provider_adapter;
 reg clk_sm=0,por_n=0,raw_grant=0,qualified_owned=0;
 reg [11:0] qualified_owned_terms=0;
 reg exec_req_v=0,provider_req_r=0,provider_rsp_v=0,exec_rsp_r=0;
 reg [336:0] exec_req=0;reg [272:0] provider_rsp=0;
 reg [31:0] held_job=0,held_selected_pc=0;
 reg [3:0] held_gen=0,retired_original_ops=0;
 reg [16:0] held_token=0;reg [19:0] held_pos=0;
 reg exec_done=0,exec_fault=0;
 always #5 clk_sm=~clk_sm;
wire exec_owned; wire off_exec_owned;
wire new_request_permit; wire off_new_request_permit;
wire fault; wire off_fault;
wire exec_req_r; wire off_exec_req_r;
wire provider_req_v; wire off_provider_req_v;
wire [336:0] provider_req; wire [336:0] off_provider_req;
wire provider_rsp_r; wire off_provider_rsp_r;
wire exec_rsp_v; wire off_exec_rsp_v;
wire [272:0] exec_rsp; wire [272:0] off_exec_rsp;
wire [72:0] owner_frame; wire [72:0] off_owner_frame;
wire [31:0] selected_pc; wire [31:0] off_selected_pc;
wire caller_exec_done; wire off_caller_exec_done;
wire caller_exec_fault; wire off_caller_exec_fault;
wire [3:0] caller_retired_original_ops; wire [3:0] off_caller_retired_original_ops;
 ot_hbm_integrated_su_provider_adapter #(.ENABLE(1),.FAST_OWNER_FRONTIER(1)) dut(.*);
 ot_hbm_integrated_su_provider_adapter off_dut(.clk_sm(clk_sm),.por_n(por_n),.raw_grant(raw_grant),.qualified_owned(qualified_owned),.qualified_owned_terms(qualified_owned_terms),.exec_req_v(exec_req_v),.exec_req(exec_req),.provider_req_r(provider_req_r),.provider_rsp_v(provider_rsp_v),.provider_rsp(provider_rsp),.exec_rsp_r(exec_rsp_r),.held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos),.held_selected_pc(held_selected_pc),.exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired_original_ops),.exec_owned(off_exec_owned),.new_request_permit(off_new_request_permit),.fault(off_fault),.exec_req_r(off_exec_req_r),.provider_req_v(off_provider_req_v),.provider_req(off_provider_req),.provider_rsp_r(off_provider_rsp_r),.exec_rsp_v(off_exec_rsp_v),.exec_rsp(off_exec_rsp),.owner_frame(off_owner_frame),.selected_pc(off_selected_pc),.caller_exec_done(off_caller_exec_done),.caller_exec_fault(off_caller_exec_fault),.caller_retired_original_ops(off_caller_retired_original_ops));
 wire gold_owned,gold_permit,gold_fault;
 ot_hbm_integrated_su_cp_association #(.ENABLE(1),.FAST_OWNER_FRONTIER(1)) golden(
 .clk(clk_sm),.por_n(por_n),.raw_grant(raw_grant),.qualified_owned(qualified_owned),
 .qualified_owned_terms(qualified_owned_terms),.exec_owned(gold_owned),
 .new_request_permit(gold_permit),.fault(gold_fault));
 integer checks=0,request_bits=0,response_bits=0,frame_bits=0;
 task check;
 begin #1;
  checks=checks+1;
  if({exec_owned,new_request_permit,fault}!=={gold_owned,gold_permit,gold_fault})$fatal(1,"association mismatch");
  if({provider_req_v,exec_req_r,provider_req}!=={exec_req_v&&gold_permit,provider_req_r&&gold_permit,exec_req})$fatal(1,"request337 mapping/admission mismatch");
  if({exec_rsp_v,provider_rsp_r,exec_rsp}!=={provider_rsp_v,exec_rsp_r,provider_rsp})$fatal(1,"accepted response drain mismatch");
  if(owner_frame!=={held_pos,held_token,held_gen,held_job}||selected_pc!==held_selected_pc)$fatal(1,"full73 identity/PC mismatch");
  if({caller_exec_done,caller_exec_fault,caller_retired_original_ops}!=={exec_done,exec_fault,retired_original_ops})$fatal(1,"done/fault/retired passthrough mismatch");
  if({off_exec_owned,off_new_request_permit,off_fault,off_exec_req_r,off_provider_req_v,off_provider_req,off_provider_rsp_r,off_exec_rsp_v,off_exec_rsp,off_owner_frame,off_selected_pc,off_caller_exec_done,off_caller_exec_fault,off_caller_retired_original_ops}!==0)$fatal(1,"defaultOFF leaked bridge grant/debt");
 end endtask
 task clock_step;
 begin @(posedge clk_sm);check();@(negedge clk_sm);end endtask
 reg [72:0] frame;
 initial begin
  check();clock_step();por_n=1;check();
  raw_grant=1;qualified_owned=1;qualified_owned_terms=12'hfff;
  exec_req_v=1;provider_req_r=1;exec_rsp_r=1;clock_step();
  if(!exec_owned||!new_request_permit)$fatal(1,"actual association not admitted");
  // Walk every field, including TOKEN17/POS20 high bits. No truncation aliases.
  for(integer i=0;i<73;i=i+1)begin
   frame=73'd1<<i;{held_pos,held_token,held_gen,held_job}=frame;check();frame_bits=frame_bits+1;
  end
  held_job=32'hfeedca57;held_gen=4'hd;held_token=17'h1ffff;held_pos=20'hfffff;held_selected_pc=32'hc0000004;check();
  // Both read/write class, every payload/byteaddr/strobe/tag bit preserved.
  for(integer i=0;i<337;i=i+1)begin exec_req=337'd1<<i;check();request_bits=request_bits+1;end
  exec_req={1'b0,32'h12345678,256'habcdef,32'd0,16'hfedc};check();
  exec_req={1'b1,32'h87654321,256'h012345,32'hffffffff,16'h3456};provider_req_r=0;
  repeat(3)clock_step();provider_req_r=1;clock_step();
  provider_rsp_v=1;exec_rsp_r=0;
  for(integer i=0;i<273;i=i+1)begin provider_rsp=273'd1<<i;check();response_bits=response_bits+1;end
  // Live veto does not erase accepted executor association or response debt.
  qualified_owned=0;qualified_owned_terms=0;provider_rsp={16'hfedc,1'b0,256'h123456789abc};check();
  if(!exec_owned||new_request_permit||!exec_rsp_v)$fatal(1,"live veto erased accepted debt");
  repeat(3)clock_step();exec_rsp_r=1;clock_step();
  provider_rsp={16'h3456,1'b1,256'hfedcba987654};check();
  // Real grant loss is external. It stops new execution, not response wiring.
  raw_grant=0;check();if(exec_owned||new_request_permit)$fatal(1,"grant loss not respected");clock_step();
  exec_done=1;retired_original_ops=3;check();retired_original_ops=4;exec_fault=1;check();
  // Exercise existing complementary-rail fault with accepted raw grant; no new state.
  raw_grant=1;qualified_owned=1;qualified_owned_terms=12'hfff;clock_step();
  force dut.g_enabled.association.on.associated_n=1'b1;
  force golden.on.associated_n=1'b1;
  check();if(!fault||exec_owned||new_request_permit||!exec_rsp_v)$fatal(1,"rail fault/debt contract missing");
  release dut.g_enabled.association.on.associated_n;release golden.on.associated_n;
  por_n=0;clock_step();por_n=1;raw_grant=0;qualified_owned=0;qualified_owned_terms=0;clock_step();
  if(fault||exec_owned||new_request_permit)$fatal(1,"cold recovery did not clear association");
  $display("PASS SU provider adapter checks=%0d request_bits=%0d response_bits=%0d owner_bits=%0d",checks,request_bits,response_bits,frame_bits);
  $finish;
 end
endmodule
