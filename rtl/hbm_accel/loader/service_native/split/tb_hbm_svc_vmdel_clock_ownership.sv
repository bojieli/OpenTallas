`timescale 1ns/1ps
module tb_hbm_svc_vmdel_clock_ownership;
 reg [7:0] clk_lane=0;
 reg rst_n=1,begin_v=0; reg [15:0] begin_epoch=0;
 wire [15:0] own; wire [127:0] epoch;
 ot_hbm_svc_static_vm_delivery_split_native dut(
  .clk_lane(clk_lane),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(1'b0),.begin_epoch(begin_epoch),
  .fill_v(32'b0),.fill_bank(32'b0),.fill_slot(192'b0),.fill_epoch(512'b0),.fill_data(8192'b0),
  .start(1'b0),.start_bank(1'b0),.start_epoch(16'b0),.start_base_sector(16'b0));
 genvar g;generate for(g=0;g<8;g=g+1)begin:observe
  assign own[g*2+:2]=dut.g_bank[g].u_lane.owned;
  assign epoch[g*16+:16]=dut.g_bank[g].u_lane.epoch0;
 end endgenerate
 integer b,k,checks=0;
 initial begin
  for(b=0;b<8;b=b+1)begin
   rst_n=0;begin_v=0;clk_lane=0;#2;rst_n=1;#2;
   // v3 lanes capture begin in a pin register: two owned pulses (capture, then state update)
   begin_v=1;begin_epoch=16'h1300+b;#2;repeat(2) begin clk_lane=8'b1<<b;#2;clk_lane=0;#2; end
   for(k=0;k<8;k=k+1)begin
    if(own[k*2+:2] !== (k==b?2'b01:2'b00))$fatal(1,"clock owner b=%0d k=%0d owned=%b",b,k,own[k*2+:2]);
    if(epoch[k*16+:16] !== (k==b?begin_epoch:16'b0))$fatal(1,"clock epoch b=%0d k=%0d",b,k);
    checks=checks+2;
   end
  end
  $display("DELIVERY_CLOCK_OWNERSHIP PASS checks=%0d",checks);$finish;
 end
endmodule
