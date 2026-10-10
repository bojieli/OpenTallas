`timescale 1ns/1ps
// 64KiB shared memory, 1024 aligned 64-byte beats. One finite transaction;
// read/write collision serialized. No address wrapping or implicit lane gather.
// CAP2 = 1 (opt-in, 1.2 GHz SS): the macro's rd_out (SS clk->Q ~700 ps) is captured two edges after the
// read, under the multicycle constraint rtl/gpu/ot_gpu_scratch_service_cap2.sdc (the read port takes no new
// address while the read is pending, so rd_out holds); a read completes one cycle later, writes unchanged.
module ot_gpu_scratch_service_m #(parameter integer CAP2 = 0) (
 input wire clk,rst_n,valid,write,
 output wire ready,
 input wire [9:0] addr, input wire [511:0] wdata,
 output reg done, input wire done_ready,
 output reg [511:0] rdata
);
 reg pending, pending2;
 wire [511:0] raw;
 assign ready=rst_n && !pending && !pending2 && !done;
 wire go=valid && ready;
 genvar b;
 generate for(b=0;b<2;b=b+1) begin:g_bank
  ot_sram_1r1w_1024x256_m2_r2c2 u_sram (
   .clk(clk),.r_ce_in(go && !write),.r_addr_in(addr),.rd_out(raw[b*256+:256]),
   .w_ce_in(go && write),.w_addr_in(addr),.wd_in(wdata[b*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end endgenerate
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin pending<=0;pending2<=0;done<=0;end
  else begin
   pending<=go && !write;
   pending2<=(CAP2!=0) && pending;
   if((CAP2==0) ? pending : pending2) begin rdata<=raw;done<=1;end
   else if(go && write) begin rdata<=0;done<=1;end
   else if(done && done_ready) done<=0;
  end
 end
endmodule
