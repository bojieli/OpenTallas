`timescale 1ns/1ps
`default_nettype none
// Full-sequence HBM native rail. Every published pin is a controller register Q;
// all sequence, epoch, ownership and CRC checks occur before valid capture.
// Registered controller/store faces, native SRAM/CRC, TX5/RX1.
module ot_hgi_coll_static_link_pinreg #(parameter integer MUT=0)(
 input wire [4:0] ck,
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
 output wire [10:0] fault_cause
);

 wire bank_we;wire [5:0] bank_wa,bank_ra;
 wire [563:0] bank_data,stored;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_hgi_coll_static_pinreg_store #(.MUT(MUT==3 && b==0)) u_store(
   .clk(ck[b+1]),.we(bank_we),.wa(bank_wa),.ra(bank_ra),
   .din(bank_data[b*141+:141]),.dout(stored[b*141+:141]));
 end
 ot_hgi_coll_static_pinreg_ctl #(.MUT(MUT)) u_ctl(
 .clk(ck[0]),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
 .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),
 .rd_v(rd_v),.rd_seq(rd_seq),.rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),
 .phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
 .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),
 .epoch_abort(epoch_abort),.retry_requested(retry_requested),.fault_cause(fault_cause),
 .bank_we(bank_we),.bank_wa(bank_wa),.bank_ra(bank_ra),.bank_data(bank_data),.stored(stored));
endmodule
`default_nettype wire
