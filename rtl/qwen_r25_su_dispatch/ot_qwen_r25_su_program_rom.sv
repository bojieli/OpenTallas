`timescale 1ns/1ps
// Immutable native program payloads, one independent bank per real quarter.
// Metadata {valid1, quarters4, window1, row0_20, rows16}. No ROM ECC.
// Held response address is mutable and protected; provider cannot accept a
// second address until the finite response seat is released or replaced.
module ot_qwen_r25_su_program_rom #(
 parameter integer ENABLE=0,
 parameter Q0="",Q1="",Q2="",Q3="",META=""
)(input wire clk,rst_n,input wire rom_v,output wire rom_rdy,
 input wire [11:0] rom_pc,output wire rom_out_v,input wire rom_out_rdy,
 output wire [11:0] rom_out_pc,output wire [2759:0] rom_words,
 output wire [3:0] rom_quarters,output wire rom_valid,rom_window,
 output wire [19:0] rom_row0,output wire [15:0] rom_rows,output wire fault);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:disabled
  assign rom_rdy=0;assign rom_out_v=0;assign rom_out_pc=0;assign rom_words=0;
  assign rom_quarters=0;assign rom_valid=0;assign rom_window=0;
  assign rom_row0=0;assign rom_rows=0;assign fault=0;
 end else begin:enabled
  reg [689:0] bank0[0:4095],bank1[0:4095],bank2[0:4095],bank3[0:4095];
  reg [41:0] metadata[0:4095];reg [71:0] address_seat;
  wire [65:0] decoded=decode64(address_seat);
  wire [11:0] pc=decoded[11:0];wire resident=decoded[12];
  assign fault=decoded[65];assign rom_out_v=resident&&!fault;
  assign rom_rdy=!fault&&(!resident||rom_out_rdy);
  assign rom_out_pc=pc;
  assign rom_words={bank3[pc],bank2[pc],bank1[pc],bank0[pc]};
  assign {rom_valid,rom_quarters,rom_window,rom_row0,rom_rows}=metadata[pc];
  integer i;
  initial begin
   for(i=0;i<4096;i=i+1)begin
    bank0[i]=0;bank1[i]=0;bank2[i]=0;bank3[i]=0;metadata[i]=0;
   end
   if(Q0!="")$readmemh(Q0,bank0);if(Q1!="")$readmemh(Q1,bank1);
   if(Q2!="")$readmemh(Q2,bank2);if(Q3!="")$readmemh(Q3,bank3);
   if(META!="")$readmemh(META,metadata);
  end
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)address_seat<=encode64(0);
   else if(rom_v&&rom_rdy)address_seat<=encode64({51'd0,1'b1,rom_pc});
   else if(rom_out_v&&rom_out_rdy)address_seat<=encode64({51'd0,1'b0,pc});
  end
 end endgenerate
endmodule
