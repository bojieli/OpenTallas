`timescale 1ns/1ps
`default_nettype none
// Full sequence identity in CRC-protected payload; fixed compiler calendar.
// Physical64 slots recycle after read consumption, independent of link flight.
// Native TX3/RX1, four real SRAMs, unchanged parallelCRC; no normal credits,
// acknowledgements or waits. Abort is exceptional; recovery is unimplemented.
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
 localparam integer FW=561,BW=141;
 reg [16:0] write_sequence,tx_sequence,rx_sequence;
 reg [7:0] active_epoch;
 reg seq_fault,epoch_fault,epoch_active,rx_seq_fault;
 reg [15:0] ts0,ts1,ts2,ts3,rs;
 reg recv_expected,recv_present;
 reg [15:0] received_seq;
 wire core_abort,raw_tx_v,raw_rx_v;
 wire [7:0] core_fault;
 wire [560:0] raw_rx_flit;
 wire [611:0] raw_tx_flit;
 wire tx_bad=raw_tx_v && raw_tx_flit[560:545]!==ts3;
 wire abort_now=core_abort|seq_fault|epoch_fault|rx_seq_fault|tx_bad;
 always @(posedge ck[0])begin
   ts0<=rd_seq;ts1<=ts0;ts2<=ts1;ts3<=ts2;
   rs<=rx_expect_seq;received_seq<=rx_pin_flit[560:545];
 end
 always @(posedge ck[0] or negedge rst_n)begin
  if(!rst_n)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=0;epoch_active<=0;seq_fault<=0;epoch_fault<=0;
   rx_seq_fault<=0;recv_expected<=0;recv_present<=0;
  end else if(epoch_begin)begin
   write_sequence<=0;tx_sequence<=0;rx_sequence<=0;
   active_epoch<=epoch;epoch_active<=1;seq_fault<=0;epoch_fault<=0;
   rx_seq_fault<=0;recv_expected<=0;recv_present<=0;
  end else begin
   recv_expected<=rx_expect_v;recv_present<=rx_pin_v;
   if((epoch_active && epoch!=active_epoch)||(!epoch_active && (wr_v||rd_v||rx_expect_v||rx_pin_v)))epoch_fault<=1;
   if(tx_bad)seq_fault<=1;
   if(recv_expected && recv_present && received_seq!==rs)rx_seq_fault<=1;
   if(wr_v)begin
    if(write_sequence[16] || wr_seq!==write_sequence[15:0])seq_fault<=1;
    if(!write_sequence[16])write_sequence<=write_sequence+1'b1;
   end
   if(rd_v)begin
    if(tx_sequence[16] || rd_seq!==tx_sequence[15:0])seq_fault<=1;
    if(!tx_sequence[16])tx_sequence<=tx_sequence+1'b1;
   end
   if(rx_expect_v)begin
    if(rx_sequence[16] || rx_expect_seq!==rx_sequence[15:0])seq_fault<=1;
    if(!rx_sequence[16])rx_sequence<=rx_sequence+1'b1;
   end
  end
 end
 assign epoch_abort=abort_now;
 assign retry_requested=epoch_abort;
 assign fault_cause={rx_seq_fault,epoch_fault,seq_fault|tx_bad,core_fault};
 assign tx_pin_v=raw_tx_v && !abort_now;
 assign tx_pin_flit=raw_tx_flit;
 assign rx_v=raw_rx_v && !abort_now;
 assign rx_flit=raw_rx_flit[544:0];
 wire [15:0] stored_sequence=wr_seq ^ ((MUT==11 && wr_seq==16'd64)?16'd64:16'd0);
 wire [563:0] padded_write={3'b0,stored_sequence,wr_flit};
 wire [563:0] stored;
 wire issue_write=wr_v && !abort_now && !epoch_begin;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_qkvd_llr_replay_sram_leaf #(.W(BW),.MUT(MUT==3 && b==0)) u_store(
   .ck(ck[b+1]),.we(issue_write),.wa(wr_seq[5:0]),.ra(rd_seq[5:0]),
   .din(padded_write[b*BW+:BW]),.dout(stored[b*BW+:BW]));
 end
 ot_qwen_static_slot_ctl #(.FW(FW),.CW(32),.PW(612)) u_ctl(
  .clk(ck[0]),.q_data(stored[560:0]),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
  .wr_v(wr_v && !abort_now),.wr_observed_v(wr_observed_v),.wr_slot(wr_seq[5:0]),
  .rd_v(rd_v && !abort_now),.rd_slot(rd_seq[5:0]),
  .rx_expect_v(rx_expect_v && !abort_now),.rx_expect_slot(rx_expect_seq[5:0]),
  .p_tx_up(phy_up),.p_tx_v(raw_tx_v),.p_tx_flit(raw_tx_flit),
  .p_rx_v(rx_pin_v),.p_rx_flit(rx_pin_flit),.rx_v(raw_rx_v),.rx_flit(raw_rx_flit),
  .epoch_abort(core_abort),.fault_cause(core_fault));
endmodule
`default_nettype wire
