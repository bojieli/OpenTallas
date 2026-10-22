`timescale 1ns/1ps
`default_nettype none
// Full-sequence HBM native rail. Every published pin is a controller register Q;
// all sequence, epoch, ownership and CRC checks occur before valid capture.
// Registered controller/store faces, native SRAM/CRC, TX5/RX1.
module ot_hgi_coll_static_pinreg_ctl #(parameter integer MUT=0)(
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
 output reg bank_we,output reg [5:0] bank_wa,bank_ra,
 output reg [563:0] bank_data,input wire [563:0] stored
);
 reg [16:0] write_sequence,tx_sequence,rx_sequence;
 reg [7:0] active_epoch;
 reg epoch_active;
 wire seq_bad=(wr_v && (write_sequence[16] || wr_seq!==write_sequence[15:0])) ||
              (rd_v && (tx_sequence[16] || rd_seq!==tx_sequence[15:0])) ||
              (rx_expect_v && (rx_sequence[16] || rx_expect_seq!==rx_sequence[15:0]));
 wire epoch_bad=(epoch_active && epoch!=active_epoch) ||
                (!epoch_active && (wr_v||rd_v||rx_expect_v||rx_pin_v));
 wire abort_in=seq_bad|epoch_bad;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=0;epoch_active<=0;
  end else if(epoch_begin)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=epoch;epoch_active<=1;
  end else begin
   // Identity counters follow reservations; no arrival selects issue.
   if(wr_v && !write_sequence[16])write_sequence<=write_sequence+1'b1;
   if(rd_v && !tx_sequence[16])tx_sequence<=tx_sequence+1'b1;
   if(rx_expect_v && !rx_sequence[16])rx_sequence<=rx_sequence+1'b1;
  end
 end
 assign retry_requested=epoch_abort;
 wire [560:0] raw_rx_flit;
 assign rx_flit=raw_rx_flit[544:0];

 reg [1:0] wv,wo,rv;
 reg [15:0] readseq[0:1];reg [5:0] writeslot[0:1];
 wire [15:0] stored_sequence=wr_seq ^ ((MUT==11 && wr_seq==16'd64)?16'd64:16'd0);
 always @(posedge clk)begin
  bank_wa<=wr_seq[5:0];bank_ra<=rd_seq[5:0];
  bank_data<={3'b0,stored_sequence,wr_flit};
  writeslot[0]<=wr_seq[5:0];writeslot[1]<=writeslot[0];
  readseq[0]<=rd_seq;readseq[1]<=readseq[0];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bank_we<=0;wv<=0;wo<=0;rv<=0;end
  else if(epoch_begin)begin bank_we<=0;wv<=0;wo<=0;rv<=0;end
  else begin
   bank_we<=wr_v && !epoch_abort && !abort_in;
   wv<={wv[0],wr_v};wo<={wo[0],wr_observed_v};rv<={rv[0],rd_v};
  end
 end
 ot_hgi_coll_static_seq_ctl u_codec(
  .clk(clk),.q_data(stored[560:0]),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
  .abort_in(abort_in),.abort_cause({epoch_bad,seq_bad}),.rd_seq(readseq[1]),.rx_expect_seq(rx_expect_seq),
  .wr_v(wv[1]),.wr_observed_v(wo[1]),.wr_slot(writeslot[1]),
  .rd_v(rv[1]),.rd_slot(readseq[1][5:0]),.rx_expect_v(rx_expect_v),.rx_expect_slot(rx_expect_seq[5:0]),
  .p_tx_up(phy_up),.p_tx_v(tx_pin_v),.p_tx_flit(tx_pin_flit),
  .p_rx_v(rx_pin_v),.p_rx_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(raw_rx_flit),
  .epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
`default_nettype wire
