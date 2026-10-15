`timescale 1ns/1ps
`default_nettype none
// Capture every external command/data/epoch/PHY input before any guard fork.
// Stored SRAM payload already has exactly one first-capture q_pin in codec.
// Flatten this wrapper with actual TX5 control as one leaf: overall TX6/RX2.
module ot_hgi_coll_static_capture_ctl #(parameter integer MUT=0)(
 input wire clk,
 input wire rst_n,epoch_begin,
 input wire [7:0] epoch,
 input wire wr_v,wr_observed_v,
 input wire [15:0] wr_seq,
 input wire [544:0] wr_flit,
 input wire rd_v,
 input wire [15:0] rd_seq,
 input wire rx_expect_v,
 input wire [15:0] rx_expect_seq,
 input wire phy_up,
 output wire tx_pin_v,
 output wire [611:0] tx_pin_flit,
 input wire rx_pin_v,
 input wire [611:0] rx_pin_flit,
 output wire rx_v,
 output wire [544:0] rx_flit,
 output wire epoch_abort,
 output wire retry_requested,
 output wire [10:0] fault_cause,
 output wire bank_we,output wire [5:0] bank_wa,bank_ra,
 output wire [563:0] bank_data,input wire [563:0] stored
);
 reg epoch_begin_pin;
 reg [7:0] epoch_pin;
 reg wr_v_pin;
 reg wr_observed_v_pin;
 reg [15:0] wr_seq_pin;
 reg [544:0] wr_flit_pin;
 reg rd_v_pin;
 reg [15:0] rd_seq_pin;
 reg rx_expect_v_pin;
 reg [15:0] rx_expect_seq_pin;
 reg phy_up_pin;
 reg rx_pin_v_pin;
 reg [611:0] rx_pin_flit_pin;
 always @(posedge clk)begin
  epoch_pin<=epoch;
  wr_seq_pin<=wr_seq;
  wr_flit_pin<=wr_flit;
  rd_seq_pin<=rd_seq;
  rx_expect_seq_pin<=rx_expect_seq;
  phy_up_pin<=phy_up;
  rx_pin_flit_pin<=rx_pin_flit;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin epoch_begin_pin<=0;wr_v_pin<=0;wr_observed_v_pin<=0;rd_v_pin<=0;rx_expect_v_pin<=0;rx_pin_v_pin<=0;end
  else begin epoch_begin_pin<=epoch_begin;wr_v_pin<=wr_v;wr_observed_v_pin<=wr_observed_v;rd_v_pin<=rd_v;rx_expect_v_pin<=rx_expect_v;rx_pin_v_pin<=rx_pin_v;end
 end
 ot_hgi_coll_static_pinreg_ctl #(.MUT(MUT)) u_core(
 .clk(clk),.rst_n(rst_n),
 .epoch_begin(epoch_begin_pin),
 .epoch(epoch_pin),
 .wr_v(wr_v_pin),
 .wr_observed_v(wr_observed_v_pin),
 .wr_seq(wr_seq_pin),
 .wr_flit(wr_flit_pin),
 .rd_v(rd_v_pin),
 .rd_seq(rd_seq_pin),
 .rx_expect_v(rx_expect_v_pin),
 .rx_expect_seq(rx_expect_seq_pin),
 .phy_up(phy_up_pin),
 .rx_pin_v(rx_pin_v_pin),
 .rx_pin_flit(rx_pin_flit_pin),
 .tx_pin_v(tx_pin_v),
 .tx_pin_flit(tx_pin_flit),
 .rx_v(rx_v),
 .rx_flit(rx_flit),
 .epoch_abort(epoch_abort),
 .retry_requested(retry_requested),
 .fault_cause(fault_cause),
 .bank_we(bank_we),
 .bank_wa(bank_wa),
 .bank_ra(bank_ra),
 .bank_data(bank_data),
 .stored(stored));
endmodule
`default_nettype wire
