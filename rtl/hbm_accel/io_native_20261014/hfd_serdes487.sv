`timescale 1ns/1ps
// Source-exact 487-bit HBM link gearbox to existing full KP4 SerDes digital
// layer. The high25 bits are declared zero extension, never another payload.
// PMA lanes/clocks are the only allowed behavioural analog boundary.
// One real pin capture at each core-facing payload face adds2 edges total.
module hfd_serdes487 #(parameter integer EMUT=0,DMUT=0,MUT_PAD=0)(
 input wire clk,rst_n,
 input wire [486:0] tx,
 output reg [486:0] rx,
 output wire [1:0] st,
 output wire [543:0] pma_tx,output wire pma_tck,
 input wire [543:0] pma_rx,input wire pma_rck,
 output reg padding_fault
);
 reg [486:0] tx_pin;
 wire [511:0] rx_word;
 always @(posedge clk)begin tx_pin<=tx;rx<=rx_word[486:0];end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)padding_fault<=0;
 else if(st[1] && rx_word[511:487]!==25'd0)padding_fault<=1;
 ot_pdie_serdes #(.EMUT(EMUT),.DMUT(DMUT)) u_digital(
 .clk(clk),.rst(rst_n),.tx({25'd0,tx_pin} ^ (MUT_PAD?512'd1:512'd0)),
 .rx(rx_word),.st(st),.pma_tx(pma_tx),.pma_tck(pma_tck),.pma_rx(pma_rx),.pma_rck(pma_rck));
endmodule
