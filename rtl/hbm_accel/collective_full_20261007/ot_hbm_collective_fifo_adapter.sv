`timescale 1ns/1ps
// 'empty' means no visible head; count includes unread SRAM and pending capture.
// Callers MUST use count==0, not empty, when proving transaction quiescence.
module ot_hbm_collective_fifo_adapter #(parameter integer ENABLE_SRAM=0,W=545,AW=6)(
 input wire clk,rst_n,push,input wire[W-1:0]din,input wire pop,
 output wire empty,output wire[W-1:0]dout,output wire ovf,output wire[AW:0]count);
 generate if(!ENABLE_SRAM)begin:g_legacy
  ot_ha2_fifo #(.W(W),.AW(AW)) u_fifo(.*);
 end else begin:g_sram
  initial if(W!=545||(AW!=6&&AW!=8))$fatal(1,"full TU packet SRAM shape mismatch");
  wire ready,valid;wire[8:0]occupancy;
  ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(1<<AW)) u_fifo(
   .clk(clk),.rst_n(rst_n),.push(push),.din(din),.ready(ready),.pop(pop),
   .valid(valid),.dout(dout),.fault(ovf),.count(occupancy));
  assign empty=!valid;assign count=occupancy[AW:0];
 end endgenerate
endmodule
