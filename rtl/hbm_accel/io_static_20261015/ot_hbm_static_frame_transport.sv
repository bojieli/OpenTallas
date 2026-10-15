`timescale 1ns/1ps
`default_nettype none
// Digital boundary only. Transports endpoint valid as an actual in-band bit;
// an idle reservation carries valid=0, never an invented received publication.
// tx_start/rx_start and tx_slot_v are compiler-assigned. No ready/backpressure.
// RX epoch must account for gearbox TX registers and all actual PHY/FEC ages.
// No integrated FEC/endpoint, synthesis or physical qualification is implied.
module ot_hbm_static_frame_transport(
 input wire clk,rst_n,tx_start,rx_start,
 input wire tx_slot_v,input wire endpoint_tx_v,
 input wire [611:0] endpoint_tx_frame,
 output wire expected_tx_slot,
 output wire transport_tx_v,output wire [486:0] transport_tx_word,
 input wire transport_rx_v,input wire [486:0] transport_rx_word,
 output reg endpoint_rx_v,output reg [611:0] endpoint_rx_frame,
 output wire fault
);
 wire [612:0] recovered;
 wire recovered_slot,tx_fault,rx_fault;
 ot_hbm_static_gearbox_tx #(.F(613),.W(487)) u_tx(
 .clk(clk),.rst_n(rst_n),.start(tx_start),.frame_v(tx_slot_v),
 .frame({endpoint_tx_v,endpoint_tx_frame}),.expected_frame(expected_tx_slot),
 .word_v(transport_tx_v),.word(transport_tx_word),.fault(tx_fault));
 ot_hbm_static_gearbox_rx #(.F(613),.W(487)) u_rx(
 .clk(clk),.rst_n(rst_n),.start(rx_start),.word_v(transport_rx_v),
 .word(transport_rx_word),.frame_v(recovered_slot),.frame(recovered),.fault(rx_fault));
 always @(posedge clk) endpoint_rx_frame<=recovered[611:0];
 always @(posedge clk or negedge rst_n)
 if(!rst_n)endpoint_rx_v<=0;
 else if(rx_start)endpoint_rx_v<=0;
 else endpoint_rx_v<=recovered_slot && recovered[612];
 assign fault=tx_fault|rx_fault;
endmodule
`default_nettype wire
