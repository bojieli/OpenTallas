`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rd_v=0,wr_v=0;reg [14:0] rd_base_word=0,wr_word=0;
 reg [227:0]rd_owner=0,wr_owner=0;reg [63:0]wr_checks=0;
 wire rd_accept_v,rd_out_v,wr_accept_v,wr_ack_v,fault,corrected_command;
 wire [255:0]rd_checks;wire [227:0]rd_out_owner,wr_ack_owner;wire[14:0]wr_ack_word;
 integer cases=0;reg[255:0]low=0,high=0;
 ot_ds_vm_check_sidecar #(.ENABLE(1)) dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 task write_half(input [14:0]word,input [63:0]checks,input integer id);
 begin
  @(negedge clk);wr_v=1;wr_word=word;wr_checks=checks;wr_owner=id;#1;
  if(wr_accept_v!==1)$fatal(1,"VALID_WRITE_REFUSED");tick;
  @(negedge clk);wr_v=0;tick;if(wr_ack_v!==0)$fatal(1,"EARLY_PARITY_ACK1");
  tick;if(wr_ack_v!==0)$fatal(1,"EARLY_PARITY_ACK2");
  tick;if(wr_ack_v!==1||wr_ack_owner!==228'(id)||wr_ack_word!==word)$fatal(1,"PARITY_ACK_ID");
  tick;if(wr_ack_v!==0)$fatal(1,"DUPLICATE_PARITY_ACK");cases=cases+1;
 end endtask
 task read_four(input [14:0]word,input [255:0]checks,input integer id,input integer flip);
 begin
  @(negedge clk);rd_v=1;rd_base_word=word;rd_owner=id;#1;
  if(rd_accept_v!==1)$fatal(1,"VALID_READ_REFUSED");tick;
  if(flip) dut.rq[0][0]=~dut.rq[0][0];
  @(negedge clk);rd_v=0;
  repeat(3)begin tick;if(rd_out_v!==0)$fatal(1,"EARLY_PARITY_READ");end
  tick;if(rd_out_v!==1||rd_out_owner!==228'(id)||rd_checks!==checks)$fatal(1,"PARITY_READ_DATA_ID");
  if(flip&&corrected_command!==1)$fatal(1,"CORRECTED_COMMAND_NOT_REPORTED");
  tick;if(rd_out_v!==0)$fatal(1,"DUPLICATE_PARITY_READ");cases=cases+1;
 end endtask
 initial begin
  wr_v=1;rd_v=1;#1;if(wr_accept_v!==0||rd_accept_v!==0)$fatal(1,"RESET_ACCEPTANCE");
  repeat(3)tick;@(negedge clk);wr_v=0;rd_v=0;rst_n=1;repeat(6)tick;
  if(wr_ack_v!==0||rd_out_v!==0||fault!==0)$fatal(1,"RESET_STALE_OUTPUT");cases=cases+1;
  for(integer b=0;b<4;b=b+1)begin
   low[b*64+:64]=64'h123456789abcdef0+b;high[b*64+:64]=64'hfedcba9876543210+b;
   write_half(b,low[b*64+:64],100+b);write_half(2048+b,high[b*64+:64],200+b);
  end
  read_four(0,low,300,0);read_four(2048,high,301,0);
  // Updating one parity half must preserve paired group's other half.
  low[63:0]=64'h3f80000040400000;write_half(0,low[63:0],400);
  read_four(0,low,401,0);read_four(2048,high,402,0);
  for(integer b=0;b<4;b=b+1)write_half(32764+b,high[b*64+:64],500+b);
  read_four(32764,high,600,0);
  // Protected read address singlebit SEU before native access is corrected.
  read_four(0,low,700,1);
  // UE in accepted write control must block the actual macro write and ACK.
  @(negedge clk);wr_v=1;wr_word=0;wr_checks=64'hbad;wr_owner=800;tick;
  @(negedge clk);wr_v=0;tick;
  dut.wq[1][0]=~dut.wq[1][0];dut.wq[1][1]=~dut.wq[1][1];#1;
  if(fault!==1)$fatal(1,"UE_NOT_QUARANTINED");
  repeat(6)begin tick;if(wr_ack_v!==0||rd_out_v!==0)$fatal(1,"UE_NORMAL_RECEIPT");end
  if(dut.g_bank[0].g_pair[0].u_sram.word_read(0)!=={high[63:0],low[63:0]})$fatal(1,"UE_MACRO_WRITE_OCCURRED");
  if(fault!==1)$fatal(1,"FAULT_DEBT_ERASED");cases=cases+1;
  // End with quarantined owner; no reset/empty-based recovery is asserted.
  $display("PASS RAW_PARITY_SIDECAR cases=%0d macros=32 owner_quarantined=1",cases);$finish;
 end
 initial begin #100000;$fatal(1,"FINITE_TEST_EVENT_BOUND");end
endmodule
