`timescale 1ns/1ps
// Minimum enclosing-control integration. Numerical c12 work uses the separate
// real-memory stage bench; this bench makes no numerical or token-PASS claim.
module tb_hbm_integrated_stage_join;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=0,enroll_v=0,start_r=0,finish_v=0,complete_r=0,warm_req=0;
 reg producer_drained=1,consumer_drained=1,owner_valid=1;
 localparam [72:0] FRAME={20'hfffff,17'h1a321,4'h9,32'h9234abcd};
 reg [72:0] owner_frame=FRAME;
 wire enroll_r,start_v,finish_r,complete_v,warm_ack,retained,issued,ce,due,fault;
 wire [72:0] held_frame;wire [31:0] held_pc,held_op;
 wire [15:0] held_source;wire [8:0] held_expert,held_count;
 wire held_matrix;wire [11:0] held_row;
 ot_hbm_integrated_stage_join #(.ENABLE(1)) dut(
  .clk(clk),.por_n(por_n),.enroll_v(enroll_v),.enroll_r(enroll_r),
  .enroll_frame(FRAME),.enroll_pc(32'd173),.enroll_op(32'd1),.enroll_source(16'h5f07),
  .enroll_expert(9'd65),.enroll_matrix(1'b1),.enroll_row(12'd2292),.enroll_count(9'd12),
  .owner_valid(owner_valid),.owner_frame(owner_frame),.source_permit(1'b1),
  .start_v(start_v),.start_r(start_r),.finish_v(finish_v),.finish_r(finish_r),
  .producer_drained(producer_drained),.consumer_drained(consumer_drained),
  .complete_v(complete_v),.complete_r(complete_r),.warm_req(warm_req),.warm_ack(warm_ack),
  .retained(retained),.issued(issued),.ce(ce),.due(due),.fault(fault),
  .held_frame(held_frame),.held_pc(held_pc),.held_op(held_op),.held_source(held_source),
  .held_expert(held_expert),.held_matrix(held_matrix),.held_row(held_row),.held_count(held_count));
 task tick;begin @(posedge clk);#0.01;end endtask
 task root_reset;begin
  @(negedge clk);por_n=0;enroll_v=0;start_r=0;finish_v=0;complete_r=0;warm_req=0;
  producer_drained=1;consumer_drained=1;owner_valid=1;owner_frame=FRAME;
  tick();@(negedge clk);por_n=1;tick();
 end endtask
 task enroll;begin
  @(negedge clk);if(!enroll_r)$fatal(1,"seat unavailable");enroll_v=1;
  tick();@(negedge clk);enroll_v=0;
  if(!start_v||held_frame!==FRAME||held_pc!==173||held_op!==1||held_source!==16'h5f07||
     held_expert!==65||!held_matrix||held_row!==2292||held_count!==12)
   $fatal(1,"held numerical descriptor differs");
 end endtask
 integer k;
 initial begin
  root_reset();enroll();
  repeat(5)begin tick();if(!retained||!start_v||issued||enroll_r)$fatal(1,"start backpressure lost descriptor");end
  // Genuine accepted start; only actual drain enables a completion.
  @(negedge clk);start_r=1;tick();@(negedge clk);start_r=0;producer_drained=0;consumer_drained=0;finish_v=1;warm_req=1;
  repeat(3)begin tick();if(!issued||finish_r||complete_v||warm_ack||enroll_r)$fatal(1,"warm erased active debt");end
  @(negedge clk);producer_drained=1;tick();if(finish_r)$fatal(1,"consumer debt ignored");
  @(negedge clk);consumer_drained=1;tick();@(negedge clk);finish_v=0;
  repeat(4)begin tick();if(!complete_v||held_frame!==FRAME||warm_ack)$fatal(1,"held completion lost owner");end
  @(negedge clk);complete_r=1;tick();@(negedge clk);complete_r=0;
  if(!warm_ack||retained||enroll_r)$fatal(1,"warm quarantine handshake");
  @(negedge clk);warm_req=0;tick();if(!enroll_r)$fatal(1,"warm rearm");
  // Correction suppresses authority for the scrub edge, then rechecks code.
  enroll();@(negedge clk);dut.g_on.descriptor.code[0][0]=~dut.g_on.descriptor.code[0][0];#0.01;
  if(!ce||start_v||enroll_r||finish_r||complete_v)$fatal(1,"CE admitted work");
  tick();if(ce||!start_v||held_frame!==FRAME)$fatal(1,"CE scrub changed identity");
  // Full position bit 19 and token bit 16 are checked, never truncated.
  @(negedge clk);owner_frame=FRAME^(73'd1<<72);#0.01;
  if(!fault||start_v||complete_v)$fatal(1,"high position owner mismatch accepted");
  tick();@(negedge clk);owner_frame=FRAME;tick();if(!fault||start_v)$fatal(1,"fault not retained");
  root_reset();enroll();@(negedge clk);owner_frame=FRAME^(73'd1<<52);#0.01;
  if(!fault||start_v)$fatal(1,"high token mismatch accepted");
  root_reset();enroll();@(negedge clk);
  dut.g_on.descriptor.code[1][0]=~dut.g_on.descriptor.code[1][0];
  dut.g_on.descriptor.code[1][1]=~dut.g_on.descriptor.code[1][1];#0.01;
  if(!due||!fault||start_v||enroll_r||complete_v||warm_ack)$fatal(1,"DUE admitted work");
  warm_req=1;repeat(3)begin tick();if(!due||!retained||warm_ack)$fatal(1,"warm cleared DUE debt");end
  $display("PASS_INTEGRATED_STAGE_JOIN bits=216 frame=73 start_hold=5 completion_hold=4 CE=1 DUE=1 warm=1 high_position=1 high_token=1");
  $finish;
 end
endmodule
