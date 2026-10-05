`timescale 1ns/1ps
module tb_a3_operand_bank_owner;
 reg clk=0, rst_n=0;
 always #5 clk=~clk;
 reg reserve_valid=0,reserve_bank=0,fill_valid=0,fill_bank=0;
 reg acquire_valid=0,acquire_bank=0,release_valid=0,release_bank=0,release_retain=0;
 reg cancel_valid=0,cancel_bank=0;
 reg [63:0] reserve_tag=0,fill_tag=0,acquire_tag=0,release_tag=0,cancel_tag=0;
 reg [9:0] reserve_words=0;
 wire reserve_ready,fill_ready,acquire_ready,release_ready,cancel_ready;
 wire [9:0] fill_index;
 wire [9:0] acquire_words;
 wire [1:0] ready_banks,active_banks;
 wire [3:0] bank_states;
 wire query_bank=0;
 wire [63:0] query_tag=0;
 wire [9:0] query_index=0;
 wire read_authorized;
 ot_a3_operand_bank_owner dut(.*);
 task tick; begin @(posedge clk); #1; end endtask
 task inputs_off; begin
  reserve_valid=0;fill_valid=0;acquire_valid=0;release_valid=0;cancel_valid=0;
 end endtask
 task reserve(input bit bank,input [63:0] id,input [9:0] words);
 begin
  @(negedge clk);inputs_off();reserve_bank=bank;reserve_tag=id;reserve_words=words;reserve_valid=1;
  #1;if(!reserve_ready)$fatal(1,"reservation refused");tick();
  @(negedge clk);reserve_valid=0;
 end endtask
 task fill(input bit bank,input [63:0] id,input integer words);
 integer i;
 begin
  for(i=0;i<words;i=i+1)begin
   @(negedge clk);inputs_off();fill_bank=bank;fill_tag=id;fill_valid=1;
   #1;if(!fill_ready || fill_index!==i)$fatal(1,"fill cursor or ready wrong");tick();
  end
  @(negedge clk);fill_valid=0;
 end endtask
 initial begin
  tick();@(negedge clk);rst_n=1;
  reserve(0,64'h1001,3);
  @(negedge clk);fill_valid=1;fill_tag=64'h1; #1;
  if(fill_ready)$fatal(1,"stale fill accepted");tick();
  @(negedge clk);inputs_off(); acquire_valid=1;acquire_tag=64'h1001;#1;
  if(acquire_ready)$fatal(1,"incomplete bank acquired");tick();
  fill(0,64'h1001,3);
  if(ready_banks!==2'b01)$fatal(1,"last write did not publish");
  @(negedge clk);acquire_valid=1;acquire_tag=64'h1001;#1;
  if(!acquire_ready)$fatal(1,"filled bank not available");tick();
  @(negedge clk);inputs_off();
  if(active_banks!==2'b01)$fatal(1,"acquire did not own bank");
  reserve(1,64'h2001,2);
  fill(1,64'h2001,2);
  if(active_banks!==2'b01 || ready_banks!==2'b10)$fatal(1,"opposite fill disturbed active bank");
  @(negedge clk);cancel_bank=0;cancel_tag=64'h1001;cancel_valid=1;
  reserve_bank=0;reserve_valid=1;reserve_words=3; #1;
  if(cancel_ready || reserve_ready)$fatal(1,"active bank can be overwritten");
  release_valid=1;release_bank=0;release_tag=64'hdead;#1;
  if(release_ready)$fatal(1,"stale release accepted");tick();
  @(negedge clk);inputs_off();release_valid=1;release_tag=64'h1001;release_retain=1;
  tick();@(negedge clk);inputs_off();
  if(ready_banks!==2'b11)$fatal(1,"reuse did not retain residency");
  // Cancellation takes precedence over acquisition and returns the bank free.
  acquire_valid=1;acquire_bank=0;acquire_tag=64'h1001;
  cancel_valid=1;cancel_bank=0;cancel_tag=64'h1001;#1;
  if(!cancel_ready || acquire_ready)$fatal(1,"cancel/acquire conflict");tick();
  @(negedge clk);inputs_off();
  reserve(0,64'h3001,2);
  @(negedge clk);fill_valid=1;fill_bank=0;fill_tag=64'h3001;
  cancel_valid=1;cancel_bank=0;cancel_tag=64'h3001;#1;
  if(fill_ready || !cancel_ready)$fatal(1,"cancel/fill conflict");tick();
  @(negedge clk);inputs_off();
  // Invalid lengths refuse rather than wrap a count into READY.
  reserve_valid=1;reserve_bank=0;reserve_words=0;#1;
  if(reserve_ready)$fatal(1,"zero length accepted");
  reserve_words=513;#1;if(reserve_ready)$fatal(1,"oversize accepted");
  inputs_off();reserve(0,64'h4001,512);fill(0,64'h4001,512);
  @(negedge clk);inputs_off();acquire_valid=1;acquire_tag=64'h4001;tick();
  @(negedge clk);inputs_off();release_valid=1;release_tag=64'h4001;release_retain=0;
  tick();@(negedge clk);inputs_off();
  if(bank_states[1:0]!==0)$fatal(1,"final release failed");
  rst_n=0;#1;
  if(bank_states!==0 || reserve_ready || fill_ready || acquire_ready)$fatal(1,"reset did not revoke credits");
  tick();@(negedge clk);rst_n=1;fill_valid=1;fill_tag=64'h4001;#1;
  if(fill_ready)$fatal(1,"old response survived reset");
  $display("PASS operand bank ownership, refill overlap, reuse, stale tags, cancellation, bounds and reset");
  $finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
