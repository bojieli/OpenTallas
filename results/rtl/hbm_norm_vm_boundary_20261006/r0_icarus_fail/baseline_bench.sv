`timescale 1ns/1ps
// Connection diagnostic, not a repeated numerical gate. The selected owner
// norm is b2523883e (LA6X/FREG); no arithmetic output is used as an oracle.
// Test-only defparams select that child because the production VM/stream ABI
// currently does not forward its cuts. Do not treat this as installed hardware.
// The direct done->finish connection is deliberately tested with delayed
// consumer drain: a one-cycle child completion cannot satisfy a held handshake.
module tb_selected_norm_vm_drain;
 localparam N=32,D=64,AW=8;
 localparam [72:0] FRAME={20'hfffff,17'h1a321,4'h9,32'h9234abcd};
 reg clk=0; always #0.5 clk=~clk;
 reg por_n=0,enroll_v=0,consumer_drained=1,complete_r=0,warm_req=0;
 reg [72:0] owner_frame=FRAME;
 wire enroll_r,start_v,start_r,finish_r,complete_v,warm_ack,retained,issued,join_fault;
 wire [72:0] held_frame;
 wire vm_busy,vm_done,vm_fault; wire [31:0] completion_id;
 wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re;
 wire [8*N-1:0] rd_src; reg [4*N*32-1:0] rd_q=0;
 wire [N-1:0] vm_we; wire [N*AW-1:0] vm_waddr;
 wire [N*32-1:0] vm_wdata;
 reg [31:0] mem[0:255]; integer l,writes,done_edges;
 // Real one-cycle VM ABI, identical read/landing contract to the component.
 // These positive finite operands exercise flow only; leaf exactness is reused.
 always @(posedge clk) begin
  for(integer k=0;k<4*N;k=k+1)
   rd_q[k*32+:32] <= rd_re[k] ? mem[rd_addr[k*AW+:AW]] : 32'd0;
  for(integer k=0;k<N;k=k+1) if(vm_we[k]) begin
   mem[vm_waddr[k*AW+:AW]] <= vm_wdata[k*32+:32];
   writes <= writes+N;
  end
  if(vm_done) done_edges <= done_edges+1;
 end
 ot_hbm_integrated_stage_join #(.ENABLE(1)) seat(
  .clk(clk),.por_n(por_n),.enroll_v(enroll_v),.enroll_r(enroll_r),
  .enroll_frame(FRAME),.enroll_pc(32'd17),.enroll_op(32'd1),
  .enroll_source(16'h5f07),.enroll_expert(9'd0),.enroll_matrix(1'b0),
  .enroll_row(12'd0),.enroll_count(9'd2),
  .owner_valid(1'b1),.owner_frame(owner_frame),.source_permit(1'b1),
  .start_v(start_v),.start_r(start_r),.finish_v(vm_done),.finish_r(finish_r),
  .producer_drained(!vm_busy||vm_done),.consumer_drained(consumer_drained),
  .complete_v(complete_v),.complete_r(complete_r),.warm_req(warm_req),
  .warm_ack(warm_ack),.retained(retained),.issued(issued),
  .ce(),.due(),.fault(join_fault),.held_frame(held_frame),
  .held_pc(),.held_op(),.held_source(),.held_expert(),.held_matrix(),
  .held_row(),.held_count());
 ot_hbm_accel_su_fused_vm #(.ENABLE(1),.KIND(1),.N(N),.D(D),.AW(AW),
  .PUBLISH_QUANT(0)) vm(
  .clk(clk),.rst_n(por_n),.cmd_valid(start_v),.source_ready(1'b1),
  .landing_reserved(1'b1),.cmd_ready(start_r),.busy(vm_busy),.done(vm_done),
  .fault(vm_fault),.job_id(held_frame[31:0]),
  .xbase(8'd0),.ubase(8'd0),.wbase(8'd0),.ybase(8'd128),.gain_base(8'd64),
  .comb(512'd0),.post_pre(128'd0),.n_f(32'h42800000),.eps(32'h3f800000),
  .lim(32'h41200000),.cos_t(32'd0),.sin_t(32'd0),
  .rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
  .q_valid(),.q_index(),.q_codes(),.q_exp(),.q_bf16(),
  .completion_id(completion_id),.reserve_events());
 defparam vm.u_engine.LM=5;
 defparam vm.u_engine.LA=6;
 defparam vm.u_engine.g_norm.u_engine.RXS=1;
 defparam vm.u_engine.g_norm.u_engine.SXC=1;
 defparam vm.u_engine.g_norm.u_engine.FREG=1;
 task tick; begin @(posedge clk); #0.01; end endtask
 task root_reset; begin
  @(negedge clk);por_n=0;enroll_v=0;complete_r=0;warm_req=0;
  consumer_drained=1;owner_frame=FRAME;writes=0;done_edges=0;
  for(l=0;l<256;l=l+1)mem[l]=32'h3f800000;
  tick();@(negedge clk);por_n=1;tick();
 end endtask
 task enroll; begin
  @(negedge clk);if(!enroll_r)$fatal(1,"descriptor seat not ready");enroll_v=1;
  tick();@(negedge clk);enroll_v=0;
  if(held_frame!==FRAME)$fatal(1,"full73 descriptor changed");
 end endtask
 // Functional pipeline bound from this selected child's stages plus the VM
 // gain/input handshakes, not a build/runtime resource deadline.
 localparam PIPE_BOUND=2*(D/N)+5+7*6+$clog2(N/8)*6+$clog2(D/N)*6+
                       9+8+6+1+3*(3*5+6)+9+2*6+1+7+8+32;
 integer cycle;
 initial begin
  root_reset();enroll();
  cycle=0;
  while(!vm_done && cycle<PIPE_BOUND)begin
   tick();cycle=cycle+1;
   if(join_fault||vm_fault)$fatal(1,"fault before completion");
  end
  if(!vm_done||completion_id!==FRAME[31:0]||writes!=D)
   $fatal(1,"selected native VM flow did not complete: writes=%0d",writes);
  tick();if(!complete_v)$fatal(1,"unblocked direct finish failed");
  $display("PASS_SELECTED_NORM_VM_DIRECT frame=73 writes=%0d cycles=%0d",writes,cycle);
  // A meaningful changed connection negative: accept with a real reserved
  // landing, but hold consumer publication ACK. Warm must preserve all debt.
  root_reset();enroll();@(negedge clk);consumer_drained=0;warm_req=1;
  cycle=0;
  while(!vm_done && cycle<PIPE_BOUND)begin
   tick();cycle=cycle+1;
   if(join_fault||vm_fault||complete_v||warm_ack||!retained)
    $fatal(1,"held consumer/warm debt lost");
  end
  if(!vm_done||finish_r||writes!=D)$fatal(1,"held publication setup failed");
  repeat(3)tick();
  @(negedge clk);consumer_drained=1;
  repeat(3)tick();
  if(!complete_v && issued && retained && done_edges==1)begin
   $display("FAIL_DIRECT_DONE_BINDING frame=73 writes=%0d child_done_pulses=%0d retained=1 issued=1 warm_ack=0: missing protected held finish handshake",writes,done_edges);
   $finish(1);
  end
  $fatal(1,"expected direct completion debt diagnostic was not reproduced");
 end
endmodule
