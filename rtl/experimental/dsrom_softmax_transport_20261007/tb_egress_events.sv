`timescale 1ps/1fs
module tb_egress_events;
 reg clk=0;always #416.666666667 clk=~clk;
 reg rst_n=0,begin_valid=0,begin_short=0,capture_commit=0,receipt_valid=0,release_valid=0;
 reg[31:0] begin_epoch=0,capture_epoch=0;reg[15:0] begin_tag=16'h7e57,capture_tag=16'h7e57;
 reg[6:0] capture_addr=0;reg[55:0] receipt_identity=0;
 wire begin_ready,event_valid,complete,fault,event_upper_half;
 wire[2:0] event_kind,phase_kind;wire[31:0] event_epoch;wire[15:0]event_tag;wire[6:0]event_row,phase_row;
 reg bridge_allow=1;wire actual_ready;wire phase_ready=actual_ready&&bridge_allow;
 ot_dsrom_softmax_egress_events dut(.*);
 reg native_v=0,den_v=0;reg[2:0]native_kind=0;
 wire phase_fault,phase_busy,phase_cmd_ready,phase_half;wire[15:0]phase_tag;
 ot_dsrom_softmax_phase phases(.clk(clk),.rst_n(rst_n),.cmd_v(begin_valid),.cmd_short(begin_short),.cmd_fault(1'b0),
  .cmd_tag(begin_tag),.cmd_ready(phase_cmd_ready),.event_v(native_v||event_valid),.event_kind(native_v?native_kind:event_kind),
  .event_tag(begin_tag),.event_ready(actual_ready),.expected_kind(phase_kind),.memory_row(phase_row),.bf16_upper_half(phase_half),
  .den_v(den_v),.den_tag(begin_tag),.busy(phase_busy),.fault(phase_fault),.active_tag(phase_tag));
 integer edge_no=0;always @(negedge clk)edge_no=edge_no+1;
 integer count2=0,count3=0,count6=0,count7=0,total=0,first_cap_b_edge=0,last_cap_b_event_edge=0;
 integer cap_edge[0:15];integer rec_edge[0:15];
 reg check_latency=0;
 always @(posedge clk)if(event_valid)begin
  if(native_v)$fatal(1,"NATIVE_EVENT_COLLISION");
  if(event_epoch!=begin_epoch||event_tag!=begin_tag||event_row!=phase_row||!actual_ready)$fatal(1,"EVENT_IDENTITY_OR_READINESS");
  if((event_kind==6||event_kind==7)&&event_upper_half!==phase_half)$fatal(1,"PACKED_HALF_ORDER");
  case(event_kind)
   2:count2=count2+1;
   3:count3=count3+1;
   6:begin
    if(check_latency&&edge_no-cap_edge[event_row-112]!=(event_upper_half?2:1))$fatal(1,"CAPTURE_EXPANSION_LATENCY got%0d",edge_no-cap_edge[event_row-112]);
    count6=count6+1;last_cap_b_event_edge=edge_no;
   end
   7:count7=count7+1;
   default:$fatal(1,"WRONG_KIND");
  endcase
  total=total+1;
 end
 task automatic reset;
  @(negedge clk);rst_n=0;begin_valid=0;capture_commit=0;receipt_valid=0;release_valid=0;native_v=0;den_v=0;bridge_allow=1;check_latency=0;
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  count2=0;count3=0;count6=0;count7=0;
  if(fault||phase_fault||event_valid||complete||!begin_ready)$fatal(1,"RESET");
 endtask
 task automatic start(input integer ep,input bit short_t);
  @(negedge clk);begin_epoch=ep;capture_epoch=ep;begin_short=short_t;begin_valid=1;
  @(negedge clk);begin_valid=0;count2=0;count3=0;count6=0;count7=0;
 endtask
 task automatic native(input integer kind,input integer n);
  for(integer j=0;j<n;j=j+1)begin
   while(!actual_ready||phase_kind!=kind)@(negedge clk);
   native_kind=kind;native_v=1;@(negedge clk);native_v=0;
   if(fault||phase_fault)$fatal(1,"NATIVE_PHASE");
  end
 endtask
 task automatic src(input integer row);
  capture_addr=row;capture_commit=1;
  if(row>=112)cap_edge[row-112]=edge_no;
  @(negedge clk);capture_commit=0;
 endtask
 task automatic receipt(input integer row,input integer ep);
  receipt_identity={row>=112,32'(ep),begin_tag,7'(row)};receipt_valid=1;
  @(negedge clk);receipt_valid=0;
 endtask
 task automatic campaign(input integer ep,input bit short_t);
  start(ep,short_t);native(0,short_t?8:40);native(1,short_t?8:40);
  bridge_allow=0;
  for(integer j=0;j<(short_t?8:40);j=j+1)src(72+j);
  for(integer j=0;j<(short_t?8:40);j=j+1)receipt(72+j,ep);
  repeat(7)@(negedge clk);
  if(count2||count3||event_valid||complete||fault)$fatal(1,"PENDING_EVENTS_LOST_OR_ESCAPED");
  bridge_allow=1;
  while(phase_kind!=4&&!fault&&!phase_fault)@(negedge clk);
  if(fault||phase_fault||count2!=(short_t?8:40)||count3!=(short_t?8:40))$fatal(1,"E_DEBT_DRAIN");
  den_v=1;@(negedge clk);den_v=0;
  native(4,32);native(5,32);check_latency=1;first_cap_b_edge=edge_no;
  for(integer j=0;j<16;j=j+1)begin src(112+j);@(negedge clk);end
  while(count6!=32&&!fault&&!phase_fault)@(negedge clk);
  if(fault||phase_fault||last_cap_b_event_edge-first_cap_b_edge!=32)$fatal(1,"BF_EXPANSION_BURST_LENGTH");
  check_latency=0;
  //15packed receipts certify30BF vectors. The last two cannot retire early.
  for(integer j=0;j<15;j=j+1)receipt(112+j,ep);
  while(count7!=30&&!fault&&!phase_fault)@(negedge clk);
  repeat(7)@(negedge clk);
  if(complete||!phase_busy||fault||phase_fault)$fatal(1,"EARLY_PACKED_COMPLETION");
  receipt(127,ep);while(!complete&&!fault&&!phase_fault)@(negedge clk);
  if(fault||phase_fault||phase_busy||count7!=32)$fatal(1,"FINAL_COMPLETION fault%b phasefault%b busy%b c7%0d complete%b ce%0d re%0d cb%0d rb%0d xb%0d yb%0d kind%0d",fault,phase_fault,phase_busy,count7,complete,dut.ce,dut.re,dut.cb,dut.rb,dut.xb,dut.yb,phase_kind);
  repeat(5)@(negedge clk);if(!complete||begin_ready)$fatal(1,"COMPLETE_HOLD");
  release_valid=1;@(negedge clk);release_valid=0;@(negedge clk);
  if(!begin_ready||fault)$fatal(1,"RELEASE");
  $display("CAMPAIGN PASS ep%0d E%0d CAP_O32 DRAIN_O32 packed_commit_to_events=1,2 last_CAP_O_from_first_packed_commit=32edges",ep,short_t?8:40);
 endtask
 initial begin
  reset();campaign(1,0);campaign(2,1);
  reset();start(3,1);src(72);receipt(72,2);if(!fault)$fatal(1,"STALE_EPOCH_NOT_REJECTED");
  reset();start(4,1);receipt(72,4);if(!fault)$fatal(1,"RECEIPT_BEFORE_CAPTURE_NOT_REJECTED");
  reset();start(5,1);src(72);src(72);if(!fault)$fatal(1,"DUPLICATE_CAPTURE_NOT_REJECTED");
  reset();start(6,1);src(112);if(!fault)$fatal(1,"BF_BEFORE_E_VISIBILITY_NOT_REJECTED");
  reset();start(7,1);capture_epoch=6;src(72);if(!fault)$fatal(1,"CAPTURE_EPOCH_NOT_REJECTED");
  reset();start(8,1);src(72);dut.ce[0]=~dut.ce[0];@(negedge clk);if(!fault)$fatal(1,"CONTROL_CORRUPTION_NOT_REJECTED");
  reset();start(9,1);release_valid=1;@(negedge clk);release_valid=0;if(!fault)$fatal(1,"EARLY_RELEASE_NOT_REJECTED");
  reset();start(10,1);src(72);receipt(72,10);reset();repeat(10)@(negedge clk);
  if(event_valid||complete)$fatal(1,"ABORT_PENDING_EVENTS_ESCAPED");
  $display("PASS committed-payload phase bridge events=%0d fullT640/T128 realphase barriers/backpressure; packed halves; identity/order/control/abort",total);$finish;
 end
 initial begin repeat(2500)@(posedge clk);$fatal(1,"FINITE_PROTOCOL_STUCK kind%0d counts%0d,%0d,%0d,%0d fault%b phasefault%b",phase_kind,count2,count3,count6,count7,fault,phase_fault);end
endmodule
