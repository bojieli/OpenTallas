`timescale 1ns/1ps
// Own per-port publication root. The three payloads and four validity/credit
// bits retain exactly the original one native edge; no queue or epoch changes.
module ot_hcoll_port_publication545 #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire qp_push,qr_push,rx_valid,rx_credit,
 input wire[544:0]qp_data,qr_data,rx_data,
 output reg out_qp_push,out_qr_push,out_rx_valid,out_rx_credit,
 output reg[544:0]out_qp_data,out_qr_data,out_rx_data
);
 always @(posedge clk)begin
  out_qp_data<=qp_data;out_qr_data<=qr_data;out_rx_data<=rx_data;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin out_qp_push<=0;out_qr_push<=0;out_rx_valid<=0;out_rx_credit<=0;end
  else begin out_qp_push<=qp_push;out_qr_push<=qr_push;out_rx_valid<=rx_valid;out_rx_credit<=MUT?!rx_credit:rx_credit;end
endmodule
