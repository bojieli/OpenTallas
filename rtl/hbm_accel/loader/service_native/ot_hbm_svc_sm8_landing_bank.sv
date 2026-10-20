`default_nettype none
// One ordinal%8 landing bank: actual response FIFO, local epoch/duplicate
// validation, and one actual two-block 128x256 SRAM. complete_v is the
// combinational last accepted landing event, captured at this stream edge.
// H-DIE 2026-10-15: LBANKS=4 = four 64-row landing blocks in one actual 256x256 SRAM (the steady-state fill latency
// ~150 ns + copy ~68 ns per block needs >=3 blocks in flight for the 99 B/cycle/SM price); LBANKS=2 = the two-block
// 128x256 original.  The response word carries a LB-bit landing index.
// ELEM-GAPS/HBMB 2026-10-18 WREG=1 (set by the strap-identity svg master ot_hbm_svc_sm4pc_cdc_id; default 0 keeps every
// existing user and closed view bit-identical): the SRAM write port (w_ce/w_addr/wd) is fed from STREAM flops that
// capture the accepted FIFO word, not from the FIFO's hbm-written storage (FWFT mem[rd_bin]) directly: a hard macro
// pin then reads only its own clock family (ref_tile reviewed_gray_fifos: the storage is consumed by registers proved
// against the FIFO read-valid).  The word lands in the SRAM one stream edge later and complete_v is delayed by the
// same edge (registered), so a block is reported complete exactly when its last row is written: copy/go +1 stream
// edge per block (compiler: landing -> resident +1).  WREG=0 = the previous combinational write (bit-identical).
module ot_hbm_svc_sm8_landing_bank #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=2,
 parameter integer LB=(LBANKS>2)?2:1,parameter integer IW=283+LB,parameter integer WREG=0,
 parameter integer FIFO_SRAM=0
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output wire in_ready,input wire [IW-1:0] in_data,
 output wire overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output wire [255:0] read_data
);
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 // L2H-IDXSCORE/SVG 2026-10-19 FIFO_SRAM=1 (set by the strap-identity svg master, gen_svc_sm_group_id.py): the response
 // FIFO storage (IW x RESPONSE_DEPTH = 2,280 b) is a dual-clock SRAM macro (ot_hbm_svc_async_fifo_sram: Gray pointers +
 // 2-entry read buffer in flops, +1 stream edge publish -> packet_v).  FIFO_SRAM=0 = the flop FIFO (bit-identical).
 generate if(FIFO_SRAM!=0)begin:g_rsram
 ot_hbm_svc_async_fifo_sram #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 end else begin:g_rflop
 ot_hbm_svc_async_fifo #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 end endgenerate
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];
 wire [5:0] row=ordinal[8:3];
 wire identity_ok=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==BANK&&
                 {1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 wire complete_now=landing_write&&received_q[bank]+1'b1==count_q[bank];
 // SRAM write port and completion: stream flops (WREG=1) or the accepted word itself (WREG=0)
 wire w_ce;wire [LB-1:0] w_bank;wire [5:0] w_row;wire [255:0] w_data;
 generate if(WREG!=0)begin:g_wreg
  reg w_ce_q,cmp_q;reg [LB-1:0] w_bank_q;reg [5:0] w_row_q;reg [255:0] w_data_q;
  always @(posedge stream_clk or negedge stream_rst_n)
   if(!stream_rst_n)begin w_ce_q<=0;cmp_q<=0;end else begin w_ce_q<=landing_write;cmp_q<=complete_now;end
  always @(posedge stream_clk)if(landing_write)begin w_bank_q<=bank;w_row_q<=row;w_data_q<=packet[255:0];end
  assign w_ce=w_ce_q;assign w_bank=w_bank_q;assign w_row=w_row_q;assign w_data=w_data_q;
  assign complete_v=cmp_q;assign complete_bank=w_bank_q;
 end else begin:g_wcomb
  assign w_ce=landing_write;assign w_bank=bank;assign w_row=row;assign w_data=packet[255:0];
  assign complete_v=complete_now;assign complete_bank=bank;
 end endgenerate
 assign fault=sticky||underflow;
 integer b;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   valid_q<=0;sticky<=0;
   for(b=0;b<LBANKS;b=b+1)begin epoch_q[b]<=0;count_q[b]<=0;received_q[b]<=0;seen_q[b]<=0;end
  end else begin
   if(reserve_v)begin
    valid_q[reserve_bank]<=1;epoch_q[reserve_bank]<=reserve_epoch;
    count_q[reserve_bank]<=reserve_total>BANK?(reserve_total+7-BANK)/8:0;
    received_q[reserve_bank]<=0;seen_q[reserve_bank]<=0;
   end
   if(packet_take)begin
    if(!identity_ok)sticky<=1;
    else begin seen_q[bank][row]<=1;received_q[bank]<=received_q[bank]+1'b1;end
   end
  end
 end
 generate if(LBANKS<=2)begin:g_two
 ot_sram_1r1w_128x256_m1_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank[0],read_row}),.rd_out(read_data),
  .w_ce_in(w_ce),.w_addr_in({w_bank[0],w_row}),.wd_in(w_data),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else begin:g_four
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(w_ce),.w_addr_in({w_bank,w_row}),.wd_in(w_data),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
