`timescale 1ns/1ps
`default_nettype none
// Same asynchronous assert and third-rising-edge release as ot_rst_relay_l.
// Half-cycle bank copies bound the 38-region source-native 76-load failure.
// Raw reset reaches exactly two face FFs; no data/valid calendar edge changes.
module ot_hidx_rst_tree_3e_f32 #(parameter integer REGIONS=38,MUT=0)(
 input wire clk,rst_n_in,output wire[REGIONS-1:0]rst_n);
 localparam integer BANKS=(REGIONS+15)/16;
 (*async_reg="true",keep="true",dont_touch="true"*)reg[1:0]sync_q;
 always@(posedge clk or negedge rst_n_in)
  if(!rst_n_in)sync_q<=0;else sync_q<={sync_q[0],1'b1};
 wire land_n=sync_q[1];
 (*keep="true",dont_touch="true"*)reg[BANKS-1:0]banks;
 if(MUT==0)begin:g_half
  always@(negedge clk or negedge land_n)
   if(!land_n)banks<=0;else banks<={BANKS{land_n}};
 end else begin:g_late
  always@(posedge clk or negedge land_n)
   if(!land_n)banks<=0;else banks<={BANKS{land_n}};
 end
 for(genvar i=0;i<REGIONS;i=i+1)begin:g_leaf
  wire rn=banks[i/16];(*keep="true",dont_touch="true"*)reg q;
  always@(posedge clk or negedge rn)if(!rn)q<=0;else q<=rn;
  assign rst_n[i]=q;
 end
endmodule
`default_nettype wire
