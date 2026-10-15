`timescale 1ns/1ps
module tb_hbm_svc_static_vm_delivery;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,begin_v=0,begin_bank=0,start=0,start_bank=0;
 reg [15:0] begin_epoch=77,start_epoch=77,start_base_sector=16'h2800;
 reg [31:0] fill_v=0,fill_bank=0;reg [191:0] fill_slot=0;
 reg [511:0] fill_epoch=0;reg [8191:0] fill_data=0;
 wire [1:0] block_ready;wire [2247:0] dq;wire busy,fault;
 integer s,p,n,seen=0;
 ot_hbm_svc_static_vm_delivery dut(.*);
 function [255:0] payload(input integer pc,slot);
  payload={8{32'h17624611 ^ (pc<<12) ^ slot}};
 endfunction
 task tick;begin @(posedge clk);#2;end endtask
 task check_slot(input integer ordinal);begin
  for(integer b=0;b<8;b=b+1)begin
   if(dq[b*281+280]!==1 || dq[b*281+264+:16]!==16'h2800+ordinal*8+b ||
      dq[b*281+8+:256]!==payload((ordinal%4)*8+b,ordinal/4) || dq[b*281+:8]!==8'hff)
    $fatal(1,"VM delivery bank/group mismatch ordinal=%0d bank=%0d",ordinal,b);
  end
 end endtask
 initial begin
  tick();@(negedge clk);rst_n=1;begin_v=1;tick();@(negedge clk);begin_v=0;
  for(s=0;s<64;s=s+1)begin
   fill_v='1;
   for(p=0;p<32;p=p+1)begin
    fill_slot[p*6+:6]=s;fill_epoch[p*16+:16]=77;fill_data[p*256+:256]=payload(p,s);
   end
   tick();@(negedge clk);
  end
  fill_v=0;if(block_ready!==1||fault)$fatal(1,"fill");
  start=1;tick();check_slot(0);@(negedge clk);start=0;
  for(n=1;n<256;n=n+1)begin tick();check_slot(n);end
  if(busy||fault)$fatal(1,"256 cycle duration");
  tick();for(p=0;p<8;p=p+1)if(dq[p*281+280])$fatal(1,"extra slot");
  // Cross-sid blocks must fail without producing any delivery.
  @(negedge clk);start=1;start_base_sector=16'h3fe0;tick();
  if(!fault||busy)$fatal(1,"aperture crossing accepted");
  $display("STATIC_VM_DELIVERY PASS sectors=2048 slots=256 II=1 dq_bits=2248 aperture_fault=1");$finish;
 end
endmodule
