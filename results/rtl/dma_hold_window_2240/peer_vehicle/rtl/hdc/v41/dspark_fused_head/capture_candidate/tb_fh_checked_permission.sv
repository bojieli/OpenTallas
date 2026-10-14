`timescale 1ns/1ps
module tb_fh_checked_permission;
 import ot_dsrom_vm_pkg::*;
 reg fast_clk=0;always #5 fast_clk=~fast_clk;
 reg cold_n=0,request_accept=0,request_warm=1,checked_reply_capture=0,published_reply_v=0;
 reg [31:0] native_ordinal=32'hfedcba98;
 reg [46:0] request_owner=47'h456789abcde;
 reg [7:0] request_id=8'h73;
 reg [3:0] head_we=1;
 reg [95:0] head_addr=96'h000000000000000000000123;
 reg [63:0] head_mask=1;
 reg [2047:0] head_data=0;
 reg [REP_BITS-1:0] checked_reply=0;
 wire bounds_fault,endpoint_fault,request_checked_v,reply_checked_v,guard_busy,head_ack_v;
 wire [7:0] head_ack_id;wire [23:0] head_ack_word;wire [15:0] head_ack_mask;
 request_t captured_request,captured_request_check;
 reply_t captured_reply,captured_reply_check;
 ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1),.CHECK_PIPE(1)) dut(.*);
 task tick;begin @(posedge fast_clk);#1;end endtask
 task reset;begin
  @(negedge fast_clk);cold_n=0;request_accept=0;checked_reply_capture=0;published_reply_v=0;
  head_we=1;head_addr=96'h123;head_mask=1;request_warm=1;head_data=0;
  tick;tick;@(negedge fast_clk);cold_n=1;tick;
 end endtask
 task take;begin
  @(negedge fast_clk);request_accept=1;tick;
  @(negedge fast_clk);request_accept=0;
  if(request_checked_v||head_ack_v)$fatal(1,"early grant");
  repeat(5)tick;
  if(!request_checked_v||!guard_busy||captured_request!=~captured_request_check)$fatal(1,"missing checked capture");
 end endtask
 task reply(input reg wrong_owner,input reg wrong_ordinal);reg [46:0] owner;reg [31:0] ordinal;begin
  owner=captured_request.owner^(wrong_owner?47'h40000000000:0);
  ordinal=captured_request.ordinal^(wrong_ordinal?32'h80000000:0);
  @(negedge fast_clk);
  checked_reply={1'b1,ordinal,owner,2'b0,1024'b0,captured_request.we,captured_request.wa,captured_request.wm,1'b0};
  checked_reply_capture=1;published_reply_v=1;tick;
  @(negedge fast_clk);checked_reply_capture=0;
  if(head_ack_v)$fatal(1,"early visibility");
  repeat(4)begin tick;if(head_ack_v)$fatal(1,"grant before all checks");end
  tick;
 end endtask
 integer cases=0;
 initial begin
  reset;head_data[31:0]=32'h3f812345;head_data[2047:32]='x;take;
  if(captured_request.wd[543:512]!==32'h3f812345||captured_request.wd[2559:544]!==0)$fatal(1,"masked X normalization");
  reply(0,0);
  if(!head_ack_v||head_ack_id!=request_id||head_ack_word!=24'h123||head_ack_mask!=1)$fatal(1,"matching ACK missing");
  tick;if(head_ack_v)$fatal(1,"duplicate held ACK");repeat(6)tick;if(head_ack_v)$fatal(1,"repeated ACK");
  @(negedge fast_clk);published_reply_v=0;tick;if(guard_busy)$fatal(1,"slot not released");cases=cases+1;
  reset;request_warm=0;take;reply(0,0);if(head_ack_v||!reply_checked_v)$fatal(1,"ordinary write warm ACK");cases=cases+1;
  reset;take;reply(1,0);if(head_ack_v||!endpoint_fault||!guard_busy)$fatal(1,"full owner quarantine");cases=cases+1;
  reset;take;reply(0,1);if(head_ack_v||!endpoint_fault||!guard_busy)$fatal(1,"full ordinal quarantine");cases=cases+1;
  reset;take;@(negedge fast_clk);request_accept=1;tick;request_accept=0;
  if(!endpoint_fault||!guard_busy)$fatal(1,"held request overwrite not quarantined");cases=cases+1;
  reset;head_addr=96'h8000;tick;if(!bounds_fault||head_ack_v)$fatal(1,"address truncation");cases=cases+1;
  reset;take;reply(0,0);
  force dut.g_distributed_check.u_guard.g_request_bank[0].u_bank.check=32'h0;
  #1;if(head_ack_v||!endpoint_fault)$fatal(1,"late payload mirror ACK");tick;
  release dut.g_distributed_check.u_guard.g_request_bank[0].u_bank.check;
  tick;if(!endpoint_fault||head_ack_v)$fatal(1,"sticky bank quarantine lost");cases=cases+1;
  reset;take;reply(0,0);
  force dut.g_distributed_check.u_guard.u_check_reduce.local_check=17'b0;
  #1;if(head_ack_v||reply_checked_v)$fatal(1,"late reduction mirror ACK");
  release dut.g_distributed_check.u_guard.u_check_reduce.local_check;cases=cases+1;
  reset;take;reset;if(guard_busy||head_ack_v||request_checked_v||reply_checked_v)$fatal(1,"reset stale grant");cases=cases+1;
  $display("PASS CHECK_PIPE identity/quarantine/reset/maskedX cases=%0d",cases);$finish;
 end
endmodule
