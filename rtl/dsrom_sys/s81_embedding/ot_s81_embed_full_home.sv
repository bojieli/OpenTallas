`timescale 1ns/1ps
// One full vocab-quarter storage home; four homes cover every released token.
// Two adjacent historical4096-word logical banks pack into each8192-word ROM.
// The final physical bank is half full; no row crossing is rejected or wrapped.
module ot_s81_embed_full_home #(
 parameter integer OWNER=0, TREE_LEVELS=6, MUTANT=0
)(
 input wire clk,rst_n,start,
 input wire [23:0] rom_clocks,
 input wire [16:0] token,
 input wire [13:0] vm_base,
 input wire [511:0] header,
 output wire busy,done,fault,vm_v,
 output wire [13:0] vm_row,
 output wire [511:0] vm_d,
 output wire hop_v,hop_last,
 output wire [511:0] hop_d
);
 localparam integer FIRST_SAMPLE=3+2*TREE_LEVELS;
 reg issuing,command_fault;
 reg [23:0] source_word;
 reg [8:0] remaining;
 reg [10:0] first_bank;
 wire legal=token<129280 && token/32320==OWNER;
 wire launch=start && !busy && legal;
 wire rv;
 wire [273:0] rd;
 reg ov;
 reg [8:0] oi;
 reg [511:0] od;
 reg [8:0] returned;
 wire [10:0] selected_bank=(MUTANT==2 ? first_bank : source_word[23:13]) ^ (MUTANT==1 ? 11'd1 : 11'd0);
 ot_s81_embed_rom_home #(.OWNER(OWNER),.SHARD_LEVELS(TREE_LEVELS-1)) fabric(
  .clk(clk),.clocks(rom_clocks),.rst_n(rst_n),.ce(issuing),.bank(selected_bank),.address(source_word[12:0]),.valid(rv),.data(rd));
 always @(posedge clk) begin
  if(!rst_n) begin issuing<=0;source_word<=0;remaining<=0;first_bank<=0;returned<=0;ov<=0;oi<=0;od<=0;command_fault<=0;end
  else begin
   if(start && (!legal || busy)) command_fault<=1;
   if(launch) begin source_word<=24'(token%32320)*24'd320;remaining<=320;first_bank<=11'((24'(token%32320)*24'd320)>>13);issuing<=1;returned<=0;end
   else if(issuing) begin
    if(remaining==1) issuing<=0;
    else begin source_word<=source_word+1'b1;end
    remaining<=remaining-1'b1;
   end
   ov<=rv;oi<=returned;
   if(rv) begin
    returned<=returned+1'b1;
    for(integer lane=0;lane<16;lane=lane+1) od[32*lane+:32]<={rd[16*lane+:16],16'b0};
   end
  end
 end
 wire ef;
 ot_s81_embed_expand #(.ROM_FIRST(FIRST_SAMPLE)) expand(
  .clk(clk),.rst_n(rst_n),.start(launch),.header(header),.vm_base(vm_base),
  .rom_v(ov),.rom_idx(oi),.rom_d(od),.busy(busy),.done(done),.fault(ef),
  .vm_v(vm_v),.vm_row(vm_row),.vm_d(vm_d),.hop_v(hop_v),.hop_last(hop_last),.hop_d(hop_d));
 assign fault=ef|command_fault;
endmodule
