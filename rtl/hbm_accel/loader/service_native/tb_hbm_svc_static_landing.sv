`timescale 1ns/1ps
module tb_hbm_svc_static_landing;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,begin_v=0,begin_bank=0,start=0,start_bank=0;
 reg [15:0] begin_epoch=0,start_epoch=0;
 reg [31:0] fill_v=0,fill_bank=0;reg [191:0] fill_slot=0;
 reg [511:0] fill_epoch=0;reg [8191:0] fill_data=0;
 wire [1:0] block_ready;wire out_v,out_bank,busy,fault;wire [1:0] out_group;wire [5:0] out_slot;
 wire [15:0] out_epoch;wire [8191:0] out_data;
 ot_hbm_svc_static_landing #(.READ_GROUPS(1)) dut(.*);
 integer outputs=0,p,s,b;
 function [255:0] payload(input integer bank,pc,slot);
  payload={8{32'h13572468 ^ (bank<<24) ^ (pc<<12) ^ slot}};
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task open_bank(input integer bank);begin
  @(negedge clk);begin_v=1;begin_bank=bank;begin_epoch=100+bank;
  tick();@(negedge clk);begin_v=0;
 end endtask
 task fill(input integer bank,slot);begin
  @(negedge clk);fill_v='1;fill_bank={32{bank[0]}};
  for(integer i=0;i<32;i=i+1)begin
   fill_slot[i*6+:6]=slot;fill_epoch[i*16+:16]=100+bank;
   fill_data[i*256+:256]=payload(bank,i,slot);
  end
  tick();@(negedge clk);fill_v=0;
 end endtask
 task reset;begin
  @(negedge clk);rst_n=0;begin_v=0;fill_v=0;start=0;
  tick();@(negedge clk);rst_n=1;tick();
 end endtask
 always @(posedge clk)begin
  #2;
  if(out_v)begin
   if(out_epoch!==100+out_bank)$fatal(1,"epoch");
   for(integer i=0;i<32;i=i+1)
    if(out_data[i*256+:256]!==payload(out_bank,i,out_slot))$fatal(1,"payload pc=%0d slot=%0d",i,out_slot);
   outputs=outputs+1;
  end
 end
 initial begin
  reset();open_bank(0);open_bank(1);
  // Fill reverse order and alternate banks, proving address rather than FIFO storage.
  for(s=63;s>=0;s=s-1)begin fill(0,s);fill(1,63-s);end
  if(block_ready!==3||fault)$fatal(1,"complete blocks");
  for(b=0;b<2;b=b+1)begin
   @(negedge clk);start=1;start_bank=b;start_epoch=100+b;
   tick();@(negedge clk);start=0;
   repeat(63)tick();
   if(busy)$fatal(1,"drain length");
   tick();
  end
  if(outputs!=128||fault)$fatal(1,"throughput outputs=%0d fault=%0d",outputs,fault);
  // Refill the other bank at full PHY bandwidth while draining the first.
  reset();open_bank(0);open_bank(1);
  for(s=0;s<64;s=s+1)fill(0,s);
  @(negedge clk);start=1;start_bank=0;start_epoch=100;
  tick();@(negedge clk);start=0;
  for(s=0;s<64;s=s+1)begin
   fill_v='1;fill_bank='1;
   for(p=0;p<32;p=p+1)begin
    fill_slot[p*6+:6]=s;fill_epoch[p*16+:16]=101;
    fill_data[p*256+:256]=payload(1,p,s);
   end
   tick();@(negedge clk);
  end
  fill_v=0;
  if(!block_ready[1]||fault||busy||outputs!=192)$fatal(1,"overlap");
  // A consumed bank may be reused only after a new begin and complete refill.
  open_bank(0);if(block_ready[0])$fatal(1,"stale ready");
  fill(0,0);fill(0,0);if(!fault)$fatal(1,"duplicate not detected");
  reset();open_bank(0);
  @(negedge clk);fill_v=1;fill_epoch[15:0]=99;
  tick();@(negedge clk);fill_v=0;if(!fault)$fatal(1,"stale epoch not detected");
  reset();open_bank(0);
  @(negedge clk);start=1;start_epoch=100;start_bank=0;
  tick();@(negedge clk);start=0;
  if(!fault||out_v||busy)$fatal(1,"incomplete block was scheduled");
  $display("STATIC_LANDING PASS PCs=32 blocks=3 outputs=192 overlap=64 II=1 faults=duplicate,epoch,incomplete");$finish;
 end
endmodule
