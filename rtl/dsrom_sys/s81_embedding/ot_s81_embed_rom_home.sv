`timescale 1ns/1ps
// Three equal physical HEAD-die partitions per logical vocabulary quarter.
// ce/bank/address and valid/data are static reserved transfer slots. Physical
// link pipelines must preserve these wires' exact compiled latency.
module ot_s81_embed_rom_home #(
 parameter integer OWNER=0, SHARD_LEVELS=5
)(
 input wire clk,rst_n,ce,
 input wire [23:0] clocks,
 input wire [10:0] bank,
 input wire [12:0] address,
 output reg valid,
 output reg [273:0] data
);
 reg ce_q;
 reg [10:0] bank_q;
 reg [12:0] address_q;
 wire [2:0] sv;
 wire [821:0] sd;
 for(genvar s=0;s<3;s=s+1) begin: head_die
  ot_s81_embed_rom_tree #(.OWNER(OWNER),.FIRST(421*s),.COUNT(421),.LEVEL(SHARD_LEVELS),.SHARD_FIRST(421*s)) shard(
   .clocks(clocks[8*s+:8]),.rst_n(rst_n),
   .ce(ce_q && bank_q>=421*s && bank_q<421*(s+1)),.bank(bank_q),.address(address_q),
   .valid(sv[s]),.data(sd[274*s+:274]));
 end
 always @(posedge clk) begin
  if(!rst_n) begin ce_q<=0;bank_q<=0;address_q<=0;valid<=0;data<=0;end
  else begin
   ce_q<=ce;bank_q<=bank;address_q<=address;
   valid<=|sv;
   data<=({274{sv[0]}}&sd[0+:274]) | ({274{sv[1]}}&sd[274+:274]) | ({274{sv[2]}}&sd[548+:274]);
  end
 end
endmodule
