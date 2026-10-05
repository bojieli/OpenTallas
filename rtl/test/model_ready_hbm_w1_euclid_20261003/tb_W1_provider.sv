`timescale 1ps/1fs
module tb_W1_provider;
 import ot_hbm_r14_pkg::*;
 reg clk=0,rst_n=0;always #500 clk=~clk;
 reg req_v=0,owned_r=0,credit_v=0,credit_we=0;request_t req;identity_t credit_id;
 reg [11:0] credit_tag=0;reg [4:0] credit_beat=0;
 wire req_r,cmd_v,cmd_r,owned_v,owned_we,owned_credit,credit_r,fault,backing_fault;
 command_t cmd;owned_t owned;wire [31:0] rsp_v,rsp_r,commit_v,commit_r;
 wire [511:0] rsp_tag;wire [159:0] rsp_beat;wire [8191:0] rsp_data;wire [63:0] commit_slot,cycle;
 wire [2:0] residents;wire [15:0] live_tags;
 wire off_req_r,off_cmd_v,off_owned_v,off_owned_we,off_owned_credit,off_credit_r,off_fault;
 wire [31:0] off_rsp_r,off_commit_r;wire [63:0] off_cycle;wire [2:0] off_residents;wire [15:0] off_tags;
 command_t off_cmd;owned_t off_owned;
 ot_hbm_causal_command_provider #(.ENABLE(0)) disabled(
 .clk(clk),.rst_n(rst_n),.req_v(1'b1),.req_r(off_req_r),.req(req),.cmd_v(off_cmd_v),.cmd_r(1'b1),.cmd(off_cmd),
 .rsp_v(32'hffffffff),.rsp_r(off_rsp_r),.rsp_tag({512{1'b1}}),.rsp_beat({160{1'b1}}),.rsp_data({8192{1'b1}}),
 .commit_v(32'hffffffff),.commit_r(off_commit_r),.commit_slot({64{1'b1}}),
 .owned_v(off_owned_v),.owned_r(1'b1),.owned_we(off_owned_we),.owned_credit(off_owned_credit),.owned(off_owned),
 .credit_v(1'b1),.credit_we(1'b1),.credit_r(off_credit_r),.credit_id(credit_id),.credit_tag(12'hfff),.credit_beat(5'h1f),
 .fault(off_fault),.cycle(off_cycle),.WRresidents(off_residents),.live_tags(off_tags));
 ot_hbm_causal_command_provider #(.ENABLE(1)) enabled(
 .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_r(req_r),.req(req),.cmd_v(cmd_v),.cmd_r(cmd_r),.cmd(cmd),
 .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
 .commit_v(commit_v),.commit_r(commit_r),.commit_slot(commit_slot),
 .owned_v(owned_v),.owned_r(owned_r),.owned_we(owned_we),.owned_credit(owned_credit),.owned(owned),
 .credit_v(credit_v),.credit_we(credit_we),.credit_r(credit_r),.credit_id(credit_id),.credit_tag(credit_tag),.credit_beat(credit_beat),
 .fault(fault),.cycle(cycle),.WRresidents(residents),.live_tags(live_tags));
 // Original backing fixture, finite test payload; no production PHY claim.
 ot_hbm_r14_backing_fixture #(.WORDS(8)) backing(.clk(clk),.rst_n(rst_n),.cyc(cycle),
 .cv(cmd_v),.cr(cmd_r),.cmd(cmd),.rv(rsp_v),.rr(rsp_r),.rtag(rsp_tag),.rbeat(rsp_beat),.rdata(rsp_data),
 .wv(commit_v),.wr(commit_r),.wslot(commit_slot),.mutant(4'b0),.fault(backing_fault));
 integer off_checks=0,accepts=0,commits=0,write_columns=0,read_columns=0,owned_results=0,reverse_accepts=0;
 always @(negedge clk)begin
  if ({off_req_r,off_cmd_v,off_cmd,off_rsp_r,off_commit_r,off_owned_v,off_owned_we,off_owned_credit,off_owned,off_credit_r,off_fault,off_cycle,off_residents,off_tags} !== '0)
   $fatal(1,"FAIL_DEFAULT_OFF_FALSE_READY_OR_ACK");
  off_checks=off_checks+1;
 end
 always @(posedge clk)if(rst_n)begin
  if(fault||backing_fault)$fatal(1,"FAIL_ENABLED_PROVIDER_FAULT");
  if(req_v&&req_r)accepts=accepts+1;
  if(|(commit_v&commit_r))commits=commits+1;
  if(cmd_v&&cmd_r&&cmd.op==WR)write_columns=write_columns+1;
  if(cmd_v&&cmd_r&&cmd.op==RD)read_columns=read_columns+1;
  if(owned_v&&owned_r)owned_results=owned_results+1;
  if(credit_v&&credit_r)reverse_accepts=reverse_accepts+1;
  // Protocol assertion for two len1 same-row transactions, not a wall-time cap.
  if(cycle==512)$fatal(1,"FAIL_FINITE_TWO_TRANSACTION_PROGRESS");
 end
 task automatic send(input bit we);
  @(negedge clk);req.we=we;req_v=1;
  do @(posedge clk);while(!req_r);
  @(negedge clk);req_v=0;
 endtask
 task automatic take_owned(input bit we,input bit grant);
  owned_t held;
  wait(owned_v);@(negedge clk);held=owned;
  if(owned_we!==we||owned_credit!==grant||held.id!==req.id||held.beat!==0)$fatal(1,"FAIL_OWNED_ID_KIND");
  if(!grant&&held.data!==req.data)$fatal(1,"FAIL_OWNED_PAYLOAD");
  repeat(5)begin @(negedge clk);
   if(!owned_v||owned!==held||owned_we!==we||owned_credit!==grant)$fatal(1,"FAIL_OWNED_HOLD");
  end
  credit_id=held.id;credit_tag=held.physical_tag;credit_beat=held.beat;
  owned_r=1;@(negedge clk);owned_r=0;
 endtask
 initial begin
  req='0;credit_id='0;
  repeat(3)@(negedge clk);rst_n=1;
  req.id='{die:1'b0,stack:2'b0,sector:34'd4096,producer:64'd7,transport:32'd8,caller:16'd9,client:6'd1,irs_slot:5'd2,irs_serial:32'd3};
  req.len=1;req.data=256'h00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff;
  send(1);take_owned(1,0);
  if(residents!=1||commits!=1)$fatal(1,"FAIL_WRITE_VISIBLE_RESIDENCE");
  @(negedge clk);credit_we=1;credit_v=1;
  do @(posedge clk);while(!credit_r);
  @(negedge clk);credit_v=0;
  take_owned(0,1);
  if(residents!=0)$fatal(1,"FAIL_WRITE_CREDIT_RELEASE");
  send(0);take_owned(0,0);
  repeat(5)@(negedge clk);
  if(accepts!=2||commits!=1||write_columns!=1||read_columns!=1||owned_results!=3||reverse_accepts!=1||off_checks<10||live_tags!=0)
   $fatal(1,"FAIL_EXACT_HANDSHAKE_COUNTS");
  $display("PASS_W1_TWO_TRANSACTIONS accepts=%0d commits=%0d WR=%0d RD=%0d owned=%0d reverse=%0d off_checks=%0d cycle=%0d",accepts,commits,write_columns,read_columns,owned_results,reverse_accepts,off_checks,cycle);$finish;
 end
endmodule
