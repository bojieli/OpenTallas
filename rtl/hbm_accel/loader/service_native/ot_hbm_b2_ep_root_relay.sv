`timescale 1ns/1ps
`default_nettype none
// ep_S1 <-> NW hub traffic passes through the root neighbour. Data has one
// registered stage; only valid/status and command strobes reset. No ready path.
module ot_hbm_b2_ep_root_relay #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire[614:0]rx_i,input wire[631:0]tx_i,
 output wire[614:0]rx_o,output wire[631:0]tx_o
);
 reg[614:0]rx_q;reg[631:0]tx_q;
 localparam [631:0] TX_CONTROL=(632'd1<<612)|(632'd1<<613)|(632'd1<<622)|(632'd1<<624);
 always @(posedge clk)begin
  rx_q[611:0]<=rx_i[611:0];
  if(!rst_n)rx_q[614:612]<=0;else rx_q[614:612]<=rx_i[614:612];
 end
 genvar b;
 generate for(b=0;b<632;b=b+1)begin:g_tx
  if(TX_CONTROL[b])begin:g_control
   always @(posedge clk)if(!rst_n)tx_q[b]<=0;else tx_q[b]<=tx_i[b];
  end else begin:g_payload
   always @(posedge clk)tx_q[b]<=tx_i[b];
  end
 end endgenerate
 reg[631:0]tx_late;
 always @(posedge clk)tx_late<=tx_q;
 assign rx_o=rx_q^(MUT==1?615'd1:615'd0);
 assign tx_o=MUT==2?tx_late:tx_q;
endmodule
`default_nettype wire
