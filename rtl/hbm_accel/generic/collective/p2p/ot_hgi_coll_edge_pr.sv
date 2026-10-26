`timescale 1ns/1ps
`default_nettype none
// PATH-HBM/Q3 2026-10-25: pin-registered (_pr) twins of the coll_q3 EDGE members (split piece ot_hfd_coll_q3_edge_core =
// 3x link_e + argmax_m_tp192 of ot_hfd_coll_q3_hard_v8x_s).  port_regclass on the as-built edge found 44 cut input bits
// captured through logic (rule: register every partition pin):
//   link{k}_epoch_begin / epoch_new / held_epoch : the epoch select `epoch_begin ? epoch_new : held_epoch` sat IN FRONT
//     of the capture-control epoch pin flop.
//     FIX (0 edges): ot_hgi_coll_static_capture_ctl_pr registers epoch_begin, epoch_new and held_epoch at the pin and
//     selects AFTER the pin flops: sel(epoch_begin_pin, epoch_new_pin, held_epoch_pin) == the old epoch_pin on every
//     edge (the select commutes with the register; epoch_begin_pin is the existing reset flop).  Bit- and edge-exact.
//   arg_mode / arg_in_slot / arg_in_v : the TKM/ARG mode gate (`in_v & {4{mode}}`) fed u_data's merge stage and the
//     u_chk lane flops.
//     FIX (+1 edge): ot_hgi_coll_argmax_m_tp192_pr keeps ONLY the pin-captured instance (the old u_chk: the actual
//     ot_hgi_coll_argmax_static on +1-edge pin registers) and takes out_v / out_flit from it as well as fault.  Every
//     input is delayed uniformly, so the argmax runs exactly 1 edge later: out_v / out_flit +1 edge; fault unchanged
//     (it already came from the pin-captured copy).  u_data (the live-input duplicate) is removed (area -1 argmax core).
//     COMPILER: the ARG publication lands 1 edge later -> the qslots ARG-source capture slot moves +1 edge in the
//     compiled programme (constant, same mechanism as the q2_s reduce_pr +1).
// Equivalence vs the originals: bench/coll_q3_split/edge_pr_eq (link_e exact, argmax out +1 edge / fault exact).
module ot_hgi_coll_static_capture_ctl_pr(
 input wire clk,
 input wire rst_n,epoch_begin,
 input wire [7:0] epoch_new,held_epoch,
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
 reg [7:0] epoch_new_pin,held_epoch_pin;
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
  epoch_new_pin<=epoch_new;
  held_epoch_pin<=held_epoch;
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
 wire [7:0] epoch_sel=epoch_begin_pin?epoch_new_pin:held_epoch_pin;  // select after the pin flops
 ot_hgi_coll_static_pinreg_ctl u_core(
 .clk(clk),.rst_n(rst_n),
 .epoch_begin(epoch_begin_pin),
 .epoch(epoch_sel),
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

// ot_hgi_coll_link_e with the capture-control leaf replaced by its _pr twin (ports identical to ot_hgi_coll_link_e).
module ot_hgi_coll_link_e_pr(
 input wire [4:0] ck,input wire rst_n,epoch_begin,input wire [7:0] epoch_new,held_epoch,
 input wire wr_v,wr_observed_v,input wire [15:0] wr_seq,input wire [544:0] wr_flit,
 input wire rd_v,input wire [15:0] rd_seq,input wire rx_expect_v,input wire [15:0] rx_expect_seq,
 input wire phy_up,output wire tx_pin_v,output wire [611:0] tx_pin_flit,
 input wire rx_pin_v,input wire [611:0] rx_pin_flit,output wire rx_v,output wire [544:0] rx_flit,
 output wire epoch_abort,retry_requested,output wire [10:0] fault_cause);
 wire bank_we;wire [5:0] bank_wa,bank_ra;
 wire [563:0] bank_data,stored;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_hgi_coll_static_pinreg_store u_store(.clk(ck[b+1]),.we(bank_we),.wa(bank_wa),.ra(bank_ra),
   .din(bank_data[b*141+:141]),.dout(stored[b*141+:141]));
 end
 ot_hgi_coll_static_capture_ctl_pr u_ctl(.clk(ck[0]),.rst_n(rst_n),.epoch_begin(epoch_begin),
  .epoch_new(epoch_new),.held_epoch(held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),
  .rd_v(rd_v),.rd_seq(rd_seq),.rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),
  .phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),
  .epoch_abort(epoch_abort),.retry_requested(retry_requested),.fault_cause(fault_cause),
  .bank_we(bank_we),.bank_wa(bank_wa),.bank_ra(bank_ra),.bank_data(bank_data),.stored(stored));
endmodule

// ot_hgi_coll_argmax_m #(.TP(192),.START_REG(1)) reduced to its pin-captured instance (ports identical to
// ot_hgi_coll_argmax_m_tp192).  Alignment of the old u_chk: lane / flush / publish / key / meta +1 edge, start and
// cfg +2 edges (START_REG pin register + 1), so the fold sees exactly the old u_data schedule 1 edge later.
module ot_hgi_coll_argmax_m_tp192_pr(
 input wire clk,rst_n,start,mode,input wire [7:0] cfg_g,cfg_gbase,cfg_rank,
 input wire [3:0] in_slot,in_v,input wire [255:0] in_key,input wire [131:0] in_meta,input wire flush_slot,publish_slot,
 output wire out_v,output wire [544:0] out_flit,output wire fault);
 localparam integer TP=192;
 reg rst_l;
 always @(posedge clk or negedge rst_n) if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
 // pin registers: every data/control input, directly from the pin
 reg start_q,flush_q,pub_q,mode_q;reg [3:0] slot_q,v_q;reg [7:0] g_q,gb_q,rk_q;reg [255:0] key_q;reg [131:0] meta_q;
 always @(posedge clk)begin g_q<=cfg_g;gb_q<=cfg_gbase;rk_q<=cfg_rank;key_q<=in_key;meta_q<=in_meta;end
 always @(posedge clk or negedge rst_l)
  if(!rst_l)begin start_q<=0;flush_q<=0;pub_q<=0;mode_q<=0;slot_q<=0;v_q<=0;end
  else begin start_q<=start;flush_q<=flush_slot;pub_q<=publish_slot;mode_q<=mode;slot_q<=in_slot;
   v_q<=in_v;end
 // START_REG: start / cfg one more edge (as the old u_chk: start_qq / g_qq)
 reg start_qq;reg [7:0] g_qq,gb_qq,rk_qq;
 always @(posedge clk)begin g_qq<=g_q;gb_qq<=gb_q;rk_qq<=rk_q;end
 always @(posedge clk or negedge rst_l) if(!rst_l)start_qq<=0;else start_qq<=start_q;
 wire [2179:0] flit_q;
 for(genvar l=0;l<4;l=l+1)begin:g_lane
  assign flit_q[l*545+:545]={meta_q[l*33+:33],448'd0,key_q[l*64+:64]};
 end
 // mode gate AFTER the pin registers (== the old slot_q / v_q = registered (x & {4{mode}}))
 wire [3:0] slot_g=slot_q & {4{mode_q}};
 wire [3:0] v_g=v_q & {4{mode_q}};
 ot_hgi_coll_argmax_static #(.MAX_GROUP(TP)) u_chk(.clk(clk),.rst_n(rst_l),.start(start_qq),
  .cfg_g(g_qq),.cfg_gbase(gb_qq),.cfg_rank(rk_qq),.in_slot(slot_g),.in_v(v_g),.in_flit(flit_q),
  .flush_slot(flush_q),.publish_slot(pub_q),.out_v(out_v),.out_flit(out_flit),.fault(fault));
endmodule
`default_nettype wire
