`timescale 1ns/1ps
`default_nettype none
// Full-sequence HBM native rail. Every published pin is a controller register Q;
// all sequence, epoch, ownership and CRC checks occur before valid capture.
// Four unchanged W141 actual SRAM leaves, TX3/RX1, no extra CRC or normal waits.
module ot_hgi_coll_static_link_seq #(parameter integer MUT=0)(
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
 localparam integer BW=141;
 reg [16:0] write_sequence,tx_sequence,rx_sequence;
 reg [7:0] active_epoch;
 reg epoch_active;
 wire seq_bad=(wr_v && (write_sequence[16] || wr_seq!==write_sequence[15:0])) ||
              (rd_v && (tx_sequence[16] || rd_seq!==tx_sequence[15:0])) ||
              (rx_expect_v && (rx_sequence[16] || rx_expect_seq!==rx_sequence[15:0]));
 wire epoch_bad=(epoch_active && epoch!=active_epoch) ||
                (!epoch_active && (wr_v||rd_v||rx_expect_v||rx_pin_v));
 wire abort_in=seq_bad|epoch_bad;
 always @(posedge ck[0] or negedge rst_n)begin
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
 wire [15:0] stored_sequence=wr_seq ^ ((MUT==11 && wr_seq==16'd64)?16'd64:16'd0);
 wire [563:0] padded_write={3'b0,stored_sequence,wr_flit};
 wire [563:0] stored;
 wire issue_write=wr_v && !epoch_abort && !abort_in && !epoch_begin;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_qkvd_llr_replay_sram_leaf #(.W(BW),.MUT(MUT==3 && b==0)) u_store(
   .ck(ck[b+1]),.we(issue_write),.wa(wr_seq[5:0]),.ra(rd_seq[5:0]),
   .din(padded_write[b*BW+:BW]),.dout(stored[b*BW+:BW]));
 end
 ot_hgi_coll_static_seq_ctl u_ctl(
  .clk(ck[0]),.q_data(stored[560:0]),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
  .abort_in(abort_in),.abort_cause({epoch_bad,seq_bad}),.rd_seq(rd_seq),.rx_expect_seq(rx_expect_seq),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_slot(wr_seq[5:0]),
  .rd_v(rd_v),.rd_slot(rd_seq[5:0]),.rx_expect_v(rx_expect_v),.rx_expect_slot(rx_expect_seq[5:0]),
  .p_tx_up(phy_up),.p_tx_v(tx_pin_v),.p_tx_flit(tx_pin_flit),
  .p_rx_v(rx_pin_v),.p_rx_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(raw_rx_flit),
  .epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
`default_nettype wire
