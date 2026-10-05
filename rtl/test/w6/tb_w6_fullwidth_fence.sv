`timescale 1ns/1ps
module tb_w6_fullwidth_fence;
  import ot_gpu_w6_secded_pkg::*;
  reg clk=0; always #5 clk=~clk;
  reg por_n=1, rst_n=1, req_internal_SIMD=0;
  reg drain_rsp_has_owner=0, drain_rsp_reset_scope=0;
  reg [8:0] alldrain_live=9'h1ff;
  wire drain_req_has_owner, drain_req_reset_scope, fault, quarantine;
  integer edge_count=0, testcase=0, checks=0, accepted=0;
  reg [54:0] owner;
  reg req_valid=0; reg [54:0] req_identity=0; wire req_ready;
  reg host_ack_valid=0; reg [54:0] host_ack_identity=0; wire host_ack_ready;
  reg simd_ack_retire_valid=0; reg [54:0] simd_ack_retire_identity=0; wire simd_ack_retire_ready;
  reg consumer_valid=0; reg [54:0] consumer_identity=0; wire consumer_ready;
  reg child_reverse_valid=0; reg [54:0] child_reverse_identity=0; wire child_reverse_ready;
  reg parent_reverse_valid=0; reg [54:0] parent_reverse_identity=0; wire parent_reverse_ready;
  reg reverse_CDC_valid=0; reg [54:0] reverse_CDC_identity=0; wire reverse_CDC_ready;
  reg drain_rsp_valid=0; reg [54:0] drain_rsp_identity=0; wire drain_rsp_ready;
  wire visible_valid; wire [54:0] visible_identity; reg visible_ready=0;
  wire drain_req_valid; wire [54:0] drain_req_identity; reg drain_req_ready=0;
  wire retire_valid; wire [54:0] retire_identity; reg retire_ready=0;
  ot_gpu_rf_visibility_fence_w6 #(.ENABLE(1)) dut(
    .clk(clk),
    .por_n(por_n),
    .rst_n(rst_n),
    .req_internal_SIMD(req_internal_SIMD),
    .drain_rsp_has_owner(drain_rsp_has_owner),
    .drain_rsp_reset_scope(drain_rsp_reset_scope),
    .alldrain_live(alldrain_live),
    .drain_req_has_owner(drain_req_has_owner),
    .drain_req_reset_scope(drain_req_reset_scope),
    .fault(fault),
    .quarantine(quarantine),
    .req_valid(req_valid),
    .req_identity(req_identity),
    .req_ready(req_ready),
    .host_ack_valid(host_ack_valid),
    .host_ack_identity(host_ack_identity),
    .host_ack_ready(host_ack_ready),
    .simd_ack_retire_valid(simd_ack_retire_valid),
    .simd_ack_retire_identity(simd_ack_retire_identity),
    .simd_ack_retire_ready(simd_ack_retire_ready),
    .consumer_valid(consumer_valid),
    .consumer_identity(consumer_identity),
    .consumer_ready(consumer_ready),
    .child_reverse_valid(child_reverse_valid),
    .child_reverse_identity(child_reverse_identity),
    .child_reverse_ready(child_reverse_ready),
    .parent_reverse_valid(parent_reverse_valid),
    .parent_reverse_identity(parent_reverse_identity),
    .parent_reverse_ready(parent_reverse_ready),
    .reverse_CDC_valid(reverse_CDC_valid),
    .reverse_CDC_identity(reverse_CDC_identity),
    .reverse_CDC_ready(reverse_CDC_ready),
    .drain_rsp_valid(drain_rsp_valid),
    .drain_rsp_identity(drain_rsp_identity),
    .drain_rsp_ready(drain_rsp_ready),
    .visible_valid(visible_valid),
    .visible_identity(visible_identity),
    .visible_ready(visible_ready),
    .drain_req_valid(drain_req_valid),
    .drain_req_identity(drain_req_identity),
    .drain_req_ready(drain_req_ready),
    .retire_valid(retire_valid),
    .retire_identity(retire_identity),
    .retire_ready(retire_ready)
  );
  wire off_req,off_visible,off_drain,off_retire,off_fault,off_quarantine;
  ot_gpu_rf_visibility_fence_w6 off_dut(
    .clk(clk),
    .por_n(por_n),
    .rst_n(rst_n),
    .req_internal_SIMD(req_internal_SIMD),
    .drain_rsp_has_owner(drain_rsp_has_owner),
    .drain_rsp_reset_scope(drain_rsp_reset_scope),
    .alldrain_live(alldrain_live),
    .drain_req_has_owner(),
    .drain_req_reset_scope(),
    .fault(off_fault),
    .quarantine(off_quarantine),
    .req_valid(req_valid),
    .req_identity(req_identity),
    .req_ready(off_req),
    .host_ack_valid(host_ack_valid),
    .host_ack_identity(host_ack_identity),
    .host_ack_ready(),
    .simd_ack_retire_valid(simd_ack_retire_valid),
    .simd_ack_retire_identity(simd_ack_retire_identity),
    .simd_ack_retire_ready(),
    .consumer_valid(consumer_valid),
    .consumer_identity(consumer_identity),
    .consumer_ready(),
    .child_reverse_valid(child_reverse_valid),
    .child_reverse_identity(child_reverse_identity),
    .child_reverse_ready(),
    .parent_reverse_valid(parent_reverse_valid),
    .parent_reverse_identity(parent_reverse_identity),
    .parent_reverse_ready(),
    .reverse_CDC_valid(reverse_CDC_valid),
    .reverse_CDC_identity(reverse_CDC_identity),
    .reverse_CDC_ready(),
    .drain_rsp_valid(drain_rsp_valid),
    .drain_rsp_identity(drain_rsp_identity),
    .drain_rsp_ready(),
    .visible_valid(off_visible),
    .visible_identity(),
    .visible_ready(visible_ready),
    .drain_req_valid(off_drain),
    .drain_req_identity(),
    .drain_req_ready(drain_req_ready),
    .retire_valid(off_retire),
    .retire_identity(),
    .retire_ready(retire_ready)
  );
  task check(input bit okay,input string message);
    begin checks=checks+1; if (!okay) $fatal(1,"W6_CHECK_FAIL case=%0d edge=%0d %s",testcase,edge_count,message); end
  endtask
  task tick; begin @(posedge clk); #1; end endtask
  task clear_inputs;
    begin
      req_valid=0;
      host_ack_valid=0;
      simd_ack_retire_valid=0;
      consumer_valid=0;
      child_reverse_valid=0;
      parent_reverse_valid=0;
      reverse_CDC_valid=0;
      drain_rsp_valid=0;
      visible_ready=0;
      drain_req_ready=0;
      retire_ready=0;
    end
  endtask
  always @(posedge clk) begin
    edge_count=edge_count+1;
    if (req_valid && req_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=req edge=%0d identity=%014h",testcase,edge_count,req_identity); end
    if (host_ack_valid && host_ack_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=host_ack edge=%0d identity=%014h",testcase,edge_count,host_ack_identity); end
    if (simd_ack_retire_valid && simd_ack_retire_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=simd_ack_retire edge=%0d identity=%014h",testcase,edge_count,simd_ack_retire_identity); end
    if (visible_valid && visible_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=visible edge=%0d identity=%014h",testcase,edge_count,visible_identity); end
    if (consumer_valid && consumer_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=consumer edge=%0d identity=%014h",testcase,edge_count,consumer_identity); end
    if (child_reverse_valid && child_reverse_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=child_reverse edge=%0d identity=%014h",testcase,edge_count,child_reverse_identity); end
    if (parent_reverse_valid && parent_reverse_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=parent_reverse edge=%0d identity=%014h",testcase,edge_count,parent_reverse_identity); end
    if (reverse_CDC_valid && reverse_CDC_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=reverse_CDC edge=%0d identity=%014h",testcase,edge_count,reverse_CDC_identity); end
    if (drain_req_valid && drain_req_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=drain_req edge=%0d identity=%014h",testcase,edge_count,drain_req_identity); end
    if (drain_rsp_valid && drain_rsp_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=drain_rsp edge=%0d identity=%014h",testcase,edge_count,drain_rsp_identity); end
    if (retire_valid && retire_ready) begin accepted=accepted+1; $display("W6_EDGE case=%0d kind=retire edge=%0d identity=%014h",testcase,edge_count,retire_identity); end
  end
  // Finite command protocol bounds are assertions, not elapsed job deadlines.
  task send(input integer kind, input reg [54:0] id);
    integer j; bit done;
    begin
      @(negedge clk); done=0;
      case(kind)
        0:begin req_valid=1; req_identity=id; end
        1:begin host_ack_valid=1; host_ack_identity=id; end
        2:begin simd_ack_retire_valid=1; simd_ack_retire_identity=id; end
        3:visible_ready=1;
        4:begin consumer_valid=1; consumer_identity=id; end
        5:begin child_reverse_valid=1; child_reverse_identity=id; end
        6:begin parent_reverse_valid=1; parent_reverse_identity=id; end
        7:begin reverse_CDC_valid=1; reverse_CDC_identity=id; end
        8:drain_req_ready=1;
        9:begin drain_rsp_valid=1; drain_rsp_identity=id; end
        10:retire_ready=1;
      endcase
      for(j=0;j<32 && !done;j=j+1) begin
        @(posedge clk);
        case(kind)
          0:done=req_ready;
          1:done=host_ack_ready;
          2:done=simd_ack_retire_ready;
          3:done=visible_valid;
          4:done=consumer_ready;
          5:done=child_reverse_ready;
          6:done=parent_reverse_ready;
          7:done=reverse_CDC_ready;
          8:done=drain_req_valid;
          9:done=drain_rsp_ready;
          10:done=retire_valid;
        endcase
        #1;
      end
      check(done,"finite valid/ready boundary did not complete");
      @(negedge clk); clear_inputs;
    end
  endtask
  task cold_boot;
    begin
      @(negedge clk); clear_inputs; por_n=0; rst_n=1;
      tick; tick; @(negedge clk); por_n=1;
      tick; check(quarantine && !req_ready,"cold boot must await global source drain");
      send(8,0);
      check(drain_req_reset_scope && !drain_req_has_owner,"boot drain scope");
      drain_rsp_has_owner=0; drain_rsp_reset_scope=1; alldrain_live='1;
      send(9,0); tick; check(!quarantine,"cold source drain unlock");
      drain_rsp_reset_scope=0; drain_rsp_has_owner=1;
    end
  endtask
  task recover;
    reg [54:0] keep; bit held_owner;
    begin
      keep=dut.enabled.identity; held_owner=dut.enabled.raw[59];
      @(negedge clk); clear_inputs; rst_n=0; tick; tick;
      check(dut.enabled.identity==keep && !req_ready,"warm reset retains owner");
      @(negedge clk); rst_n=1;
      send(8,keep);
      drain_rsp_has_owner=held_owner; drain_rsp_reset_scope=1; alldrain_live='1;
      // Old normal-scope response and foreign reset identity cannot release.
      @(negedge clk); drain_rsp_valid=1; drain_rsp_identity=keep;
      drain_rsp_reset_scope=0; tick;
      check(!drain_rsp_ready && quarantine,"old normal certificate rejected during reset");
      @(negedge clk); drain_rsp_reset_scope=1; drain_rsp_identity=keep^55'd1; tick;
      check(!drain_rsp_ready && quarantine,"wrong reset owner rejected");
      @(negedge clk); clear_inputs;
      // An old ACK is ignored in quarantine; the source drain level remains
      // false while that copy exists. No invented historical epoch certificate.
      drain_rsp_valid=1; drain_rsp_identity=keep;
      host_ack_valid=1; host_ack_identity=keep; alldrain_live=9'h1fe;
      tick; check(!host_ack_ready && !drain_rsp_ready && quarantine,"old ACK copy blocks external scoped drain");
      @(negedge clk); clear_inputs; alldrain_live='1;
      send(9,keep); tick; check(!fault && !quarantine,"source coordinated reset recovery");
      drain_rsp_reset_scope=0; drain_rsp_has_owner=1;
    end
  endtask
  task prefix(input integer stop);
    begin
      req_internal_SIMD=0; send(0,owner);
      if(stop>=1) send(1,owner);
      if(stop>=2) send(3,owner);
      if(stop>=3) send(4,owner);
      if(stop>=4) send(5,owner);
      if(stop>=5) send(6,owner);
      if(stop>=6) send(7,owner);
      if(stop>=7) send(8,owner);
      if(stop>=8) send(9,owner);
    end
  endtask
  integer i,j; reg [143:0] pristine; reg [65:0] decoded;
  initial begin
    // C0 client0 first; KV client5 next. Preserve PC/tag/gen/slot full widths.
    owner={7'd127,3'd0,32'hfe123456,4'hf,9'h1ff};
    cold_boot;
    testcase=1; req_internal_SIMD=0; send(0,owner); send(1,owner);
    // Visibility held over consumer backpressure; no forward lease release.
    repeat(6) begin tick; check(visible_identity==owner && !req_ready,"held owner under backpressure"); end
    check(visible_valid,"visibility survives stall");
    send(3,owner); send(4,owner); send(5,owner); send(6,owner); send(7,owner); send(8,owner);
    // Each one of the nine live source debt classes independently blocks reuse.
    for(i=0;i<9;i=i+1) begin
      @(negedge clk); drain_rsp_valid=1; drain_rsp_identity=owner; alldrain_live=9'h1ff^(9'd1<<i);
      tick; check(!drain_rsp_ready && !req_ready && !retire_valid,"missing current source drain class");
    end
    @(negedge clk); clear_inputs; alldrain_live='1;
    send(9,owner); send(10,owner);
    testcase=2; owner={7'd127,3'd5,32'hfe123456,4'h0,9'h1ff};
    req_internal_SIMD=1; send(0,owner); send(2,owner); send(3,owner); send(4,owner);
    send(5,owner); send(6,owner); send(7,owner); send(8,owner); send(9,owner); send(10,owner);
    testcase=3; owner={7'd127,3'd0,32'hfe123456,4'h0,9'h1ff};
    req_internal_SIMD=0; send(0,owner); send(1,owner); send(3,owner); send(4,owner);
    send(5,owner); send(6,owner); send(7,owner);
    repeat(5) begin tick; check(drain_req_valid && drain_req_identity==owner && !req_ready,"held source drain request"); end
    send(8,owner); send(9,owner);
    repeat(5) begin tick; check(retire_valid && retire_identity==owner && !req_ready,"held retirement identity"); end
    send(10,owner);
    // Wrong field mutants PC,client,tag high/low,gen,slot; no mirrored ACK alias.
    for(i=0;i<6;i=i+1) begin
      testcase=10+i; req_internal_SIMD=0; send(0,owner);
      @(negedge clk); host_ack_valid=1; host_ack_identity=owner^(55'd1 << (i==0?54:i==1?45:i==2?44:i==3?13:i==4?9:0));
      tick; check(fault && !visible_valid && !req_ready && dut.enabled.identity==owner,"foreign ACK alias mutant");
      @(negedge clk); clear_inputs; recover;
    end
    testcase=20; req_internal_SIMD=1; send(0,owner);
    @(negedge clk); host_ack_valid=1; host_ack_identity=owner; tick;
    check(fault && !visible_valid,"host ACK cannot retire internal SIMD");
    @(negedge clk); clear_inputs; recover;
    testcase=21; req_internal_SIMD=0; send(0,owner);
    @(negedge clk); simd_ack_retire_valid=1; simd_ack_retire_identity=owner; tick;
    check(fault && !visible_valid,"SIMD ACK cannot retire host origin");
    @(negedge clk); clear_inputs; recover;
    // Reset at each retained phase, including retirement waiting on downstream.
    for(i=0;i<9;i=i+1) begin testcase=30+i; prefix(i); recover; end
    // Reversed and duplicate completion: ready never grants faulting transition.
    testcase=40; prefix(2);
    @(negedge clk); parent_reverse_valid=1; parent_reverse_identity=owner; tick;
    check(fault && !consumer_ready,"reverse before consumer refused");
    @(negedge clk); clear_inputs; recover;
    testcase=41; prefix(3);
    @(negedge clk); consumer_valid=1; consumer_identity=owner; tick;
    check(fault && !child_reverse_ready,"duplicate consumer refused");
    @(negedge clk); clear_inputs; recover;
    testcase=42; prefix(0);
    @(negedge clk); drain_rsp_valid=1; drain_rsp_identity=owner; tick;
    check(fault && !retire_valid,"unsolicited drain response refused");
    @(negedge clk); clear_inputs; recover;
    // Every reverse completion port retains and matches the complete owner.
    for(i=0;i<3;i=i+1) begin
      testcase=43+i; prefix(3+i);
      @(negedge clk);
      case(i)
        0:begin child_reverse_valid=1; child_reverse_identity=owner^55'd512; end
        1:begin parent_reverse_valid=1; parent_reverse_identity=owner^55'd1; end
        2:begin reverse_CDC_valid=1; reverse_CDC_identity=owner^(55'd1<<44); end
      endcase
      tick; check(fault && !drain_req_valid && dut.enabled.identity==owner,"reverse identity mutant refused");
      @(negedge clk); clear_inputs; recover;
    end
    // Every retained physical bit corrected and scrubbed while owner held ACK.
    testcase=50; prefix(0); repeat(4) tick;
    pristine=dut.enabled.protected_state;
    for(i=0;i<144;i=i+1) begin
      @(negedge clk); dut.enabled.protected_state=pristine^(144'd1<<i);
      #1; check(!fault && dut.enabled.identity==owner,"single-bit ECC owner recovery");
      tick; check(dut.enabled.protected_state==pristine,"single-bit ECC scrub");
    end
    @(negedge clk); dut.enabled.protected_state=pristine^144'd3;
    #1; check(fault && quarantine && !host_ack_ready && !req_ready,"double-bit ECC fail closed");
    tick; check(dut.enabled.protected_state==(pristine^144'd3),"UE never guesses corrected owner");
    @(negedge clk); rst_n=0; tick;
    check(fault && quarantine,"runtime reset cannot erase uncorrectable identity");
    cold_boot;
    testcase=60;
    check(!off_req && !off_visible && !off_drain && !off_retire && !off_fault && !off_quarantine,"default-off outputs");
    // Reserved NC6 namespace client6 is not an invented directory client.
    @(negedge clk); req_valid=1; req_identity={7'd1,3'd6,32'd1,4'd0,9'd0}; tick;
    check(fault && !req_ready,"unmapped seventh client refused");
    $display("PASS_W6_LOCAL_COMPONENT checks=%0d accepted=%0d raw=71 protected=144 production_alldrain=0 physical=0",checks,accepted);
    $finish;
  end
endmodule
