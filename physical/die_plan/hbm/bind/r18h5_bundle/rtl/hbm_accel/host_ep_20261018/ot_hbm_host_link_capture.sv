`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_host_link_capture (H-D4G5/HOSTEP 2026-10-18): the host-link reliability layer of the d4g host control plane,
// = COLL's ot_hgi_coll_static_link_capture (sequence, CRC-32, 64-deep publication store, epoch abort) with ONE change:
// the three 16-bit identity counters WRAP (mod 2^16) instead of saturating at 2^16.
//   Why: a COLL epoch is one collective (<< 65,536 frames); the host link carries one session for the whole deployment
//   (programme install = 10^5..10^6 packets), and an epoch change needs both link ends quiescent.  Every frame is still
//   checked in order against the full 16-bit expected sequence (seq_ctl rx_seq_bad / tx_seq_bad), so a lost, repeated or
//   reordered frame is detected exactly as before; wrap only removes the per-epoch frame limit.
// Unchanged, reused by source: ot_hgi_coll_static_seq_ctl (CRC-32 codec, TX3/RX1 pipes, ownership map, fault causes),
// ot_hgi_coll_static_pinreg_store (4 x 141-b pin-registered replay SRAM leaves).  This file carries the wrapper, the
// all-input pin capture (= ot_hgi_coll_static_capture_ctl) and the counter block (= ot_hgi_coll_static_pinreg_ctl but
// wrapping).  Latencies are COLL's: rd_v -> tx_pin_v 7 edges (TX6 + output flop), rx_pin_v/rx_expect_v (same edge) ->
// rx_v 3 edges.
// MUT (bench only): 1 = saturating counters (COLL behaviour; a session longer than 65,536 frames aborts).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_host_link_pinreg_ctl #(parameter integer MUT=0)(
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
 reg [16:0] write_sequence,tx_sequence,rx_sequence;   // bit 16 = COLL saturation flag; stays 0 here unless MUT==1
 reg [7:0] active_epoch;
 reg epoch_active;
 wire seq_bad=(wr_v && (write_sequence[16] || wr_seq!==write_sequence[15:0])) ||
              (rd_v && (tx_sequence[16] || rd_seq!==tx_sequence[15:0])) ||
              (rx_expect_v && (rx_sequence[16] || rx_expect_seq!==rx_sequence[15:0]));
 wire epoch_bad=(epoch_active && epoch!=active_epoch) ||
                (!epoch_active && (wr_v||rd_v||rx_expect_v||rx_pin_v));
 wire abort_in=seq_bad|epoch_bad;
 function automatic [16:0] nxt(input [16:0] s);
  nxt=(MUT==1)?(s[16]?s:s+17'd1):{1'b0,s[15:0]+16'd1};
 endfunction
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=0;epoch_active<=0;
  end else if(epoch_begin)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=epoch;epoch_active<=1;
  end else begin
   if(wr_v)write_sequence<=nxt(write_sequence);
   if(rd_v)tx_sequence<=nxt(tx_sequence);
   if(rx_expect_v)rx_sequence<=nxt(rx_sequence);
  end
 end
 assign retry_requested=epoch_abort;
 wire [560:0] raw_rx_flit;
 assign rx_flit=raw_rx_flit[544:0];
 reg [1:0] wv,wo,rv;
 reg [15:0] readseq[0:1];reg [5:0] writeslot[0:1];
 always @(posedge clk)begin
  bank_wa<=wr_seq[5:0];bank_ra<=rd_seq[5:0];
  bank_data<={3'b0,wr_seq,wr_flit};
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

module ot_hbm_host_link_capture #(parameter integer MUT=0)(
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
 output wire [10:0] fault_cause
);
 // all-input pin capture (ot_hgi_coll_static_capture_ctl)
 reg epoch_begin_pin,wr_v_pin,wr_observed_v_pin,rd_v_pin,rx_expect_v_pin,rx_pin_v_pin,phy_up_pin;
 reg [7:0] epoch_pin;reg [15:0] wr_seq_pin,rd_seq_pin,rx_expect_seq_pin;
 reg [544:0] wr_flit_pin;reg [611:0] rx_pin_flit_pin;
 always @(posedge clk)begin
  epoch_pin<=epoch;wr_seq_pin<=wr_seq;wr_flit_pin<=wr_flit;rd_seq_pin<=rd_seq;
  rx_expect_seq_pin<=rx_expect_seq;phy_up_pin<=phy_up;rx_pin_flit_pin<=rx_pin_flit;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin epoch_begin_pin<=0;wr_v_pin<=0;wr_observed_v_pin<=0;rd_v_pin<=0;rx_expect_v_pin<=0;rx_pin_v_pin<=0;end
  else begin epoch_begin_pin<=epoch_begin;wr_v_pin<=wr_v;wr_observed_v_pin<=wr_observed_v;rd_v_pin<=rd_v;
   rx_expect_v_pin<=rx_expect_v;rx_pin_v_pin<=rx_pin_v;end
 end
 wire bank_we;wire [5:0] bank_wa,bank_ra;
 wire [563:0] bank_data,stored;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_hgi_coll_static_pinreg_store u_store(
   .clk(clk),.we(bank_we),.wa(bank_wa),.ra(bank_ra),
   .din(bank_data[b*141+:141]),.dout(stored[b*141+:141]));
 end
 wire retry_unused;
 ot_hbm_host_link_pinreg_ctl #(.MUT(MUT)) u_core(
  .clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin_pin),.epoch(epoch_pin),
  .wr_v(wr_v_pin),.wr_observed_v(wr_observed_v_pin),.wr_seq(wr_seq_pin),.wr_flit(wr_flit_pin),
  .rd_v(rd_v_pin),.rd_seq(rd_seq_pin),.rx_expect_v(rx_expect_v_pin),.rx_expect_seq(rx_expect_seq_pin),
  .phy_up(phy_up_pin),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v_pin),.rx_pin_flit(rx_pin_flit_pin),.rx_v(rx_v),.rx_flit(rx_flit),
  .epoch_abort(epoch_abort),.retry_requested(retry_unused),.fault_cause(fault_cause),
  .bank_we(bank_we),.bank_wa(bank_wa),.bank_ra(bank_ra),.bank_data(bank_data),.stored(stored));
endmodule
`default_nettype wire
