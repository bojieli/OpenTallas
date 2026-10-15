`timescale 1ns/1ps
// Four-way registered address fanout and registered valid/data reduction.
// Every leaf is a real memory compiler ROM model. COUNT is the actual number
// of resident physical banks; padded tree positions instantiate no memory.
module ot_s81_embed_rom_tree #(
 parameter integer OWNER=0, FIRST=0, COUNT=421, LEVEL=5, SHARD_FIRST=0
)(
 input wire [7:0] clocks,
 input wire rst_n,ce,
 input wire [10:0] bank,
 input wire [12:0] address,
 output wire valid,
 output wire [273:0] data
);
 localparam integer CLOCK_GROUP=LEVEL<=3 ? 1+(FIRST-SHARD_FIRST)/64 : 0;
 wire clk=clocks[CLOCK_GROUP];
 generate if(LEVEL==0) begin: leaf
  reg v;
  wire [273:0] q;
  ot_rom_8192x274_m8 #(.INSTANCE($sformatf("s81_embed_o%0d_b%0d",OWNER,FIRST))) rom(
    .clk(clk),.ce_in(ce),.addr_in(address),.rd_out(q));
  always @(posedge clk) begin if(!rst_n) v<=0; else v<=ce; end
  assign valid=v; assign data=q;
 end else begin: branch
  localparam integer SPAN=4**(LEVEL-1);
  reg ce_q;
  reg [10:0] bank_q;
  reg [12:0] address_q;
  wire [3:0] cv;
  wire [1095:0] cd;
  reg v;
  reg [273:0] q;
  for(genvar child=0;child<4;child=child+1) begin: children
   localparam integer CHILD_FIRST=FIRST+child*SPAN;
   localparam integer REMAIN=COUNT-child*SPAN;
   if(REMAIN>0) begin: resident
    ot_s81_embed_rom_tree #(.OWNER(OWNER),.FIRST(CHILD_FIRST),.COUNT(REMAIN<SPAN?REMAIN:SPAN),.LEVEL(LEVEL-1),.SHARD_FIRST(SHARD_FIRST)) sub(
     .clocks(clocks),.rst_n(rst_n),.ce(ce_q && bank_q>=CHILD_FIRST && bank_q<CHILD_FIRST+(REMAIN<SPAN?REMAIN:SPAN)),
     .bank(bank_q),.address(address_q),.valid(cv[child]),.data(cd[274*child+:274]));
   end else begin: empty
    assign cv[child]=0; assign cd[274*child+:274]=0;
   end
  end
  always @(posedge clk) begin
   if(!rst_n) begin ce_q<=0;bank_q<=0;address_q<=0;v<=0;q<=0;end
   else begin
    ce_q<=ce;bank_q<=bank;address_q<=address;
    v<=|cv;
    q<=({274{cv[0]}}&cd[0+:274]) | ({274{cv[1]}}&cd[274+:274]) |
       ({274{cv[2]}}&cd[548+:274]) | ({274{cv[3]}}&cd[822+:274]);
   end
  end
  assign valid=v;assign data=q;
 end endgenerate
endmodule
