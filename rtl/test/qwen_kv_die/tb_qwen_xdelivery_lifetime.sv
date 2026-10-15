`timescale 1ns/1ps
module tb_qwen_xdelivery_lifetime;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, begin_v=0, issue_v=0, retire_v=0, seal_v=0, fenced_clear=0;
  reg [15:0] context_i=9, issue_context=9, retire_context=9, seal_context=9;
  reg [31:0] version_i=7, issue_version=7, retire_version=7, seal_version=7;
  reg [1:0] issue_id=0,retire_id=0,seal_id=0;
  reg [3:0] issue_seq=0,retire_seq=0;
  wire issue_ready,retire_ready,drained,bank_fault;
  ot_qwen_xdelivery_ack_bank #(.ENABLE(1),.N(4),.SEQ_W(4),.COUNT_W(2)) bank(
    .clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_context(context_i),
    .begin_version(version_i),.participant_mask(4'b1111),
    .issue_v(issue_v),.issue_ready(issue_ready),.issue_id(issue_id),.issue_seq(issue_seq),
    .issue_context(issue_context),.issue_version(issue_version),
    .retire_v(retire_v),.retire_ready(retire_ready),.retire_id(retire_id),.retire_seq(retire_seq),
    .retire_context(retire_context),.retire_version(retire_version),
    .seal_v(seal_v),.seal_id(seal_id),.seal_context(seal_context),.seal_version(seal_version),
    .fenced_clear(fenced_clear),.drained(drained),.fault(bank_fault));
  reg offer_v=0, offer_mode=0, acquire_ready=0, accept_v=0;
  reg [378:0] offer_ib=0,accept_ib=0;
  reg [1:0] accept_tile=0,accept_context=0;
  reg [31:0] accept_version=0;
  reg [1:0] bank_drained=0;
  reg source_output_drained=0,release_ready=0,transport_flush_ack=0;
  wire offer_ready,acquire_v,dispatch_v,release_v,flush_req,ctrl_fault,banks_begin;
  wire [378:0] held_ib; wire held_mode; wire [1:0] held_context; wire [31:0] held_version;
  ot_qwen_xdelivery_lifetime_ctrl #(.ENABLE(1),.TILES(4),.BANKS(2),.TOKEN_W(2)) ctrl(
    .clk(clk),.rst_n(rst_n),.offer_v(offer_v),.offer_ready(offer_ready),
    .offer_ib(offer_ib),.offer_mode(offer_mode),.offer_participants(4'b1111),
    .acquire_v(acquire_v),.acquire_ready(acquire_ready),.acquire_version(32'd71),
    .held_ib(held_ib),.held_mode(held_mode),.held_context(held_context),.held_version(held_version),
    .dispatch_v(dispatch_v),.accept_v(accept_v),.accept_tile(accept_tile),
    .accept_context(accept_context),.accept_version(accept_version),.accept_ib(accept_ib),
    .banks_begin(banks_begin),.bank_drained(bank_drained),.source_output_drained(source_output_drained),
    .release_v(release_v),.release_ready(release_ready),.flush_req(flush_req),
    .transport_flush_ack(transport_flush_ack),.fault(ctrl_fault));
  task step; begin @(posedge clk); #1; @(negedge clk); end endtask
  task reset_all; begin rst_n=0; step; rst_n=1; step; end endtask
  integer op,j;
  initial begin
    reset_all;
    if(!flush_req || offer_ready) $fatal(1,"reset opened before transport fence");
    transport_flush_ack=1; step; transport_flush_ack=0;
    for(op=0;op<12;op=op+1) begin
      offer_ib=379'h123+op; offer_mode=op%2; offer_v=1; step; offer_v=0;
      if(!acquire_v || dispatch_v) $fatal(1,"dispatch before VM reservation");
      offer_ib=379'hdead; offer_mode=!held_mode; step;
      if(held_ib!==379'h123+op || held_context!==op%4) $fatal(1,"offered IB replaced held operation");
      acquire_ready=1; step; acquire_ready=0;
      accept_context=held_context; accept_version=held_version; accept_ib=held_ib;
      for(j=0;j<4;j=j+1) begin accept_tile=j;accept_v=1;step; end
      accept_v=0;step;
      bank_drained=2'b11;source_output_drained=0;step;
      if(release_v) $fatal(1,"release before source quiescence");
      source_output_drained=1;bank_drained=2'b01;step;
      if(release_v) $fatal(1,"release before every recipient bank");
      bank_drained=2'b11;step;
      if(!release_v || ctrl_fault) $fatal(1,"complete operation failed to release");
      release_ready=1;step;release_ready=0;bank_drained=0;source_output_drained=0;
      if(op%4==3) begin
        if(!flush_req || offer_ready) $fatal(1,"context wrap reopened without fence");
        repeat(3) step;
        transport_flush_ack=1;step;transport_flush_ack=0;
      end
    end
    offer_v=1;offer_ib=379'h789;step;offer_v=0;
    acquire_ready=1;step;acquire_ready=0;
    accept_tile=0;accept_context=held_context+1'b1;accept_version=held_version;
    accept_ib=held_ib;accept_v=1;step;accept_v=0;
    if(!ctrl_fault) $fatal(1,"late context acceptance joined new operation");
    reset_all;transport_flush_ack=1;step;transport_flush_ack=0;
    offer_v=1;offer_ib=379'h789;step;offer_v=0;
    acquire_ready=1;step;acquire_ready=0;
    accept_tile=0;accept_context=held_context;accept_version=held_version;
    accept_ib=379'hbad;accept_v=1;step;accept_v=0;
    if(!ctrl_fault) $fatal(1,"offered IB substituted for actually accepted IB");
    // Actual issue/retire ordering: captures can arrive while consumer remains live.
    begin_v=1;step;begin_v=0;
    issue_v=1;issue_seq=0;step;issue_seq=1;step;issue_seq=2;step;
    issue_seq=3;#1;if(issue_ready) $fatal(1,"counter overflow accepted");step;
    if(bank_fault) $fatal(1,"ordinary backpressure faulted");
    issue_v=0;seal_v=1;seal_id=0;step;seal_v=0;
    for(j=1;j<4;j=j+1) begin seal_id=j;seal_v=1;step;end seal_v=0;
    if(drained) $fatal(1,"seal waived outstanding consumer requests");
    retire_v=1;retire_seq=0;step;retire_seq=1;step;retire_seq=2;step;retire_v=0;
    if(!drained || bank_fault) $fatal(1,"ordered drain failed");
    // A late ACK for an old VM version must fail closed, even with same token.
    begin_v=1;version_i=8;step;begin_v=0;
    issue_version=8;issue_seq=0;issue_v=1;step;issue_v=0;
    retire_version=7;retire_seq=0;retire_v=1;step;retire_v=0;
    if(!bank_fault || drained) $fatal(1,"late version ACK retired new request");
    fenced_clear=1;step;fenced_clear=0;
    if(bank_fault || drained) $fatal(1,"fenced clear failed");
    for(j=0;j<3;j=j+1) begin
      issue_v=0;retire_v=0;seal_v=0;fenced_clear=1;step;fenced_clear=0;
      begin_v=1;issue_v=(j==0);retire_v=(j==1);seal_v=(j==2);
      step;begin_v=0;issue_v=0;retire_v=0;seal_v=0;
      if(!bank_fault || drained) $fatal(1,"scalar begin overlap silently dropped event");
    end
    $display("PASS lifetime: 12 held operations, 3 context wraps, backpressure, consumer drain, late ACK");
    $finish;
  end
endmodule
