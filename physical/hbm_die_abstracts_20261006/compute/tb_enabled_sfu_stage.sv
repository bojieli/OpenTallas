`timescale 1ps/1fs
// Minimum actual stage/held framing mechanism with real full-width SFU64.
// Verilator cuts the identical arithmetic child; no flattened array/die build.
module tb_enabled_sfu_stage;
 import ot_gpu_w6_secded_pkg::*;
 localparam IW=2083,OW=2081,CASES=10,MAXWAIT=2+3+2+276+32;
 reg clk=0,por_n=0;always #416.666667 clk=~clk;
 reg warm_req=0,enroll_v=0,owner_valid=1,source_permit=1;
 reg producer_drained=1,consumer_drained=1;
 reg rx_v=0,rx_first=0,rx_last=0,tx_r=0,complete_r=0;
 reg [1023:0] rx_d=0;
 reg [72:0] frame=0,rx_owner=0,complete_owner=0;
 wire warm_ack,enroll_r,rx_r,tx_v,tx_last,complete_v;
 wire retained,issued,ce,due,fault;wire [72:0] held_frame,tx_owner;
 wire [1023:0] tx_d;wire [3:0] tx_index;
 ot_hbm_integrated_sfu_c12_stage #(.ENABLE(1)) dut(
  .clk(clk),.por_n(por_n),.warm_req(warm_req),.warm_ack(warm_ack),
  .enroll_v(enroll_v),.enroll_r(enroll_r),.enroll_frame(frame),
  .enroll_pc(32'h89abcdef),.enroll_op(32'h12345678),.enroll_source(16'h81a5),
  .enroll_expert(9'h12b),.enroll_matrix(1'b1),.enroll_row(12'd4090),.enroll_count(9'd3),
  .owner_valid(owner_valid),.owner_frame(frame),.source_permit(source_permit),
  .producer_drained(producer_drained),.consumer_drained(consumer_drained),
  .rx_v(rx_v),.rx_r(rx_r),.rx_d(rx_d),.rx_owner(rx_owner),.rx_first(rx_first),.rx_last(rx_last),
  .tx_v(tx_v),.tx_r(tx_r),.tx_d(tx_d),.tx_owner(tx_owner),.tx_index(tx_index),.tx_last(tx_last),
  .complete_v(complete_v),.complete_r(complete_r),.complete_owner(complete_owner),
  .retained(retained),.issued(issued),.ce(ce),.due(due),.fault(fault),.held_frame(held_frame),
  .held_pc(),.held_op(),.held_source(),.held_expert(),.held_matrix(),.held_row(),.held_count());
 // Same child specialization as all64 real lanes, compiled once by hierarchy.
 reg child_rst_n=0,child_v=0;reg [IW-1:0] child_d=0;
 wire child_vo,child_fault;wire [31:0] child_y;
 ot_hbm_sfu_result_c12 child(.clk(clk),.rst_n(child_rst_n),.v(child_v),
  .fn(child_d[2048+:3]),.x(child_d[0+:32]),.vo(child_vo),.y(child_y),.fault(child_fault));
 reg [IW-1:0] requests[0:CASES-1];reg [OW-1:0] expected[0:CASES-1];
 string dir;integer neg_hold=0,roots=0,starts=0,quarter_accepts=0,quarter_retires=0,checked=0;
 always @(posedge clk)begin
  roots=roots+1;
  if(por_n)begin
   if(dut.stage_start&&rx_v&&rx_r&&rx_first)starts=starts+1;
   if(dut.u_sfu.req_v&&dut.u_sfu.req_r)quarter_accepts=quarter_accepts+1;
   if(dut.u_sfu.rsp_v&&dut.u_sfu.rsp_r)quarter_retires=quarter_retires+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task negedge_step;begin @(negedge clk);#1;end endtask
 task cold_reset;
  begin
   negedge_step();por_n=0;warm_req=0;enroll_v=0;rx_v=0;tx_r=0;complete_r=0;
   producer_drained=1;consumer_drained=1;source_permit=1;owner_valid=1;
   repeat(3)tick();negedge_step();por_n=1;tick();
   if(retained||fault||tx_v||complete_v)$fatal(1,"POR_STALE_OWNER_OR_RESPONSE");
  end
 endtask
 task enroll(input integer k);
  begin
   // High token/position bits are real identity bits, independent of localtag32.
   negedge_step();frame=(73'b1<<72)|(73'b1<<52)|73'(32'hde000000+k);
   rx_owner=frame;complete_owner=frame;
   if(!enroll_r)$fatal(1,"ENROLL_NOT_READY");
   enroll_v=1;tick();negedge_step();enroll_v=0;
   if(!retained||held_frame!==frame||issued)$fatal(1,"DESCRIPTOR_ENROLL_FAIL");
  end
 endtask
 task input_packet(input integer k,input integer inject_ce);
  integer b,w;
  begin
   for(b=0;b<3;b=b+1)begin
    negedge_step();rx_v=1;rx_d=({{(3072-IW){1'b0}},requests[k]}>>(1024*b));
    rx_first=b==0;rx_last=b==2;rx_owner=frame;w=0;
    while(!rx_r)begin tick();w=w+1;if(fault||w>8)$fatal(1,"RX_FRAME_REFUSED beat=%0d",b);end
    tick();negedge_step();rx_v=0;rx_d=~rx_d;
    if(inject_ce&&b==0)begin
     dut.u_sfu.u_frame.g_on.u_frame.code[0]^=72'h4;
     #1;if(!dut.u_sfu.u_frame.g_on.repairing||rx_r)$fatal(1,"FRAMING_CE_PERMISSION_FAIL");
     repeat(7)tick();
     if(fault)$fatal(1,"FRAMING_CE_REPAIR_FAIL");
    end
   end
   if(!issued||!retained||held_frame!==frame)$fatal(1,"START_OWNER_LOST");
  end
 endtask
 task run_case(input integer k,input integer inject_ce,input integer warm_drain);
  integer b,w,h,old_starts,old_accepts,old_retires;
  reg [1023:0] held,expbeat;
  begin
   old_starts=starts;old_accepts=quarter_accepts;old_retires=quarter_retires;
   enroll(k);input_packet(k,inject_ce);
   negedge_step();producer_drained=0;consumer_drained=0;
   if(warm_drain)begin warm_req=1;source_permit=0;end
   for(b=0;b<3;b=b+1)begin
    w=0;
    while(!tx_v)begin tick();w=w+1;
     if(fault||w>MAXWAIT)$fatal(1,"ACTUAL_SFU_COMPLETION_FAIL k=%0d beat=%0d",k,b);
    end
    expbeat=({{(3072-OW){1'b0}},expected[k]}>>(1024*b));held=tx_d;
    if(tx_d!==expbeat||tx_owner!==frame||tx_index!==b||tx_last!==(b==2))
     $fatal(1,"FRAMED_GOLDEN_FAIL k=%0d beat=%0d got=%h expected=%h",k,b,tx_d,expbeat);
    // Upstream holds a new first packet; downstream independently stalls.
    negedge_step();rx_v=1;rx_first=1;rx_last=0;rx_owner=frame^73'b1;rx_d=0;
    for(h=0;h<9;h=h+1)begin
     if(neg_hold&&b==0&&h==4)begin
      negedge_step();dut.u_sfu.u_quarter.g_on.u_hold.u_response.u_state.code[0]^=encode64(64'b1);
      $display("NEGATIVE_HELD_CODEWORD_INJECTED");
     end
     tick();
     if(!tx_v||tx_d!==held||tx_owner!==frame||tx_index!==b||rx_r||complete_v||warm_ack)
      $fatal(1,"HELD_RESPONSE_CHANGED");
     if(quarter_retires!=old_retires)$fatal(1,"PREMATURE_CHILD_RETIRE");
    end
    negedge_step();rx_v=0;tx_r=1;tick();negedge_step();tx_r=0;
   end
   if(quarter_retires!=old_retires+1)$fatal(1,"REAL_FINAL_TX_DRAIN_FAIL");
   repeat(5)begin tick();if(complete_v||warm_ack||!retained)$fatal(1,"UNDRAINED_OWNER_RETIRED");end
   negedge_step();producer_drained=1;
   repeat(3)begin tick();if(complete_v)$fatal(1,"CONSUMER_DRAIN_SKIPPED");end
   negedge_step();consumer_drained=1;w=0;
   while(!complete_v)begin tick();w=w+1;if(fault||w>8)$fatal(1,"PERSISTENT_COMPLETE_MISSING");end
   repeat(9)begin tick();if(!complete_v||!retained||held_frame!==frame||warm_ack)$fatal(1,"COMPLETE_NOT_HELD");end
   if(starts!=old_starts+1||quarter_accepts!=old_accepts+1)$fatal(1,"DUPLICATE_START_OR_CHILD_REQUEST");
   negedge_step();complete_owner=k==9?frame^(73'b1<<72):frame;complete_r=1;
   tick();negedge_step();complete_r=0;repeat(2)tick();
   if(k==9)begin
    if(!fault||!retained||held_frame!==frame||complete_v||rx_r||warm_ack)
     $fatal(1,"HIGH_POSITION_COMPLETION_NOT_REFUSED");
    $display("REAL_WRONG_FULL73_COMPLETION_REFUSED");cold_reset();
   end else if(retained||tx_v||complete_v||fault)$fatal(1,"POST_RETIRE_GHOST");
   if(warm_drain)begin
    if(!warm_ack||enroll_r||rx_r)$fatal(1,"WARM_DRAIN_QUARANTINE_FAIL");
    negedge_step();warm_req=0;source_permit=1;repeat(2)tick();
   end
   checked=checked+1;$display("FRAMED_STAGE_RESULT k=%0d roots=%0d",k,roots);
  end
 endtask
 task owner_refusal;
  integer before_starts;
  begin
   before_starts=starts;enroll(0);
   negedge_step();frame=frame^(73'b1<<72);tick();
   if(!fault||!retained||rx_r||complete_v||starts!=before_starts)$fatal(1,"HIGH_POSITION_OWNER_NOT_REFUSED");
   cold_reset();
  end
 endtask
 task single_child_golden;
  integer c,w;
  begin
   for(c=0;c<CASES;c=c+1)begin
    negedge_step();child_rst_n=0;child_v=0;child_d=requests[c];repeat(3)tick();
    negedge_step();child_rst_n=1;repeat(2)tick();negedge_step();child_v=1;tick();
    negedge_step();child_v=0;w=0;
    while(!child_vo)begin tick();w=w+1;if(w>MAXWAIT)$fatal(1,"CHILD_COMPLETION_FAIL");end
    if(child_y!==expected[c][0+:32]||child_fault!==expected[c][2048])$fatal(1,"CHILD_GOLDEN_FAIL k=%0d",c);
   end
   negedge_step();child_rst_n=0;
   $display("SINGLE_CHILD_GOLDEN_PASS family=SFU cases=%0d",CASES);
  end
 endtask
 integer k;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  $readmemh({dir,"/sfu_req.mem"},requests);$readmemh({dir,"/sfu_exp.mem"},expected);
  neg_hold=$test$plusargs("NEG_HOLD");
  if($test$plusargs("CHILD_ONLY"))begin single_child_golden();$finish;end
  cold_reset();
  if(neg_hold)begin run_case(2,0,0);$fatal(1,"NEGATIVE_NOT_OBSERVED");end
  owner_refusal();
  for(k=0;k<CASES;k=k+1)run_case(k,k==2,k==3);
  $display("ENABLED_FULLSHAPE_PASS family=SFU vehicle=ACTUAL_PROTECTED_FRAMED_STAGE checked=%0d starts=%0d child_accepts=%0d child_retires=%0d",checked,starts,quarter_accepts,quarter_retires);
  $finish;
 end
endmodule
