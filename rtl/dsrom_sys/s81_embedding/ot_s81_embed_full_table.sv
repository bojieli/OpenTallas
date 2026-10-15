`timescale 1ns/1ps
// Complete released embedding vocabulary, exactly one global table copy.
// Four storage homes feed the ONE existing two-SRAM expander. Only the
// compiler-selected owner reads; fixed transfer slots never use ready/credits.
module ot_s81_embed_full_table #(parameter integer MUTANT=0)(
 input wire clk,rst_n,start,
 input wire [95:0] rom_clocks,
 input wire [16:0] token,
 input wire [13:0] vm_base,
 input wire [511:0] header,
 output wire busy,done,fault,vm_v,
 output wire [13:0] vm_row,
 output wire [511:0] vm_d,
 output wire hop_v,hop_last,
 output wire [511:0] hop_d
);
 reg issuing,command_fault;
 reg [1:0] owner_q;
 reg [23:0] source_word;
 reg [10:0] first_bank;
 reg [8:0] remaining,returned;
 wire launch=start && !busy && token<129280;
 wire [3:0] rv;
 wire [1095:0] rd;
 wire [10:0] selected_bank=(MUTANT==2 ? first_bank : source_word[23:13]) ^ (MUTANT==1 ? 11'd1 : 11'd0);
 for(genvar owner=0;owner<4;owner=owner+1) begin: quarters
  ot_s81_embed_rom_home #(.OWNER(owner)) storage(
   .clk(clk),.rst_n(rst_n),.clocks(rom_clocks[24*owner+:24]),
   .ce(issuing && owner_q==owner),.bank(selected_bank),.address(source_word[12:0]),
   .valid(rv[owner]),.data(rd[274*owner+:274]));
 end
 wire [273:0] payload=({274{rv[0]}}&rd[0+:274])|({274{rv[1]}}&rd[274+:274])|
                      ({274{rv[2]}}&rd[548+:274])|({274{rv[3]}}&rd[822+:274]);
 reg ov;
 reg [8:0] oi;
 reg [511:0] od;
 always @(posedge clk) begin
  if(!rst_n) begin issuing<=0;owner_q<=0;source_word<=0;first_bank<=0;remaining<=0;
   returned<=0;command_fault<=0;ov<=0;oi<=0;od<=0;end
  else begin
   if(start && (token>=129280 || busy)) command_fault<=1;
   if(launch) begin
    owner_q<=2'(token/32320);source_word<=24'(token%32320)*24'd320;
    first_bank<=11'((24'(token%32320)*24'd320)>>13);remaining<=320;returned<=0;issuing<=1;
   end else if(issuing) begin
    if(remaining==1) issuing<=0;
    else source_word<=source_word+1'b1;
    remaining<=remaining-1'b1;
   end
   ov<=|rv;oi<=returned;
   if(|rv) begin
    returned<=returned+1'b1;
    for(integer lane=0;lane<16;lane=lane+1) od[32*lane+:32]<={payload[16*lane+:16],16'b0};
   end
  end
 end
 wire ef;
 ot_s81_embed_expand #(.ROM_FIRST(15)) expand(
  .clk(clk),.rst_n(rst_n),.start(launch),.header(header),.vm_base(vm_base),
  .rom_v(ov),.rom_idx(oi),.rom_d(od),.busy(busy),.done(done),.fault(ef),
  .vm_v(vm_v),.vm_row(vm_row),.vm_d(vm_d),.hop_v(hop_v),.hop_last(hop_last),.hop_d(hop_d));
 assign fault=ef|command_fault;
endmodule
