`timescale 1ns/1ps
// Connection diagnostic, not a repeated numerical gate. The selected owner
// norm is b2523883e (LA6X/FREG); no arithmetic output is used as an oracle.
// Disjoint production wrappers actually forward the selected cuts. The
// protected parent accepts held finish only after the consumer drains.
// This component gate does not qualify physical capture or installed ALLON.
module tb_selected_norm_vm_drain;
 localparam N=32,D=64,AW=8;
 localparam [72:0] FRAME={20'hfffff,17'h1a321,4'h9,32'h9234abcd};
 reg clk=0; always #0.416666667 clk=~clk;
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
 ot_hbm_integrated_norm_vm #(.ENABLE(1),.KIND(1),.N(N),.D(D),.AW(AW),
  .PUBLISH_QUANT(0),.LM(5),.LA(6),.RXS(1),.SXC(1),.FREG(1),
  .HOLD_COMPLETION(1)) vm(
  .clk(clk),.rst_n(por_n),.completion_ready(finish_r),.cmd_valid(start_v),.source_ready(1'b1),
  .landing_reserved(1'b1),.cmd_ready(start_r),.busy(vm_busy),.done(vm_done),
  .fault(vm_fault),.job_id(held_frame[31:0]),
  .xbase(8'd0),.ubase(8'd0),.wbase(8'd0),.ybase(8'd128),.gain_base(8'd64),
  .comb(512'd0),.post_pre(128'd0),.n_f(32'h42800000),.eps(32'h3f800000),
  .lim(32'h41200000),.cos_t(32'd0),.sin_t(32'd0),
  .rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
  .q_valid(),.q_index(),.q_codes(),.q_exp(),.q_bf16(),
  .completion_id(completion_id),.reserve_events());
 wire off_ready,off_busy,off_done,off_fault;wire [N-1:0] off_we;
 ot_hbm_integrated_norm_vm #(.N(N),.D(D),.AW(AW),.PUBLISH_QUANT(0)) off_vm(
  .clk(clk),.rst_n(por_n),.cmd_valid(1'b1),.source_ready(1'b1),.landing_reserved(1'b1),
  .completion_ready(1'b0),.cmd_ready(off_ready),.busy(off_busy),.done(off_done),.fault(off_fault),
  .job_id(32'd0),.xbase(8'd0),.ubase(8'd0),.wbase(8'd0),.ybase(8'd0),.gain_base(8'd0),
  .comb(512'd0),.post_pre(128'd0),.n_f(32'd0),.eps(32'd0),.lim(32'd0),
  .cos_t(32'd0),.sin_t(32'd0),.rd_q({4*N*32{1'b0}}),.vm_we(off_we));
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
  root_reset();
  if(off_vm.RXS!=0||off_vm.SXC!=0||off_vm.FREG!=0||off_vm.HOLD_COMPLETION!=0||
     off_ready||off_busy||off_done||off_fault||(|off_we))$fatal(1,"default OFF/cuts not inert");
  enroll();
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
  repeat(3)begin
   tick();
   if(!vm_done||!vm_busy||complete_v||warm_ack||completion_id!==FRAME[31:0]||held_frame!==FRAME)
    $fatal(1,"held finish lost completion/identity");
  end
  @(negedge clk);consumer_drained=1;
  repeat(3)tick();
  if(!complete_v||!retained||warm_ack||vm_busy||vm_done)
   $fatal(1,"real consumer drain failed held finish acceptance");
  repeat(3)begin tick();if(!complete_v||held_frame!==FRAME||warm_ack)$fatal(1,"caller backpressure lost full73 completion");end
  @(negedge clk);complete_r=1;tick();@(negedge clk);complete_r=0;
  if(!warm_ack||retained)$fatal(1,"warm completed debt did not quarantine");
  root_reset();enroll();owner_frame=FRAME^(73'd1<<52);#0.01;
  if(!join_fault||start_v)$fatal(1,"foreign high TOKEN17 started child");
  repeat(3)begin tick();if(vm_busy||vm_done||(|vm_we))$fatal(1,"foreign owner produced output");end
  if(vm.RXS!=1||vm.SXC!=1||vm.FREG!=1||vm.u_engine.RXS!=1||vm.u_engine.SXC!=1||vm.u_engine.FREG!=1||vm.u_engine.g_norm.u_engine.RXS!=1||vm.u_engine.g_norm.u_engine.SXC!=1||vm.u_engine.g_norm.u_engine.FREG!=1)
   $fatal(1,"selected cuts not actually forwarded");
  $display("PASS_SELECTED_NORM_VM_DRAIN frame=73 RXS=1 SXC=1 FREG=1 held_finish=3 caller_hold=3 warm=1 foreign_token=1 no_numerical_requalification=1");
  $finish;
 end
endmodule
