`timescale 1ns/1ps
module tb_qkd_host_lifecycle_collected;
 reg clk=0;
 reg por_n=0;
 reg warm_ready=0;
 reg request_valid=0;
 wire request_ready;
 reg [17:0] request_token=0;
 reg [17:0] request_position=0;
 reg [1:0] request_generation=0;
 wire grant_valid;
 reg grant_ready=0;
 wire [15:0] grant_epoch;
 wire [17:0] grant_token;
 wire [17:0] grant_position;
 wire [1:0] grant_generation;
 wire [58:0] grant_tag;
 wire allocated_valid;
 wire allocated_delivered;
 reg [7:0] participant_valid=0;
 reg [471:0] participant_tag=0;
 reg [15:0] participant_generation=0;
 wire [7:0] participant_accepted;
 reg engine_admit_ready=0;
 reg [7:0] participant_ready=0;
 wire dispatch_valid;
 wire dispatched;
 wire [58:0] cohort_tag;
 wire [1:0] cohort_generation;
 wire [7:0] accepted_ranks;
 reg result_valid=0;
 reg result_done=0;
 reg result_fault=0;
 reg [58:0] result_tag=0;
 reg [1:0] result_generation=0;
 reg [7:0] cancel_valid=0;
 reg [7:0] cancel_done=0;
 reg [7:0] cancel_fault=0;
 reg [471:0] cancel_tag=0;
 reg [15:0] cancel_generation=0;
 wire [7:0] cancel_accepted;
 reg [7:0] kv_drained=0;
 reg [7:0] vm_drained=0;
 reg [7:0] collective_drained=0;
 reg [7:0] host_drained=0;
 reg post_retired=0;
 reg [58:0] post_tag=0;
 reg [1:0] post_generation=0;
 wire post_pending;
 wire [58:0] acknowledged_tag;
 wire [1:0] acknowledged_generation;
 reg recovery_start=0;
 reg [7:0] links_drained=0;
 reg [7:0] link_reset_seen=0;
 reg [7:0] retraining_done=0;
 wire link_reset_request;
 wire retraining_request;
 wire recovery_complete;
 wire wrap_locked;
 wire identity_fault;
 wire terminal_accepted;
 wire lifecycle_fault;
 qkd_host_lifecycle_collected #(.INITIAL_EPOCH(16'hffff)) dut (.clk(clk), .por_n(por_n), .warm_ready(warm_ready), .request_valid(request_valid), .request_ready(request_ready), .request_token(request_token), .request_position(request_position), .request_generation(request_generation), .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token), .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag), .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered), .participant_valid(participant_valid), .participant_tag(participant_tag), .participant_generation(participant_generation), .participant_accepted(participant_accepted), .engine_admit_ready(engine_admit_ready), .participant_ready(participant_ready), .dispatch_valid(dispatch_valid), .dispatched(dispatched), .cohort_tag(cohort_tag), .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks), .result_valid(result_valid), .result_done(result_done), .result_fault(result_fault), .result_tag(result_tag), .result_generation(result_generation), .cancel_valid(cancel_valid), .cancel_done(cancel_done), .cancel_fault(cancel_fault), .cancel_tag(cancel_tag), .cancel_generation(cancel_generation), .cancel_accepted(cancel_accepted), .kv_drained(kv_drained), .vm_drained(vm_drained), .collective_drained(collective_drained), .host_drained(host_drained), .post_retired(post_retired), .post_tag(post_tag), .post_generation(post_generation), .post_pending(post_pending), .acknowledged_tag(acknowledged_tag), .acknowledged_generation(acknowledged_generation), .recovery_start(recovery_start), .links_drained(links_drained), .link_reset_seen(link_reset_seen), .retraining_done(retraining_done), .link_reset_request(link_reset_request), .retraining_request(retraining_request), .recovery_complete(recovery_complete), .wrap_locked(wrap_locked), .identity_fault(identity_fault), .terminal_accepted(terminal_accepted), .lifecycle_fault(lifecycle_fault));
 task tick; begin #5; clk=1; #1; clk=0; #4; end endtask
 task check(input bit ok,input string why); begin if(!ok) $fatal(1,"%s",why); end endtask
 reg [58:0] allocated;
 integer i;
 initial begin
  tick; por_n=1; warm_ready=1; participant_ready=255; engine_admit_ready=1;
  request_token=151935; request_position=8191; request_generation=3; request_valid=1;
  tick; request_valid=0; check(grant_valid,"grant absent"); allocated=grant_tag;
  check(grant_epoch==65535 && wrap_locked,"last epoch allocation");
  grant_ready=1; tick; grant_ready=0;
  for(i=0;i<8;i=i+1) begin participant_tag[59*i+:59]=allocated; participant_generation[2*i+:2]=3; end
  participant_valid=127; tick; participant_valid=0; tick;
  check(!dispatched,"partial cohort dispatched");
  participant_valid=128; tick; check(participant_accepted==128,"participant aggregation");
  participant_valid=0; tick; check(dispatched,"dispatch absent");
  // Completion must remain held while any actual participant drain is absent.
  result_tag={allocated[58:43],6'd37,allocated[36:0]}; result_generation=3;
  result_valid=1; result_done=1; kv_drained=255; vm_drained=255; collective_drained=255; host_drained=127;
  tick; result_valid=0; tick; tick;
  check(allocated_valid && !terminal_accepted,"missing rank drain retired token");
  for(i=0;i<8;i=i+1) begin cancel_tag[59*i+:59]=result_tag; cancel_generation[2*i+:2]=3; end
  cancel_valid=8'h81; cancel_fault=8'h81; host_drained=255;
  tick; check(terminal_accepted,"held result not consumed");
  check(cancel_accepted==8'h81,"identity ACK absent");
  tick; cancel_valid=0; tick; tick;
  check(post_pending && !request_ready,"POST barrier absent");
  check(acknowledged_tag==result_tag && acknowledged_generation==3,"ACK identity lost");
  // A new late source after terminal and rearm acknowledges the same accepted
  // identity exactly once; it does not manufacture another terminal event.
  cancel_valid=2;cancel_fault=2;#1;check(cancel_accepted==2,"late matching cancel stranded during POST");
  tick;check(cancel_accepted==0,"held late cancel acknowledged twice");cancel_valid=0;tick;
  check(!identity_fault,"late matching cancel diagnosed as stale");
  post_retired=1; post_tag=result_tag; post_generation=3; tick; post_retired=0;
  check(!post_pending && wrap_locked && !request_ready,"wrap fence absent");
  // Stale reset/training pulses before recovery cannot satisfy its witnesses.
  link_reset_seen=255; retraining_done=255; tick; link_reset_seen=0; retraining_done=0;
  recovery_start=1; tick; recovery_start=0; links_drained=127; tick;
  check(!link_reset_request && !recovery_complete,"undrained link requested reset");
  links_drained=255; tick; check(link_reset_request,"real drained links not used");
  tick; check(!retraining_request && !recovery_complete,"stale reset witness accepted");
  link_reset_seen=127; tick; check(!retraining_request,"missing rank reset accepted");
  link_reset_seen=128; tick; link_reset_seen=0; check(retraining_request,"reset aggregation absent");
  retraining_done=127; tick; tick; check(!recovery_complete && wrap_locked,"missing rank training accepted");
  retraining_done=128; tick; retraining_done=0; tick;
  check(recovery_complete && !wrap_locked && !identity_fault,"coherent wrap recovery failed");
  request_valid=1; tick; request_valid=0; check(grant_epoch==0 && grant_valid,"epoch zero not restored");
  cancel_valid=1; cancel_fault=1; cancel_generation[0+:2]=3;
  cancel_tag[0+:59]={grant_tag[58:43],6'd37,grant_tag[36:0]};
  tick; tick; tick; cancel_valid=0; tick; tick;
  check(post_pending && !request_ready && !wrap_locked,"normal epoch POST barrier absent");
  post_retired=1; post_tag=acknowledged_tag; post_generation=3; tick; post_retired=0;
  request_valid=1; tick; request_valid=0;
  // Wrong held cancel identity must fail closed without acknowledging its source.
  cancel_valid=1; cancel_tag[0+:59]=59'h123; cancel_generation[0+:2]=3; cancel_fault=1;
  tick; tick; check(identity_fault && cancel_accepted==0 && allocated_valid,"stale cancel accepted");
  cancel_tag[0+:59]={grant_tag[58:43],6'd37,grant_tag[36:0]};
  tick; tick; check(terminal_accepted && cancel_accepted==1,"owned cancellation could not retire stale snapshot");
  tick; cancel_valid=0; tick; tick;
  post_retired=1; post_tag=acknowledged_tag; post_generation=3; tick; post_retired=0;
  recovery_start=1; tick; recovery_start=0;
  link_reset_seen=255; retraining_done=255; tick; tick; tick;
  check(recovery_complete && !identity_fault,"identity fault physical recovery failed");
  link_reset_seen=0; retraining_done=0;
  // A real cancellation also retires an allocation whose grant was never delivered.
  por_n=0; cancel_valid=0; tick; por_n=1; request_valid=1; tick; request_valid=0;
  check(allocated_valid && !allocated_delivered,"undelivered allocation absent");
  cancel_tag[0+:59]={grant_tag[58:43],6'd37,grant_tag[36:0]};
  cancel_generation[0+:2]=3; cancel_fault=1; cancel_done=0; cancel_valid=1;
  tick; tick; check(terminal_accepted && cancel_accepted==1,"undelivered cancel not acknowledged");
  tick; tick; tick; check(!terminal_accepted && cancel_accepted==0 && !identity_fault,"held cancel consumed twice");
  check(post_pending && !request_ready,"cancel omitted POST barrier");
  $display("PASS collected lifecycle identity/drains/POST/latecancel/participant/wrap/recovery"); $finish;
 end
endmodule
