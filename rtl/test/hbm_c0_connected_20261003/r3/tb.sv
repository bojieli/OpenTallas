`timescale 1ns/1ps
// Real connector/RF/W6/FMIN RTL. Behavioral SRAM and protocol-scoped issuer/drain fixture.
module tb;
 reg  clk;
 reg  por_n;
 reg  rst_n;
 reg  req_valid;
 wire  req_ready;
 reg [45:0] req_owner46;
 reg [63:0] req_native_tag;
 reg [63:0] req_native_generation;
 reg  issuer_binding_valid;
 reg  visibility_enable;
 wire  rd_valid;
 wire  rd_ready;
 wire [8:0] rd_a;
 wire [8:0] rd_b;
 wire  rsp_valid;
 wire [4095:0] rsp_a;
 wire [4095:0] rsp_b;
 wire  rsp_ready;
 wire  wr_valid;
 wire  wr_ready;
 wire [8:0] wr_addr;
 wire [4095:0] wr_data;
 wire  ack_valid;
 wire  ack_ready;
 wire[45:0]ack_owner,wr_owner;wire[8:0]ack_slot;wire ack_identity_fault,ack_integration_fault;
 wire  visible_valid;
 wire [54:0] visible_identity;
 wire  result_valid;
 reg  result_ready;
 wire [4095:0] result;
 wire  consumer_accepted;
 wire [54:0] consumer_identity;
 reg  child_reverse_valid;
 reg [54:0] child_reverse_identity;
 wire  child_reverse_ready;
 reg  parent_reverse_valid;
 reg [54:0] parent_reverse_identity;
 wire  parent_reverse_ready;
 reg  reverse_CDC_valid;
 reg [54:0] reverse_CDC_identity;
 wire  reverse_CDC_ready;
 wire  drain_req_valid;
 wire [54:0] drain_req_identity;
 wire  drain_req_has_owner;
 wire  drain_req_reset_scope;
 reg  drain_req_ready;
 reg  drain_rsp_valid;
 reg [54:0] drain_rsp_identity;
 reg  drain_rsp_has_owner;
 reg  drain_rsp_reset_scope;
 reg [8:0] alldrain_live;
 wire  drain_rsp_ready;
 wire  done_valid;
 reg  done_ready;
 wire [63:0] done_native_tag;
 wire [63:0] done_native_generation;
 reg  rearm_valid;
 reg  admission_stop;
 reg  issuer_allcopy_fenced;
 wire  rearm_ready;
 wire  exclusive_lease;
 wire  fault;
 ot_gpu_pc40_physical_ack_source #(.ENABLE(1)) dut(
.clk(clk),
.por_n(por_n),
.rst_n(rst_n),
.req_valid(req_valid),
.req_ready(req_ready),
.req_owner46(req_owner46),
.req_native_tag(req_native_tag),
.req_native_generation(req_native_generation),
.issuer_binding_valid(issuer_binding_valid),
.visibility_enable(visibility_enable),
.rd_valid(rd_valid),
.rd_ready(rd_ready),
.rd_a(rd_a),
.rd_b(rd_b),
.rsp_valid(rsp_valid),
.rsp_a(rsp_a),
.rsp_b(rsp_b),
.rsp_ready(rsp_ready),
.wr_valid(wr_valid),
.wr_ready(wr_ready),
.wr_addr(wr_addr),
.wr_data(wr_data),
.ack_valid(ack_valid),
.ack_ready(ack_ready),
.ack_owner(ack_owner),.ack_slot(ack_slot),.ack_identity_fault(ack_identity_fault),.wr_owner(wr_owner),.ack_integration_fault(ack_integration_fault),
.visible_valid(visible_valid),
.visible_identity(visible_identity),
.result_valid(result_valid),
.result_ready(result_ready),
.result(result),
.consumer_accepted(consumer_accepted),
.consumer_identity(consumer_identity),
.child_reverse_valid(child_reverse_valid),
.child_reverse_identity(child_reverse_identity),
.child_reverse_ready(child_reverse_ready),
.parent_reverse_valid(parent_reverse_valid),
.parent_reverse_identity(parent_reverse_identity),
.parent_reverse_ready(parent_reverse_ready),
.reverse_CDC_valid(reverse_CDC_valid),
.reverse_CDC_identity(reverse_CDC_identity),
.reverse_CDC_ready(reverse_CDC_ready),
.drain_req_valid(drain_req_valid),
.drain_req_identity(drain_req_identity),
.drain_req_has_owner(drain_req_has_owner),
.drain_req_reset_scope(drain_req_reset_scope),
.drain_req_ready(drain_req_ready),
.drain_rsp_valid(drain_rsp_valid),
.drain_rsp_identity(drain_rsp_identity),
.drain_rsp_has_owner(drain_rsp_has_owner),
.drain_rsp_reset_scope(drain_rsp_reset_scope),
.alldrain_live(alldrain_live),
.drain_rsp_ready(drain_rsp_ready),
.done_valid(done_valid),
.done_ready(done_ready),
.done_native_tag(done_native_tag),
.done_native_generation(done_native_generation),
.rearm_valid(rearm_valid),
.admission_stop(admission_stop),
.issuer_allcopy_fenced(issuer_allcopy_fenced),
.rearm_ready(rearm_ready),
.exclusive_lease(exclusive_lease),
.fault(fault));
 reg seed_valid,seed_mode;reg[8:0]seed_addr;reg[4095:0]seed_data;
 wire physical_wr_ready,physical_ack;
 reg inject_stale_ack=0,inject_bad_drain=0;
 assign wr_ready=physical_wr_ready&&!seed_valid;assign ack_valid=(physical_ack&&!seed_mode)||inject_stale_ack;
 ot_gpu_rf_service #(.ACK_ID(1)) rf(.clk(clk),.rst_n(rst_n),.rd_valid(rd_valid),.rd_ready(rd_ready),.rd_a(rd_a),.rd_b(rd_b),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_a(rsp_a),.rsp_b(rsp_b),
 .wr_valid(seed_valid||wr_valid),.wr_ready(physical_wr_ready),.wr_addr(seed_valid?seed_addr:wr_addr),
 .wr_data(seed_valid?seed_data:wr_data),.ack_valid(physical_ack),.ack_ready(seed_mode?1'b1:ack_ready),.wr_owner(seed_mode?46'd0:wr_owner),.ack_owner(ack_owner),.ack_slot(ack_slot),.ack_identity_fault(ack_identity_fault));
 // Real provider macro pins: observe all16banks of both actual RF copies.
 genvar page,bank;
 generate for(page=0;page<4;page=page+1)begin:observe_page
  for(bank=0;bank<16;bank=bank+1)begin:observe_bank
   always @(posedge clk)if(wr_valid&&wr_ready&&wr_addr[8:7]==page)begin
    if(rf.g_identity.g_page[page].g_bank[bank].u_operand_a.w_ce_in!==1'b1 ||
       rf.g_identity.g_page[page].g_bank[bank].u_operand_b.w_ce_in!==1'b1)
      $fatal(1,"actual RF mirror WCE missing");
    $display("EVENT cycle=%0d phase=physical_mirror_WCE page=%0d bank=%0d owner=%h slot=%0d copies=2",cycle,page,bank,wr_owner,wr_addr);
   end
  end
 end endgenerate
 always #0.416667 clk=~clk;
 reg[4095:0]gate_vector,expected_max,expected_min;
 integer cycle=0,reads=0,writes=0,accept_cycle=0;
 reg[45:0]accepted_root_owner,actual_write_owner;reg[8:0]actual_write_slot;reg physical_pending=0;reg actor_pending=0;
 localparam integer PRICED_CONDITIONAL_BOUND=127;
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(seed_mode&&exclusive_lease)$fatal(1,"fixture seed path violated exclusive owner");
  if(req_valid&&req_ready)begin
   actor_pending<=1;accept_cycle<=cycle;accepted_root_owner<=req_owner46;
   $display("EVENT cycle=%0d phase=accepted nativeTag=%h nativeGen=%h enteringWorkspaceLive=0 scope=cold_exclusive_actor",cycle,req_native_tag,req_native_generation);
  end
  if((done_valid&&done_ready)||fault)actor_pending<=0;
  if(actor_pending&&!fault&&cycle-accept_cycle>PRICED_CONDITIONAL_BOUND)$fatal(1,"model conditional bound exceeded");
  if(rd_valid&&rd_ready)begin reads<=reads+1;$display("EVENT cycle=%0d phase=RF_read a=%0d b=%0d",cycle,rd_a,rd_b);end
  if(wr_valid&&wr_ready)begin
   if(wr_owner!==accepted_root_owner)$fatal(1,"current caller inputs retagged accepted physical owner");
   actual_write_owner<=wr_owner;actual_write_slot<=wr_addr;physical_pending<=1;
   writes<=writes+1;$display("EVENT cycle=%0d phase=mirrored_write slot=%0d",cycle,wr_addr);
   if(wr_addr==19)for(integer i=0;i<128;i=i+1)if(wr_data[i*32+:32]!==expected_max[i*32+:32])$fatal(1,"FMAX oracle bits lane%0d",i);
  end
  if(ack_valid&&ack_ready)begin
   if(!physical_pending || ack_owner!==actual_write_owner || ack_slot!==actual_write_slot || ack_identity_fault)$fatal(1,"physical accepted tuple mismatch");
   physical_pending<=0;
  end
  if(ack_valid&&ack_ready)$display("EVENT cycle=%0d phase=physical_ACK owner=%h slot=%0d",cycle,ack_owner,ack_slot);
  if(visible_valid&&visibility_enable)$display("EVENT cycle=%0d phase=visible identity=%h",cycle,visible_identity);
  if(result_valid&&result_ready)$display("EVENT cycle=%0d phase=FMIN_result_accept identity=%h",cycle,consumer_identity);
  if(consumer_accepted)$display("EVENT cycle=%0d phase=W6_consumer identity=%h",cycle,consumer_identity);
  if(done_valid&&done_ready)$display("EVENT cycle=%0d phase=retire nativeTag=%h nativeGen=%h",cycle,done_native_tag,done_native_generation);
 end
 // Positive held allcopy witness only for this cold, sole-source actor.
 // Not a certificate for omitted global production queues/CDC.
 always @(posedge clk)begin
  if(!por_n)begin drain_rsp_valid<=0;drain_rsp_identity<=0;drain_rsp_has_owner<=0;drain_rsp_reset_scope<=0;end
  else if(drain_rsp_valid&&drain_rsp_ready)drain_rsp_valid<=0;
  else if(drain_req_valid&&drain_req_ready)begin
   drain_rsp_valid<=1;drain_rsp_identity<=drain_req_identity ^ (inject_bad_drain?55'd1:55'd0);
   drain_rsp_has_owner<=drain_req_has_owner;drain_rsp_reset_scope<=drain_req_reset_scope;
  end
 end
 always @* drain_req_ready=~drain_rsp_valid;
 task seed(input[4095:0]bits);
 begin
  @(negedge clk);seed_mode=1;seed_valid=1;seed_addr=38;seed_data=bits;
  wait(physical_wr_ready);@(posedge clk);@(negedge clk);seed_valid=0;
  wait(physical_ack);@(posedge clk);@(negedge clk);seed_mode=0;
 end endtask
 // Cold POR between independent mutants is a test-fixture coordinated reset,
 // never a runtime mechanism permitting accepted production debt to disappear.
 task cold_actor;
 begin
  @(negedge clk);por_n=0;rst_n=0;req_valid=0;visibility_enable=0;result_ready=0;
  child_reverse_valid=0;parent_reverse_valid=0;reverse_CDC_valid=0;
  done_ready=0;inject_stale_ack=0;inject_bad_drain=0;alldrain_live=9'h1ff;
  repeat(2)@(negedge clk);por_n=1;rst_n=1;seed(gate_vector);
 end endtask
 task accept_actor;
 begin
  req_native_tag=req_native_tag+1;req_owner46=req_owner46+16;
  wait(req_ready);@(negedge clk);req_valid=1;@(posedge clk);@(negedge clk);req_valid=0;req_owner46=req_owner46^(46'd1<<35);
 end endtask
 task numerical_consume;
 begin
  wait(visible_valid);visibility_enable=1;
  child_reverse_identity=visible_identity;parent_reverse_identity=visible_identity;reverse_CDC_identity=visible_identity;
  wait(result_valid);for(integer i=0;i<128;i=i+1)if(result[i*32+:32]!==expected_min[i*32+:32])$fatal(1,"mutant numerical lane%0d",i);
  @(negedge clk);result_ready=1;@(posedge clk);@(negedge clk);result_ready=0;
 end endtask
 task matched_reverse;
 begin
  wait(child_reverse_ready);@(negedge clk);child_reverse_valid=1;@(posedge clk);@(negedge clk);child_reverse_valid=0;
  wait(parent_reverse_ready);@(negedge clk);parent_reverse_valid=1;@(posedge clk);@(negedge clk);parent_reverse_valid=0;
  wait(reverse_CDC_ready);@(negedge clk);reverse_CDC_valid=1;@(posedge clk);@(negedge clk);reverse_CDC_valid=0;
 end endtask
 task retained_fault(input[255:0]label);
 begin
  repeat(3)@(negedge clk);
  if(!fault||req_ready||done_valid||!exclusive_lease)$fatal(1,"mutant lost debt %s",label);
  $display("CASE_PASS %s retained_owned_debt",label);
 end endtask
 task mutate_valid_tuple(input[54:0]mask,input[255:0]label);
 begin
  cold_actor();accept_actor();wait(physical_ack);@(negedge clk);
  rf.g_identity.protected_ACK=rf.w4_encode({ack_owner,ack_slot} ^ mask);
  wait(fault);retained_fault(label);
  if(ack_ready||!physical_ack||!ack_integration_fault)$fatal(1,"foreign physical tuple consumed");
 end endtask
 initial begin
  clk=0;
  por_n=0;
  rst_n=0;
  req_valid=0;
  req_owner46=0;
  req_native_tag=0;
  req_native_generation=0;
  issuer_binding_valid=0;
  visibility_enable=0;
  result_ready=0;
  child_reverse_valid=0;
  child_reverse_identity=0;
  parent_reverse_valid=0;
  parent_reverse_identity=0;
  reverse_CDC_valid=0;
  reverse_CDC_identity=0;
  alldrain_live=0;
  done_ready=0;
  rearm_valid=0;
  admission_stop=0;
  issuer_allcopy_fenced=0;
  gate_vector=4096'h800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000ff7fffff7f7fffffbf8000003f800000800000010000000142b0000042ae00008000000000000000c2c8000042c80000;expected_max=4096'h0000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae00007f7fffffc2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042c80000c2ae0000;expected_min=4096'h0000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae000042b00000c2ae00003f800000bf8000000000000180000001c2ae0000c2ae0000000000008000000042b00000c2ae0000;
  seed_mode=0;seed_valid=0;seed_addr=0;seed_data=0;alldrain_live=9'h1ff;issuer_binding_valid=1;
  repeat(2)@(negedge clk);por_n=1;rst_n=1;
  seed(gate_vector);
  // Opaque accepted control namespace: no claimed physical HBM PC or W2 ticket.
  req_owner46={7'd1,3'd0,32'd13,4'd2};req_native_tag=64'h100000001;req_native_generation=64'h100000012;
  wait(req_ready);@(negedge clk);req_valid=1;@(posedge clk);@(negedge clk);req_valid=0;req_owner46=req_owner46^(46'd1<<35);
  wait(visible_valid);
  repeat(4)begin @(negedge clk);if(!visible_valid||req_ready||!exclusive_lease)$fatal(1,"held visibility/workspace");end
  if(reads!=3||writes!=5)$fatal(1,"literal producer provider counts");
  child_reverse_identity=visible_identity;parent_reverse_identity=visible_identity;reverse_CDC_identity=visible_identity;
  visibility_enable=1;
  wait(result_valid);
  for(integer i=0;i<128;i=i+1)if(result[i*32+:32]!==expected_min[i*32+:32])$fatal(1,"real RF19 FMIN oracle lane%0d",i);
  repeat(3)begin @(negedge clk);if(!result_valid||fault||req_ready||!exclusive_lease)$fatal(1,"held numerical result/lease");end
  result_ready=1;@(posedge clk);@(negedge clk);result_ready=0;
  wait(child_reverse_ready);@(negedge clk);child_reverse_valid=1;@(posedge clk);@(negedge clk);child_reverse_valid=0;
  wait(parent_reverse_ready);@(negedge clk);parent_reverse_valid=1;@(posedge clk);@(negedge clk);parent_reverse_valid=0;
  wait(reverse_CDC_ready);@(negedge clk);reverse_CDC_valid=1;@(posedge clk);@(negedge clk);reverse_CDC_valid=0;
  wait(done_valid);
  repeat(3)begin @(negedge clk);if(!done_valid||req_ready||reads!=4)$fatal(1,"retained native completion/real consumer read");end
  if(done_native_tag!==64'h100000001||done_native_generation!==64'h100000012||fault)$fatal(1,"native64 identity");
  done_ready=1;@(posedge clk);@(negedge clk);done_ready=0;
  visibility_enable=0;
  wait(req_ready);seed({128{32'h7fc12345}});
  req_owner46={7'd1,3'd0,32'd14,4'd2};req_native_tag=64'h100000002;
  wait(req_ready);@(negedge clk);req_valid=1;@(posedge clk);@(negedge clk);req_valid=0;req_owner46=req_owner46^(46'd1<<35);
  wait(fault);repeat(3)@(negedge clk);
  if(writes!=7||visible_valid||result_valid||req_ready||!exclusive_lease)$fatal(1,"nonfinite published or owner debt lost");
  $display("CASE_PASS NONFINITE_REFUSAL retained_owned_debt");
  cold_actor();accept_actor();
  // Stale untyped physical ACK outside the outstanding write phase refuses.
  inject_stale_ack=1;@(posedge clk);@(negedge clk);inject_stale_ack=0;
  retained_fault("STALE_ACK");
  cold_actor();accept_actor();wait(visible_valid);
  @(negedge clk);rst_n=0;@(posedge clk);@(negedge clk);rst_n=1;
  retained_fault("RUNTIME_RESET");
  cold_actor();accept_actor();numerical_consume();
  wait(child_reverse_ready);@(negedge clk);child_reverse_identity=child_reverse_identity^55'd1;child_reverse_valid=1;
  @(posedge clk);@(negedge clk);child_reverse_valid=0;
  retained_fault("WRONG_REVERSE");
  cold_actor();accept_actor();numerical_consume();inject_bad_drain=1;matched_reverse();
  wait(fault);retained_fault("WRONG_DRAIN");
  cold_actor();accept_actor();numerical_consume();alldrain_live=0;matched_reverse();
  wait(drain_rsp_valid);
  repeat(4)begin @(negedge clk);if(done_valid||drain_rsp_ready||fault||!exclusive_lease)$fatal(1,"missing live allcopy witness released debt");end
  alldrain_live=9'h1ff;wait(done_valid);@(negedge clk);done_ready=1;@(posedge clk);@(negedge clk);done_ready=0;
  $display("CASE_PASS MISSING_ALLCOPY blocks_then_matched_drain");
  mutate_valid_tuple(55'd1<<54,"WRONG_PC7");
  mutate_valid_tuple(55'd1<<45,"WRONG_CLIENT3");
  mutate_valid_tuple(55'd1<<44,"WRONG_TAG32_HIGH");
  mutate_valid_tuple(55'd1<<9,"WRONG_GEN4");
  mutate_valid_tuple(55'd1,"WRONG_RF_SLOT9");
  cold_actor();accept_actor();wait(physical_ack);@(negedge clk);
  rf.g_identity.protected_ACK=rf.g_identity.protected_ACK ^ 72'd3;
  wait(fault);retained_fault("W4_ACK_DUE");
  if(ack_ready||!physical_ack||!ack_identity_fault)$fatal(1,"faulted physical ACK consumed");
  $display("CONNECTED_PHYSICAL_ACK_PC40_PASS FMAX128 FMIN128 actual_RF4read_5write_ACK_W6 held_native64_and_workspace NaN_refusal production_caller_FALSE");$finish;
 end
endmodule
module ot_sram_1r1w_128x256_m1_r2c2(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,w_mask_in,
 input wire[1:0]rr_en,input wire[11:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg[255:0]mem[0:127];
 always @(posedge clk)begin if(r_ce_in)rd_out<=mem[r_addr_in];if(w_ce_in)mem[w_addr_in]<=wd_in;end
endmodule
