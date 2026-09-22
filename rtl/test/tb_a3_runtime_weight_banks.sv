`timescale 1ns/1ps
// Behavioral macro model follows the documented one-cycle single-port contract.
module fakeram_512x128(input wire clk, input wire [8:0] addr_in,
 input wire ce_in,we_in,input wire [127:0] wd_in,output reg [127:0] rd_out);
 reg [127:0] mem[0:511];
 always @(posedge clk) if(ce_in) begin
  if(we_in) mem[addr_in]<=wd_in; else rd_out<=mem[addr_in];
 end
endmodule
module tb_a3_runtime_weight_banks;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg reserve_valid=0,reserve_bank=0,fill_valid=0,fill_bank=0;
 reg acquire_valid=0,acquire_bank=0,release_valid=0,release_bank=0,release_retain=0;
 reg cancel_valid=0,cancel_bank=0,read_valid=0,read_bank=0,response_ready=0;
 reg [63:0] reserve_tag=0,fill_tag=0,acquire_tag=0,release_tag=0,cancel_tag=0,read_tag=0;
 reg [9:0] reserve_words=0,read_index=0;
 reg [127:0] fill_data=0;
 wire reserve_ready,fill_ready,acquire_ready,release_ready,cancel_ready,read_ready;
 wire response_valid,response_bank;
 wire [63:0] response_tag;
 wire [127:0] response_data;
 wire [1:0] ready_banks,active_banks;
 wire [9:0] acquire_words;
 integer i,overlaps=0;
 ot_a3_runtime_weight_banks dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 task off;begin reserve_valid=0;fill_valid=0;acquire_valid=0;release_valid=0;cancel_valid=0;read_valid=0;end endtask
 task reserve(input bit bank,input [63:0] tag,input [9:0] words);
 begin @(negedge clk);off();reserve_valid=1;reserve_bank=bank;reserve_tag=tag;reserve_words=words;
 #1;if(!reserve_ready)$fatal(1,"reserve");tick();@(negedge clk);off();end endtask
 task acquire(input bit bank,input [63:0] tag);
 begin @(negedge clk);off();acquire_valid=1;acquire_bank=bank;acquire_tag=tag;
 #1;if(!acquire_ready)$fatal(1,"acquire");tick();@(negedge clk);off();end endtask
 initial begin
 tick();@(negedge clk);rst_n=1;
 reserve(0,64'h100,4);
 for(i=0;i<4;i=i+1)begin
  @(negedge clk);fill_valid=1;fill_bank=0;fill_tag=64'h100;fill_data=128'h1000+128'(i);
  #1;if(!fill_ready)$fatal(1,"fill");tick();
 end
 @(negedge clk);off();acquire(0,64'h100);
 reserve(1,64'h200,4);
 // Opposite banks, deliberately DIFFERENT addresses: bank0 reverse, bank1 forward.
 response_ready=1;
 for(i=0;i<4;i=i+1)begin
  @(negedge clk);fill_valid=1;fill_bank=1;fill_tag=64'h200;fill_data=128'h2000+128'(i);
  read_valid=1;read_bank=0;read_tag=64'h100;read_index=10'(3-i);
  #1;if(!read_ready || !fill_ready)$fatal(1,"overlap not accepted");overlaps=overlaps+1;
  tick();if(!response_valid || response_data!==128'h1000+128'(3-i) || response_tag!==64'h100)
   $fatal(1,"overlap read corrupted");
 end
 // Response must hold under backpressure, and release cannot invalidate it.
 @(negedge clk);off();response_ready=0;release_valid=1;release_bank=0;release_tag=64'h100;
 read_valid=1;read_index=0;
 repeat(3)begin
  #1;if(read_ready || release_ready)$fatal(1,"outstanding response lost ownership");
  tick();if(!response_valid || response_data!==128'h1000)$fatal(1,"stalled data changed");
  @(negedge clk);
 end
 off();response_ready=1;tick();@(negedge clk);
 release_valid=1;release_tag=64'h100;#1;if(!release_ready)$fatal(1,"drained release blocked");
 tick();@(negedge clk);off();
 acquire(1,64'h200);
 // Confirm the overlapping writes landed at their OWN bank-local addresses.
 for(i=0;i<4;i=i+1)begin
  @(negedge clk);read_valid=1;read_bank=1;read_tag=64'h200;read_index=10'(i);
  #1;if(!read_ready)$fatal(1,"read");tick();
  if(response_data!==128'h2000+128'(i) || !response_valid || !response_bank)$fatal(1,"fill address corruption");
 end
 @(negedge clk);off();tick();@(negedge clk);
 read_valid=1;read_bank=1;read_tag=64'h100;read_index=0;
 #1;if(read_ready)$fatal(1,"stale read tag accepted");
 read_tag=64'h200;read_index=4;#1;if(read_ready)$fatal(1,"out of range read accepted");
 fill_valid=1;fill_bank=1;fill_tag=64'h200;#1;if(fill_ready)$fatal(1,"active overwrite accepted");
 off();read_valid=1;read_index=2;tick();@(negedge clk);off();response_ready=0;
 // A full-bank refill must not disturb a held response from the other bank.
 reserve(0,64'h300,512);
 for(i=0;i<512;i=i+1)begin
  @(negedge clk);fill_valid=1;fill_bank=0;fill_tag=64'h300;fill_data=128'h3000+128'(i);
  #1;if(!fill_ready)$fatal(1,"full bank fill refused");tick();
  if(!response_valid || response_data!==128'h2002)$fatal(1,"other-bank fill disturbed held response");
 end
 @(negedge clk);off();acquire(0,64'h300);
 response_ready=1;
 for(i=0;i<512;i=i+1)begin
  @(negedge clk);read_valid=1;read_bank=0;read_tag=64'h300;read_index=10'(511-i);
  #1;if(!read_ready)$fatal(1,"full bank read refused");tick();
  if(!response_valid || response_data!==128'h3000+128'(511-i))$fatal(1,"full bank address mismatch");
 end
 @(negedge clk);off();response_ready=0;
 rst_n=0;#1;if(response_valid || read_ready || fill_ready)$fatal(1,"reset left transaction live");
 tick();@(negedge clk);rst_n=1;read_valid=1;read_tag=64'h200;
 #1;if(read_ready)$fatal(1,"old bank readable after reset");
 if(overlaps!=4)$fatal(1,"overlap coverage missing");
 $display("PASS runtime weight banks: 4 concurrent read/write beats, 512-word fill/read, independent addresses, response backpressure, protected release, stale tags, bounds, reset");
 $finish;
 end
 initial begin #50000;$fatal(1,"timeout");end
endmodule
