`timescale 1ns/1ps
module tb_qwen_xdelivery_vector;
  localparam N=48, SW=40;
  reg clk=0;always #5 clk=~clk;
  reg rst_n=0,begin_v=0,fenced_clear=0;
  reg [N-1:0] issue_v=0,retire_v=0,seal_v=0;
  reg [N*SW-1:0] issue_seq=0,retire_seq=0;
  reg [N*16-1:0] issue_context={N{16'd3}},retire_context={N{16'd3}},seal_context={N{16'd3}};
  reg [N*32-1:0] issue_version={N{32'd5}},retire_version={N{32'd5}},seal_version={N{32'd5}};
  wire [N-1:0] issue_ready,retire_ready;
  wire drained,fault;
  integer q;
  ot_qwen_xdelivery_ack_vector #(.ENABLE(1),.N(N),.SEQ_W(SW)) dut(
    .clk(clk),.rst_n(rst_n),.begin_v(begin_v),.fenced_clear(fenced_clear),
    .begin_context(16'd3),.begin_version(32'd5),.participant_mask({N{1'b1}}),
    .issue_v(issue_v),.issue_ready(issue_ready),.issue_seq(issue_seq),
    .issue_context(issue_context),.issue_version(issue_version),
    .retire_v(retire_v),.retire_ready(retire_ready),.retire_seq(retire_seq),
    .retire_context(retire_context),.retire_version(retire_version),
    .seal_v(seal_v),.seal_context(seal_context),.seal_version(seal_version),
    .drained(drained),.fault(fault));
  task step;begin @(posedge clk);#1;@(negedge clk);end endtask
  initial begin
    step;rst_n=1;begin_v=1;step;begin_v=0;
    issue_v={N{1'b1}};#1;
    if(issue_ready!=={N{1'b1}}) $fatal(1,"parallel48 issue capacity lost");
    step;issue_seq={N{40'd1}};retire_v={N{1'b1}};#1;
    if(issue_ready!=={N{1'b1}} || retire_ready!=={N{1'b1}}) $fatal(1,"parallel simultaneous issue/retire lost");
    step;issue_v=0;retire_v=0;seal_v={N{1'b1}};step;seal_v=0;
    if(drained) $fatal(1,"vector seal waived outstanding requests");
    retire_seq={N{40'd1}};retire_v={N{1'b1}};step;retire_v=0;
    if(!drained || fault) $fatal(1,"parallel48 drain failed");
    begin_v=1;step;begin_v=0;issue_v={N{1'b1}};issue_seq=0;step;issue_v=0;
    retire_v={N{1'b1}};retire_seq=0;retire_version[17*32+:32]=4;step;retire_v=0;
    if(!fault || drained) $fatal(1,"one stale version escaped parallel cohort");
    // One query per coherent step may leave49 consumer stages outstanding.
    fenced_clear=1;step;fenced_clear=0;begin_v=1;step;begin_v=0;
    retire_v=0;retire_version={N{32'd5}};issue_v={N{1'b1}};
    for(q=0;q<49;q=q+1) begin
      issue_seq={N{40'(q)}};#1;
      if(issue_ready!=={N{1'b1}}) $fatal(1,"49-stage outstanding capacity lost");
      step;
    end
    issue_v=0;seal_v={N{1'b1}};step;seal_v=0;
    if(drained) $fatal(1,"49-stage pipeline prematurely drained");
    retire_v={N{1'b1}};
    for(q=0;q<49;q=q+1) begin
      retire_seq={N{40'(q)}};#1;
      if(retire_ready!=={N{1'b1}}) $fatal(1,"49-stage ordered retirement lost");
      step;
    end
    retire_v=0;
    if(!drained || fault) $fatal(1,"49-stage pipeline did not drain");
    // High bits are real identity, not a narrowed/truncated dictionary index.
    fenced_clear=1;step;fenced_clear=0;begin_v=1;step;begin_v=0;
    issue_v=0;retire_version={N{32'd5}};issue_seq=0;
    issue_seq[23*SW+32]=1;issue_v[23]=1;step;issue_v=0;
    if(!fault) $fatal(1,"query sequence high bit truncated");
    // Initialization is not an event sink: no simultaneous tuple may vanish.
    for(q=0;q<3;q=q+1) begin
      issue_v=0;retire_v=0;seal_v=0;fenced_clear=1;step;fenced_clear=0;
      begin_v=1;
      if(q==0) issue_v[0]=1;
      if(q==1) retire_v[0]=1;
      if(q==2) seal_v[0]=1;
      step;begin_v=0;issue_v=0;retire_v=0;seal_v=0;
      if(!fault || drained) $fatal(1,"vector begin overlap silently dropped event");
    end
    $display("PASS vector:48 simultaneous queries,49 outstanding stages, all-recipient drain, stale version and full40-bit identity");
    $finish;
  end
endmodule
